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


@dataclass
class HeldRef:
    """Abstract predicate: is object held by player?

    This is an abstraction of LocationRef(object) that reduces state space:
    - LocationRef tracks exact location (~N rooms as possible values)
    - HeldRef tracks only "held vs not-held" (2 values: True/False)

    Use when the constraint only cares about "player has X", not "X is in room Y".
    """
    object: str  # e.g., "@key"

    def __hash__(self):
        return hash(("held", self.object))

    def __str__(self):
        return f"{self.object}:held"


# A StateRef is any of the above
StateRef = PropertyRef | LocationRef | QueueRef | HeldRef


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

    # What target values each behavior sets for each state ref
    # modifies_to[state][behavior] = set of possible target values
    # None in the set means "unknown/variable value"
    modifies_to: dict[StateRef, dict[BehaviorRef, set[Any]]] = field(default_factory=dict)

    # What reads each piece of state (for relevance analysis)
    reads: dict[StateRef, set[BehaviorRef]] = field(default_factory=dict)

    # Properties that are never modified
    constants: set[StateRef] = field(default_factory=set)

    # All state references found
    all_state: set[StateRef] = field(default_factory=set)

    def add_modify(self, state: StateRef, behavior: BehaviorRef, target_value: Any = None):
        """Record that a behavior can modify a state reference.

        Args:
            state: The state reference being modified
            behavior: The behavior doing the modification
            target_value: The value being set (None means unknown/variable)
        """
        self.all_state.add(state)
        if state not in self.modifies:
            self.modifies[state] = set()
        self.modifies[state].add(behavior)

        # Track target value
        if state not in self.modifies_to:
            self.modifies_to[state] = {}
        if behavior not in self.modifies_to[state]:
            self.modifies_to[state][behavior] = set()
        self.modifies_to[state][behavior].add(target_value)

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

    def to_paths(self) -> "PathEffectAnalysis":
        """Convert to StatePath-based representation.

        Returns a PathEffectAnalysis with the same data but using StatePath
        instead of PropertyRef/LocationRef/QueueRef/HeldRef.
        """
        from frotz.state import StatePath, state_ref_to_path

        result = PathEffectAnalysis()

        for ref in self.all_state:
            result.all_state.add(state_ref_to_path(ref))

        for ref, behaviors in self.modifies.items():
            path = state_ref_to_path(ref)
            result.modifies[path] = behaviors.copy()

        for ref, behavior_targets in self.modifies_to.items():
            path = state_ref_to_path(ref)
            result.modifies_to[path] = {
                behavior: targets.copy()
                for behavior, targets in behavior_targets.items()
            }

        for ref, behaviors in self.reads.items():
            path = state_ref_to_path(ref)
            result.reads[path] = behaviors.copy()

        for ref in self.constants:
            result.constants.add(state_ref_to_path(ref))

        return result


@dataclass
class PathEffectAnalysis:
    """Effect analysis results using StatePath.

    This is the new unified representation that Phase 3 (value domain inference)
    will use. It has the same structure as EffectAnalysis but uses StatePath
    instead of the old StateRef variants.
    """

    # What can modify each piece of state
    modifies: dict["StatePath", set[BehaviorRef]] = field(default_factory=dict)

    # What target values each behavior sets for each state path
    modifies_to: dict["StatePath", dict[BehaviorRef, set[Any]]] = field(
        default_factory=dict
    )

    # What reads each piece of state
    reads: dict["StatePath", set[BehaviorRef]] = field(default_factory=dict)

    # State paths that are never modified
    constants: set["StatePath"] = field(default_factory=set)

    # All state paths found
    all_state: set["StatePath"] = field(default_factory=set)

    def get_write_values(self, path: "StatePath") -> set[Any]:
        """Get all possible values that can be written to a path.

        Returns the union of target values across all behaviors that write
        to this path. None in the set means "unknown/variable value".
        """
        if path not in self.modifies_to:
            return set()
        result = set()
        for targets in self.modifies_to[path].values():
            result.update(targets)
        return result


# Import StatePath for type annotations (at module level after PathEffectAnalysis)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from frotz.state import StatePath


class EffectAnalyzer:
    """Analyzes a Grue world to find what state can change."""

    def __init__(self, world: GrueWorld):
        self.world = world
        self.analysis = EffectAnalysis()
        self._current_behavior: BehaviorRef | None = None
        self._current_self: str | None = None  # Object name for ?self resolution

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

        # Built-in: takeable objects can be taken/dropped by runtime
        # This is equivalent to having default :take and :drop behaviors
        self._collect_takeable_effects()

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

    def _collect_takeable_effects(self):
        """Model runtime default :take and :drop behaviors for takeable objects.

        Objects with :takeable true can be taken (moved to @player) and dropped
        (moved to current room) via the runtime's default behavior. This is
        equivalent to having implicit behaviors on each takeable object.
        """
        player_name = self.world.player or "@player"

        for obj_name, obj in self.world.objects.items():
            # Check if object is takeable
            is_takeable = obj.properties.get("takeable", False)
            if not is_takeable:
                continue

            # Check if object has a custom :take behavior that already handles location
            # If so, we don't need to add the runtime default
            has_custom_take = False
            if hasattr(obj, 'behaviors') and obj.behaviors:
                for behavior in obj.behaviors:
                    if behavior.verb == "take":
                        has_custom_take = True
                        break

            if not has_custom_take:
                # Runtime's default :take moves object to player
                obj_loc = LocationRef(obj_name)
                self.analysis.add_modify(obj_loc, BehaviorRef("runtime", "take"), player_name)

            # Drop is always available for held objects (runtime default)
            # It moves the object to current room (variable destination)
            obj_loc = LocationRef(obj_name)
            self.analysis.add_modify(obj_loc, BehaviorRef("runtime", "drop"), None)  # None = unknown destination

    def _analyze_object_behaviors(self, obj_name: str, obj: Any):
        """Analyze all behaviors on an object."""
        if not hasattr(obj, 'behaviors') or not obj.behaviors:
            return

        for behavior in obj.behaviors:
            self._current_behavior = BehaviorRef(obj_name, behavior.verb)
            self._current_self = obj_name  # Track ?self for resolution
            self._walk_expr(behavior.body)
            self._current_self = None

    def _analyze_room_behaviors(self, room_name: str, room: Any):
        """Analyze all behaviors on a room."""
        if not hasattr(room, 'behaviors') or not room.behaviors:
            return

        for behavior in room.behaviors:
            self._current_behavior = BehaviorRef(room_name, behavior.verb)
            self._current_self = room_name  # Track ?self for resolution
            self._walk_expr(behavior.body)
            self._current_self = None

    def _analyze_event(self, event_name: str, event: Any):
        """Analyze an event's body (on_turn handler)."""
        if not hasattr(event, 'body') or not event.body:
            return

        self._current_behavior = BehaviorRef(f"event:{event_name}", "on_turn")
        self._walk_expr(event.body)

    def _resolve_object_ref(self, expr: Any) -> str | None:
        """Resolve an expression to an object name.

        Handles:
        - @object symbols -> "@object"
        - ?self -> current behavior's object (if set)

        Returns None if the expression can't be resolved to a static object name.
        """
        if isinstance(expr, Symbol):
            if expr.name.startswith("@"):
                return expr.name
            if expr.name == "?self" and self._current_self:
                return self._current_self
        return None

    def _extract_literal_value(self, expr: Any) -> Any:
        """Extract a literal value from an expression, or None if not a literal.

        Returns the actual value for:
        - Booleans: True, False
        - Numbers: int, float
        - Strings: str
        - Symbols: @object names (as strings like "@player")
        - Keywords: :keyword names

        Returns None for complex expressions (function calls, etc.)
        """
        if expr is None:
            return None
        if isinstance(expr, bool):
            return expr
        if isinstance(expr, (int, float)):
            return expr
        if isinstance(expr, str):
            return expr
        if isinstance(expr, Symbol):
            # Object references like @player, @cell
            if expr.name.startswith("@"):
                return expr.name
            # Boolean symbols
            if expr.name == "true":
                return True
            if expr.name == "false":
                return False
            if expr.name == "nil":
                return None
            # Other symbols are variable references - unknown value
            return None
        if isinstance(expr, Keyword):
            return expr.name
        # SList or other complex expressions - unknown value
        return None

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

                # Function call inlining: (function-name args...)
                # If this is a call to a defn'd function, walk its body
                if name in self.world.functions:
                    fn = self.world.functions[name]
                    # Track that we're inlining to avoid infinite recursion
                    if not hasattr(self, '_inlining_stack'):
                        self._inlining_stack = set()
                    if name not in self._inlining_stack:
                        self._inlining_stack.add(name)
                        try:
                            self._walk_expr(fn.body)
                        finally:
                            self._inlining_stack.discard(name)
                    # Also walk arguments for potential reads
                    for item in items[1:]:
                        self._walk_expr(item)
                    return

                # Effect detection: (set @obj :prop value) or (set ?self :prop value)
                if name == "set" and len(items) >= 4:
                    obj = items[1]
                    prop = items[2]
                    value_expr = items[3]
                    obj_name = self._resolve_object_ref(obj)
                    if obj_name and isinstance(prop, Keyword):
                        ref = PropertyRef(obj_name, prop.name)
                        target_value = self._extract_literal_value(value_expr)
                        self.analysis.add_modify(ref, self._current_behavior, target_value)
                    # Also walk the value expression for reads
                    for item in items[3:]:
                        self._walk_expr(item)
                    return

                # Effect detection: (set-prop @obj prop value) - variant
                if name == "set-prop" and len(items) >= 4:
                    obj = items[1]
                    prop = items[2]
                    value_expr = items[3]
                    obj_name = self._resolve_object_ref(obj)
                    if obj_name:
                        prop_name = prop.name if isinstance(prop, (Symbol, Keyword)) else str(prop)
                        ref = PropertyRef(obj_name, prop_name)
                        target_value = self._extract_literal_value(value_expr)
                        self.analysis.add_modify(ref, self._current_behavior, target_value)
                    for item in items[3:]:
                        self._walk_expr(item)
                    return

                # Effect detection: (move @obj dest) or (move ?self dest)
                if name == "move" and len(items) >= 3:
                    obj = items[1]
                    dest = items[2]
                    obj_name = self._resolve_object_ref(obj)
                    if obj_name:
                        ref = LocationRef(obj_name)
                        # Destination could be @room, @player, or (loc @player)
                        target_value = self._extract_literal_value(dest)
                        self.analysis.add_modify(ref, self._current_behavior, target_value)
                    # Walk destination for reads
                    self._walk_expr(dest)
                    return

                # Effect detection: (take @obj) or (take ?self) - moves object to player
                if name == "take" and len(items) >= 2:
                    obj = items[1]
                    obj_name = self._resolve_object_ref(obj)
                    if obj_name:
                        ref = LocationRef(obj_name)
                        self.analysis.add_modify(ref, self._current_behavior, "@player")
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

                # Read detection: (loc @obj) or (loc ?self)
                if name == "loc" and len(items) >= 2:
                    obj = items[1]
                    obj_name = self._resolve_object_ref(obj)
                    if obj_name:
                        ref = LocationRef(obj_name)
                        self.analysis.add_read(ref, self._current_behavior)
                    return

                # Read detection: (held? @obj) or (held? ?self)
                if name == "held?" and len(items) >= 2:
                    obj = items[1]
                    obj_name = self._resolve_object_ref(obj)
                    if obj_name:
                        ref = LocationRef(obj_name)
                        self.analysis.add_read(ref, self._current_behavior)
                    return

                # Read detection: (queued? event)
                if name == "queued?" and len(items) >= 2:
                    event = items[1]
                    event_name = event.name if isinstance(event, Symbol) else str(event)
                    ref = QueueRef(event_name)
                    self.analysis.add_read(ref, self._current_behavior)
                    return

                # Read detection: (in-room? @obj @room ...) or (in-room? ?self @room ...)
                if name == "in-room?" and len(items) >= 2:
                    obj = items[1]
                    obj_name = self._resolve_object_ref(obj)
                    if obj_name:
                        ref = LocationRef(obj_name)
                        self.analysis.add_read(ref, self._current_behavior)
                    return

            # Keyword-as-function: (:prop @obj) or (:prop ?self) reads a property
            if isinstance(head, Keyword) and len(items) >= 2:
                obj = items[1]
                obj_name = self._resolve_object_ref(obj)
                if obj_name:
                    ref = PropertyRef(obj_name, head.name)
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
