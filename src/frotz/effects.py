"""
Effect analysis pass for Grue games.

Scans world definitions to build:
- modifies: property -> set[behavior] - which behaviors can modify each property
- reads: property -> set[behavior] - which behaviors depend on each property
- constants: set[property] - properties that never change

This is the "def" side of def-use analysis.
"""

from dataclasses import dataclass, field
from typing import Any

from grue import GrueWorld
from grue.sexpr import SList, Symbol, Keyword


@dataclass
class PropertyRef:
    """Reference to an object property."""
    object: str  # e.g., "@cell-door"
    property: str  # e.g., "locked"

    def __hash__(self):
        return hash((self.object, self.property))

    def __str__(self):
        return f"{self.object}:{self.property}"


@dataclass
class LocationRef:
    """Reference to an object's location."""
    object: str  # e.g., "@key"

    def __hash__(self):
        return hash(("loc", self.object))

    def __str__(self):
        return f"{self.object}:location"


@dataclass
class QueueRef:
    """Reference to an event queue."""
    event: str  # e.g., "hacker-helps"

    def __hash__(self):
        return hash(("queue", self.event))

    def __str__(self):
        return f"queue:{self.event}"


# A StateRef is any of the above
StateRef = PropertyRef | LocationRef | QueueRef


@dataclass
class BehaviorRef:
    """Reference to a specific behavior on an object."""
    object: str  # e.g., "@cell-door"
    verb: str  # e.g., "unlock"

    def __hash__(self):
        return hash((self.object, self.verb))

    def __str__(self):
        return f"{self.object}:{self.verb}"


@dataclass
class EffectAnalysis:
    """Results of effect analysis on a world."""

    # What can modify each piece of state
    modifies: dict[StateRef, set[BehaviorRef]] = field(default_factory=dict)

    # What reads each piece of state (for relevance analysis)
    reads: dict[StateRef, set[BehaviorRef]] = field(default_factory=dict)

    # Properties that are never modified
    constants: set[StateRef] = field(default_factory=set)

    # All state references found
    all_state: set[StateRef] = field(default_factory=set)

    def add_modify(self, state: StateRef, behavior: BehaviorRef):
        """Record that a behavior can modify a state reference."""
        self.all_state.add(state)
        if state not in self.modifies:
            self.modifies[state] = set()
        self.modifies[state].add(behavior)

    def add_read(self, state: StateRef, behavior: BehaviorRef):
        """Record that a behavior reads a state reference."""
        self.all_state.add(state)
        if state not in self.reads:
            self.reads[state] = set()
        self.reads[state].add(behavior)

    def compute_constants(self):
        """Compute the set of state that is never modified."""
        self.constants = self.all_state - set(self.modifies.keys())

    def summary(self) -> str:
        """Return a human-readable summary."""
        lines = []
        lines.append(f"Total state references: {len(self.all_state)}")
        lines.append(f"Modifiable: {len(self.modifies)}")
        lines.append(f"Constants: {len(self.constants)}")
        lines.append("")

        if self.modifies:
            lines.append("Modifiable state:")
            for state, behaviors in sorted(self.modifies.items(), key=lambda x: str(x[0])):
                behavior_strs = ", ".join(str(b) for b in sorted(behaviors, key=str))
                lines.append(f"  {state} <- {behavior_strs}")
            lines.append("")

        if self.constants:
            lines.append("Constants:")
            for state in sorted(self.constants, key=str):
                lines.append(f"  {state}")

        return "\n".join(lines)


class EffectAnalyzer:
    """Analyzes a Grue world to find what state can change."""

    def __init__(self, world: GrueWorld):
        self.world = world
        self.analysis = EffectAnalysis()
        self._current_behavior: BehaviorRef | None = None

    def analyze(self) -> EffectAnalysis:
        """Run the analysis and return results."""
        # Collect initial state from object definitions
        self._collect_initial_state()

        # Walk all behaviors
        for obj_name, obj in self.world.objects.items():
            self._analyze_object_behaviors(obj_name, obj)

        for room_name, room in self.world.rooms.items():
            self._analyze_room_behaviors(room_name, room)

        for event_name, event in self.world.events.items():
            self._analyze_event(event_name, event)

        # Compute constants
        self.analysis.compute_constants()

        return self.analysis

    def _collect_initial_state(self):
        """Collect all state references from initial definitions."""
        # Objects
        for obj_name, obj in self.world.objects.items():
            # Location
            self.analysis.all_state.add(LocationRef(obj_name))

            # Properties
            for prop in obj.properties.keys():
                self.analysis.all_state.add(PropertyRef(obj_name, prop))

        # Rooms
        for room_name, room in self.world.rooms.items():
            for prop in room.properties.keys():
                self.analysis.all_state.add(PropertyRef(room_name, prop))

        # Events (queue state)
        for event_name in self.world.events.keys():
            self.analysis.all_state.add(QueueRef(event_name))

        # Built-in: player movement is handled by runtime's :go action
        # This is equivalent to having a behavior that modifies player location
        player_name = self.world.player
        if player_name:
            player_loc = LocationRef(player_name)
            self.analysis.all_state.add(player_loc)
            # Mark as modifiable by the built-in "go" action
            self.analysis.add_modify(player_loc, BehaviorRef("runtime", "go"))

            # Navigation through doors (:via) depends on the door's :through behavior
            # Find all doors used in exits and mark runtime:go as reading what :through reads
            self._collect_navigation_dependencies()

    def _collect_navigation_dependencies(self):
        """Find all :via doors in exits and track their :through behavior dependencies.

        When a room exit has :via @door, the runtime calls @door's :through behavior
        to check if navigation is allowed. So runtime:go effectively reads whatever
        :through behaviors read.
        """
        runtime_go = BehaviorRef("runtime", "go")

        # Collect all doors used in :via exits
        doors_used: set[str] = set()
        for room in self.world.rooms.values():
            for exit_info in room.exits:
                # exit_info is an Exit with via attribute
                if hasattr(exit_info, 'via') and exit_info.via:
                    doors_used.add(exit_info.via)

        # For each door, find what its :through behavior reads
        for door_name in doors_used:
            if door_name in self.world.objects:
                door = self.world.objects[door_name]
                if hasattr(door, 'behaviors') and door.behaviors:
                    for behavior in door.behaviors:
                        if behavior.verb == "through":
                            # Analyze what :through reads and mark as read by runtime:go
                            self._current_behavior = runtime_go
                            self._walk_expr(behavior.body)

    def _analyze_object_behaviors(self, obj_name: str, obj: Any):
        """Analyze all behaviors on an object."""
        if not hasattr(obj, 'behaviors') or not obj.behaviors:
            return

        for behavior in obj.behaviors:
            self._current_behavior = BehaviorRef(obj_name, behavior.verb)
            self._walk_expr(behavior.body)

    def _analyze_room_behaviors(self, room_name: str, room: Any):
        """Analyze all behaviors on a room."""
        if not hasattr(room, 'behaviors') or not room.behaviors:
            return

        for behavior in room.behaviors:
            self._current_behavior = BehaviorRef(room_name, behavior.verb)
            self._walk_expr(behavior.body)

    def _analyze_event(self, event_name: str, event: Any):
        """Analyze an event's on_turn handler."""
        if not hasattr(event, 'on_turn') or not event.on_turn:
            return

        self._current_behavior = BehaviorRef(f"event:{event_name}", "on_turn")
        self._walk_expr(event.on_turn)

    def _walk_expr(self, expr: Any):
        """Recursively walk an expression looking for effects and reads."""
        if expr is None:
            return

        if isinstance(expr, Symbol):
            # Check for object references that might indicate a read
            if expr.name.startswith("@"):
                # Just a reference to an object - we'll catch property reads in function calls
                pass
            return

        if isinstance(expr, (str, int, float, bool, Keyword)):
            return

        if isinstance(expr, SList):
            items = expr.items
            if not items:
                return

            head = items[0]
            if isinstance(head, Symbol):
                name = head.name

                # Effect detection: (set @obj :prop value)
                if name == "set" and len(items) >= 4:
                    obj = items[1]
                    prop = items[2]
                    if isinstance(obj, Symbol) and obj.name.startswith("@"):
                        if isinstance(prop, Keyword):
                            ref = PropertyRef(obj.name, prop.name)
                            self.analysis.add_modify(ref, self._current_behavior)
                    # Also walk the value expression for reads
                    for item in items[3:]:
                        self._walk_expr(item)
                    return

                # Effect detection: (set-prop @obj prop value) - variant
                if name == "set-prop" and len(items) >= 4:
                    obj = items[1]
                    prop = items[2]
                    if isinstance(obj, Symbol) and obj.name.startswith("@"):
                        prop_name = prop.name if isinstance(prop, (Symbol, Keyword)) else str(prop)
                        ref = PropertyRef(obj.name, prop_name)
                        self.analysis.add_modify(ref, self._current_behavior)
                    for item in items[3:]:
                        self._walk_expr(item)
                    return

                # Effect detection: (move @obj dest)
                if name == "move" and len(items) >= 3:
                    obj = items[1]
                    if isinstance(obj, Symbol) and obj.name.startswith("@"):
                        ref = LocationRef(obj.name)
                        self.analysis.add_modify(ref, self._current_behavior)
                    # Walk destination for reads
                    self._walk_expr(items[2])
                    return

                # Effect detection: (queue event) or (queue event countdown)
                if name == "queue" and len(items) >= 2:
                    event = items[1]
                    event_name = event.name if isinstance(event, Symbol) else str(event)
                    ref = QueueRef(event_name)
                    self.analysis.add_modify(ref, self._current_behavior)
                    return

                # Effect detection: (dequeue event)
                if name == "dequeue" and len(items) >= 2:
                    event = items[1]
                    event_name = event.name if isinstance(event, Symbol) else str(event)
                    ref = QueueRef(event_name)
                    self.analysis.add_modify(ref, self._current_behavior)
                    return

                # Read detection: (:prop @obj) or (:prop @obj default)
                # This is handled by keyword-as-function below

                # Read detection: (loc @obj)
                if name == "loc" and len(items) >= 2:
                    obj = items[1]
                    if isinstance(obj, Symbol) and obj.name.startswith("@"):
                        ref = LocationRef(obj.name)
                        self.analysis.add_read(ref, self._current_behavior)
                    return

                # Read detection: (held? @obj)
                if name == "held?" and len(items) >= 2:
                    obj = items[1]
                    if isinstance(obj, Symbol) and obj.name.startswith("@"):
                        ref = LocationRef(obj.name)
                        self.analysis.add_read(ref, self._current_behavior)
                    return

                # Read detection: (queued? event)
                if name == "queued?" and len(items) >= 2:
                    event = items[1]
                    event_name = event.name if isinstance(event, Symbol) else str(event)
                    ref = QueueRef(event_name)
                    self.analysis.add_read(ref, self._current_behavior)
                    return

                # Read detection: (in-room? @obj @room ...)
                if name == "in-room?" and len(items) >= 2:
                    obj = items[1]
                    if isinstance(obj, Symbol) and obj.name.startswith("@"):
                        ref = LocationRef(obj.name)
                        self.analysis.add_read(ref, self._current_behavior)
                    return

            # Keyword-as-function: (:prop @obj) reads a property
            if isinstance(head, Keyword) and len(items) >= 2:
                obj = items[1]
                if isinstance(obj, Symbol) and obj.name.startswith("@"):
                    ref = PropertyRef(obj.name, head.name)
                    self.analysis.add_read(ref, self._current_behavior)
                # Walk remaining args
                for item in items[2:]:
                    self._walk_expr(item)
                return

            # Default: walk all children
            for item in items:
                self._walk_expr(item)

        elif isinstance(expr, list):
            # Python list (shouldn't happen often in parsed expressions)
            for item in expr:
                self._walk_expr(item)


def analyze_effects(world: GrueWorld) -> EffectAnalysis:
    """Convenience function to analyze a world."""
    analyzer = EffectAnalyzer(world)
    return analyzer.analyze()
