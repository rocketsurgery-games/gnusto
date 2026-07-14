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
from grue.reduce import Reducer


# The effect-list mutation heads this analyzer models in `_walk_expr`. This must
# stay in exact sync with the runtime's authoritative vocabulary
# (grue.expr.EffectInterpreter.MUTATIONS): a mutation the runtime can apply but
# the analyzer doesn't model is hidden state that silently corrupts every
# downstream tool (reach, requires, depgraph, deadends). The equality is
# enforced by tests/test_effects_completeness.py so a new runtime effect can't
# land without a matching analyzer handler. See docs/frotz.md.
HANDLED_EFFECT_MUTATIONS = frozenset(
    {
        "move",
        "set",
        "set-prop",
        "set-in",
        "inc",
        "dec",
        "queue",
        "dequeue",
        "take",
        "expose",
    }
)

# Runtime default (engine-level) actions that mutate location state without an
# explicit effect-list head. These come from the `_do_*` handlers, not the
# effect vocabulary, and are modeled in `_collect_takeable_effects`.
HANDLED_RUNTIME_ACTIONS = frozenset({"take", "drop", "put", "go"})


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

    # Required action arguments for behaviors
    # required_args[behavior] = set of object names that must be passed as arguments
    # E.g., if a behavior has (= ?tool @axe), it requires @axe as an argument
    required_args: dict[BehaviorRef, set[str]] = field(default_factory=dict)

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

    def add_modify_values(self, state: StateRef, behavior: BehaviorRef, target_values: set[Any]):
        """Record that a behavior can modify a state reference to multiple possible values.

        Args:
            state: The state reference being modified
            behavior: The behavior doing the modification
            target_values: Set of possible values (None in set means unknown/variable)
        """
        self.all_state.add(state)
        if state not in self.modifies:
            self.modifies[state] = set()
        self.modifies[state].add(behavior)

        # Track target values
        if state not in self.modifies_to:
            self.modifies_to[state] = {}
        if behavior not in self.modifies_to[state]:
            self.modifies_to[state][behavior] = set()
        self.modifies_to[state][behavior].update(target_values)

    def add_read(self, state: StateRef, behavior: BehaviorRef):
        """Record that a behavior reads a state reference."""
        self.all_state.add(state)
        if state not in self.reads:
            self.reads[state] = set()
        self.reads[state].add(behavior)

    def add_required_arg(self, behavior: BehaviorRef, obj_name: str):
        """Record that a behavior requires a specific object as argument.

        This is detected from patterns like (= ?tool @axe) which constrain
        an action argument to a specific object.
        """
        if behavior not in self.required_args:
            self.required_args[behavior] = set()
        self.required_args[behavior].add(obj_name)

    def compute_constants(self):
        """Compute the set of state that is never modified."""
        self.constants = self.all_state - set(self.modifies.keys())

    def get_one_way_flags(self, world: "GrueWorld") -> dict[StateRef, tuple[Any, Any]]:
        """Identify properties that only change in one direction.

        Returns a dict mapping StateRef -> (initial_value, final_value) for
        properties that:
        1. Are only ever set to a single known value (not None/variable)
        2. Have an initial value different from that target value

        Common examples:
        - rmung: False -> True (destroyed)
        - severed: False -> True (cut)
        - locked: True -> False (unlocked)

        These can be used for monotonic pruning: if we've seen a state with
        a one-way flag at its final value, states with the same other values
        but the flag at initial value are dominated (can't reach anything new).
        """
        result: dict[StateRef, tuple[Any, Any]] = {}

        for ref, behavior_targets in self.modifies_to.items():
            if not isinstance(ref, PropertyRef):
                continue

            # Collect all target values across all behaviors
            all_targets: set[Any] = set()
            for targets in behavior_targets.values():
                all_targets.update(targets)

            # If only one known value (not None), it's a candidate
            if len(all_targets) != 1 or None in all_targets:
                continue

            target_value = list(all_targets)[0]

            # Get initial value from world definition
            obj_name = ref.object
            prop_name = ref.property

            initial_value = None
            if obj_name in world.objects:
                initial_value = world.objects[obj_name].properties.get(prop_name)
            elif obj_name in world.rooms:
                initial_value = world.rooms[obj_name].properties.get(prop_name)

            # If initial != final, this is a one-way flag
            if initial_value is not None and initial_value != target_value:
                result[ref] = (initial_value, target_value)

        return result

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
        self._reducer = Reducer(world=world)  # Partial evaluator for inlining

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
                            # Set _current_self so ?self references resolve to the door
                            self._current_behavior = runtime_go
                            self._current_self = door_name
                            self._walk_expr(behavior.body)
                            self._current_self = None

    def _collect_takeable_effects(self):
        """Model the runtime default :take, :drop and :put actions for takeable objects.

        Objects with :takeable true can be, via the engine's default handlers:
        - taken (moved to @player),
        - dropped (moved to the current room), and
        - put into any container/surface (moved to that destination).

        These are engine-level actions (`_do_*`), not effect-list heads, so they
        have no game-code body to walk; we model them here as implicit modifiers
        of each takeable object's location. Omitting `put` was defect A: without
        it, a deposit goal like `@painting:location = @trophy-case` has no
        achiever and the backward analyzer marks it constant (empty tree).
        """
        player_name = self.world.player or "@player"

        # All destinations a `put` can target: containers and surfaces.
        put_destinations = {
            name
            for name, o in self.world.objects.items()
            if o.properties.get("container") or o.properties.get("surface")
        }

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

            # Put moves the object into any container/surface (runtime default,
            # bidirectional with the container's :put). A takeable object can end
            # up in any such destination except itself.
            if put_destinations:
                self.analysis.add_modify_values(
                    obj_loc,
                    BehaviorRef("runtime", "put"),
                    {d for d in put_destinations if d != obj_name},
                )

    def _analyze_object_behaviors(self, obj_name: str, obj: Any):
        """Analyze all behaviors on an object."""
        if not hasattr(obj, 'behaviors') or not obj.behaviors:
            return

        for behavior in obj.behaviors:
            self._current_behavior = BehaviorRef(obj_name, behavior.verb)
            self._current_self = obj_name  # Track ?self for resolution
            # Reduce before walking to inline functions and expose literal values
            reduced_body = self._reducer.reduce(behavior.body)
            self._walk_expr(reduced_body)
            self._current_self = None

    def _analyze_room_behaviors(self, room_name: str, room: Any):
        """Analyze all behaviors on a room."""
        if not hasattr(room, 'behaviors') or not room.behaviors:
            return

        for behavior in room.behaviors:
            self._current_behavior = BehaviorRef(room_name, behavior.verb)
            self._current_self = room_name  # Track ?self for resolution
            # Reduce before walking to inline functions and expose literal values
            reduced_body = self._reducer.reduce(behavior.body)
            self._walk_expr(reduced_body)
            self._current_self = None

    def _analyze_event(self, event_name: str, event: Any):
        """Analyze an event's body (on_turn handler)."""
        if not hasattr(event, 'body') or not event.body:
            return

        self._current_behavior = BehaviorRef(f"event:{event_name}", "on_turn")
        # Reduce before walking to inline functions and expose literal values
        reduced_body = self._reducer.reduce(event.body)
        self._walk_expr(reduced_body)

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

    def _extract_path_keys(self, expr: Any) -> list[str]:
        """Extract the key names from a (set-in @obj (:a :b) ...) path expression.

        The path may arrive quoted (an SList whose head is 'quote') or as a bare
        SList of keywords/symbols. Returns the ordered key names, or [] if the
        path can't be statically resolved.
        """
        if isinstance(expr, SList):
            items = expr.items
            # Unwrap (quote (:a :b))
            if items and isinstance(items[0], Symbol) and items[0].name == "quote":
                if len(items) >= 2 and isinstance(items[1], SList):
                    items = items[1].items
                else:
                    return []
            keys: list[str] = []
            for item in items:
                if isinstance(item, (Keyword, Symbol)):
                    keys.append(item.name)
                else:
                    return []
            return keys
        return []

    def _extract_literal_value(self, expr: Any) -> Any:
        """Extract a literal value from an expression, or None if not a literal.

        Returns the actual value for:
        - Booleans: True, False
        - Numbers: int, float
        - Strings: str
        - Symbols: @object names, room names, object names
        - Keywords: :keyword names

        Returns None for complex expressions (function calls, variable refs, etc.)
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
            # Room names (known locations)
            if expr.name in self.world.rooms:
                return expr.name
            # Object names (known objects)
            if expr.name in self.world.objects:
                return expr.name
            # Other symbols are variable references - unknown value
            return None
        if isinstance(expr, Keyword):
            return expr.name
        # SList or other complex expressions - unknown value
        return None

    def _extract_possible_values(self, expr: Any) -> set[Any]:
        """Extract all possible literal values from an expression.

        Unlike _extract_literal_value which returns a single value,
        this handles control flow (cond, if) and quasiquote (unquote)
        to return the set of all possible values.

        Returns a set containing:
        - The literal values if determinable
        - {None} if the value is completely unknown
        """
        # Try simple literal extraction first
        literal = self._extract_literal_value(expr)
        if literal is not None:
            return {literal}

        if not isinstance(expr, SList) or not expr.items:
            return {None}  # Unknown

        head = expr.items[0]
        if not isinstance(head, Symbol):
            return {None}

        name = head.name

        # Handle (unquote expr) - unwrap and recurse
        if name == "unquote" and len(expr.items) >= 2:
            return self._extract_possible_values(expr.items[1])

        # Handle (cond (test1 result1) (test2 result2) ...)
        if name == "cond":
            values = set()
            for clause in expr.items[1:]:
                if isinstance(clause, SList) and len(clause.items) >= 2:
                    result_expr = clause.items[1]
                    values.update(self._extract_possible_values(result_expr))
            return values if values else {None}

        # Handle (if cond then else?)
        if name == "if":
            values = set()
            if len(expr.items) >= 3:
                values.update(self._extract_possible_values(expr.items[2]))
            if len(expr.items) >= 4:
                values.update(self._extract_possible_values(expr.items[3]))
            return values if values else {None}

        return {None}  # Unknown

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

                # Argument constraint detection: (= ?arg @obj)
                # This pattern indicates the behavior requires a specific object as argument
                if name == "=" and len(items) == 3:
                    arg1, arg2 = items[1], items[2]
                    # Check for ?var = @obj pattern (either order)
                    obj_name = None
                    is_arg_constraint = False

                    if isinstance(arg1, Symbol) and arg1.name.startswith("?"):
                        # ?arg = @obj
                        obj_name = self._resolve_object_ref(arg2)
                        is_arg_constraint = True
                    elif isinstance(arg2, Symbol) and arg2.name.startswith("?"):
                        # @obj = ?arg
                        obj_name = self._resolve_object_ref(arg1)
                        is_arg_constraint = True

                    if is_arg_constraint and obj_name and self._current_behavior:
                        self.analysis.add_required_arg(self._current_behavior, obj_name)
                    # Continue walking to catch nested expressions
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
                        target_values = self._extract_possible_values(value_expr)
                        self.analysis.add_modify_values(ref, self._current_behavior, target_values)
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
                        target_values = self._extract_possible_values(value_expr)
                        self.analysis.add_modify_values(ref, self._current_behavior, target_values)
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
                        # Destination could be @room, @player, or complex (cond/unquote)
                        target_values = self._extract_possible_values(dest)
                        self.analysis.add_modify_values(ref, self._current_behavior, target_values)
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

                # Effect detection: (inc @obj :prop [amt]) / (dec @obj :prop [amt])
                # Both read the current numeric value and write a new one. The
                # resulting value is data-dependent, so we record an untargeted
                # modify (no specific target value).
                if name in ("inc", "dec") and len(items) >= 3:
                    obj_name = self._resolve_object_ref(items[1])
                    prop = items[2]
                    if obj_name and isinstance(prop, (Symbol, Keyword)):
                        ref = PropertyRef(obj_name, prop.name)
                        self.analysis.add_read(ref, self._current_behavior)
                        self.analysis.add_modify(ref, self._current_behavior)
                    # Walk an optional amount expression for reads
                    for item in items[3:]:
                        self._walk_expr(item)
                    return

                # Effect detection: (set-in @obj (:path :keys) value) - nested prop
                # At the coarse granularity we track, this modifies the object's
                # top-level property named by the first key of the path.
                if name == "set-in" and len(items) >= 4:
                    obj_name = self._resolve_object_ref(items[1])
                    keys = self._extract_path_keys(items[2])
                    if obj_name and keys:
                        ref = PropertyRef(obj_name, keys[0])
                        self.analysis.add_modify(ref, self._current_behavior)
                    self._walk_expr(items[3])
                    return

                # Effect detection: (expose @obj) - sets :known true
                if name == "expose" and len(items) >= 2:
                    obj_name = self._resolve_object_ref(items[1])
                    if obj_name:
                        ref = PropertyRef(obj_name, "known")
                        self.analysis.add_modify_values(
                            ref, self._current_behavior, {True}
                        )
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
