"""
GRUE Runtime - Execute GRUE world definitions.

This module provides a runtime that:
- Manages game state (object locations, flags, properties)
- Dispatches actions to object behaviors
- Evaluates behavior cases to determine outcomes
- Executes effects to update state

Usage:
    from grue import load_grue, GrueRuntime

    world = load_grue("game.grue")
    runtime = GrueRuntime(world)

    result = runtime.do("open", "DOOR")
    print(result.outcome)  # "success" or "blocked"
"""

from dataclasses import dataclass, field
from typing import Any
from copy import deepcopy

from .parser import GrueWorld, GrueBehavior
from .expr import (
    ExprEvaluator, EffectExecutor, EffectInterpreter, GrueFn, Environment, quote_to_data,
    BehaviorSuccess, BehaviorBlocked, BehaviorRedirect, BehaviorDefault, is_truthy
)
from .sexpr import SExpr, Symbol, SList, Keyword, to_string


# Canonical movement directions and their accepted synonyms. Exits are authored
# with the canonical token (left column); players/agents may use any synonym.
# IF convention (and Zork itself) treats "ne" and "northeast" as the same exit.
_DIRECTION_SYNONYMS = {
    "north": "north", "n": "north",
    "south": "south", "s": "south",
    "east": "east", "e": "east",
    "west": "west", "w": "west",
    "ne": "ne", "northeast": "ne",
    "nw": "nw", "northwest": "nw",
    "se": "se", "southeast": "se",
    "sw": "sw", "southwest": "sw",
    "up": "up", "u": "up",
    "down": "down", "d": "down",
    "in": "in", "inside": "in", "enter": "in",
    "out": "out", "outside": "out", "exit": "out",
}


def normalize_direction(direction: Any) -> Any:
    """Map a movement direction to its canonical token.

    Accepts direction synonyms/abbreviations ("northeast" -> "ne", "n" ->
    "north", "inside" -> "in", ...) so exits authored with the canonical token
    match however the player or agent phrases the direction. Unknown values
    (and non-strings) pass through unchanged so callers can still report a
    clean no-exit for a genuinely bogus direction.
    """
    if isinstance(direction, str):
        return _DIRECTION_SYNONYMS.get(direction.strip().lower(), direction)
    return direction


@dataclass
class ObjectState:
    """Runtime state for an object.

    Flags are stored as boolean properties with natural names (e.g., :open, :takeable).
    This unifies the data model - everything is a property.
    """
    name: str
    location: str | None
    properties: dict[str, Any]


@dataclass
class GameState:
    """Complete runtime game state."""
    objects: dict[str, ObjectState] = field(default_factory=dict)
    rooms: set[str] = field(default_factory=set)
    queues: dict[str, int | None] = field(default_factory=dict)  # event -> countdown (None = indefinite)

    def copy(self) -> "GameState":
        """Create a deep copy of the state."""
        return deepcopy(self)


@dataclass
class ActionResult:
    """Result of executing an action."""
    outcome: str  # "success", "blocked", "default", "error"
    reason: str | None = None  # For blocked outcomes
    context: list[tuple[str, Any]] = field(default_factory=list)
    default_action: SExpr | None = None  # For default with explicit action
    effects_applied: list[str] = field(default_factory=list)  # Description of effects
    error: str | None = None  # For errors
    redirects: list[SExpr] = field(default_factory=list)  # Chain of redirected actions
    output: list[tuple[str, str | None, str]] = field(default_factory=list)  # [(type, entity, text), ...]
    event_name: str | None = None  # Set when this result came from a fired event (not a player action)


class GrueRuntime:
    """
    Runtime for executing GRUE world definitions.

    Manages game state and dispatches actions to object behaviors.
    Implements MutableWorldState interface for ExprEvaluator/EffectExecutor.
    """

    def __init__(self, world: GrueWorld):
        self.world = world
        self._validate_world()
        self.state = self._init_state()
        self.bindings: dict[str, Any] = {}  # Current action bindings (?with, ?on, self, etc.)
        self.player_name = self.world.player
        self._functions = self._init_functions()  # User-defined functions from world.functions

    def _validate_world(self) -> None:
        """Validate world definition has required structure."""
        if not self.world.player:
            raise ValueError("World must define a player via (world ... :player @name)")
        if self.world.player not in self.world.objects:
            raise ValueError(f"Player '{self.world.player}' not found in world objects")

    def _init_functions(self) -> dict[str, GrueFn]:
        """Initialize user-defined functions from world definition."""
        functions: dict[str, GrueFn] = {}
        for name, grue_func in self.world.functions.items():
            functions[name] = GrueFn(
                params=grue_func.params,
                body=grue_func.body,
            )
        return functions

    def _build_entity_scope(self, nested_forms: list[SExpr]) -> tuple[dict[str, GrueFn], dict[str, Any]]:
        """Build scoped functions and values from nested forms.

        Processes (def ...) and (defn ...) forms that appear inside
        entity definitions (object, room).

        Returns:
            (scoped_functions, scoped_values) - functions and static values
        """
        scoped_functions: dict[str, GrueFn] = {}
        scoped_values: dict[str, Any] = {}

        for form in nested_forms:
            if not isinstance(form, SList) or len(form) < 1:
                continue
            if not isinstance(form[0], Symbol):
                continue

            form_type = form[0].name

            if form_type == "defn":
                # (defn name (params) body)
                if len(form) != 4:
                    continue
                name_sym = form[1]
                if not isinstance(name_sym, Symbol):
                    continue
                name = name_sym.name

                params_expr = form[2]
                params: list[str] = []
                if isinstance(params_expr, SList):
                    for p in params_expr.items:
                        if isinstance(p, Symbol):
                            # Strip leading ? if present
                            param_name = p.name[1:] if p.name.startswith("?") else p.name
                            params.append(param_name)

                body = form[3]
                scoped_functions[name] = GrueFn(params=params, body=body)

            elif form_type == "def":
                # (def name value)
                if len(form) != 3:
                    continue
                name_sym = form[1]
                if not isinstance(name_sym, Symbol):
                    continue
                name = name_sym.name

                # Evaluate value statically
                value_expr = form[2]
                if isinstance(value_expr, (str, int, bool)):
                    scoped_values[name] = value_expr
                elif isinstance(value_expr, Symbol):
                    # Could be reference to global or another scoped value
                    scoped_values[name] = value_expr.name
                elif isinstance(value_expr, SList) and len(value_expr) >= 1:
                    # Handle (quote ...) forms - convert to Python data
                    if isinstance(value_expr[0], Symbol) and value_expr[0].name == "quote":
                        if len(value_expr) == 2:
                            scoped_values[name] = quote_to_data(value_expr[1])
                        else:
                            scoped_values[name] = value_expr
                    else:
                        # Store complex expressions as SExpr for later evaluation
                        scoped_values[name] = value_expr
                else:
                    # Store as SExpr for later evaluation if needed
                    scoped_values[name] = value_expr

        return scoped_functions, scoped_values

    # Implied properties: capability flag -> state property with default value
    # These are semantic implications from ZIL-style flags
    IMPLIED_PROPERTIES: dict[str, tuple[str, Any]] = {
        "openable": ("open", False),      # :openable true implies :open false
        "wearable": ("worn", False),      # :wearable true implies :worn false
        "lightable": ("lit", False),      # :lightable true implies :lit false
    }

    def _add_implied_properties(self, props: dict[str, Any]) -> None:
        """Add implied state properties based on capability flags.

        When an object has a capability flag (like :openable), it implies the
        existence of a state property (like :open) with a default value.
        This allows (:open @door) to work without explicitly declaring :open false.
        """
        for flag, (state_prop, default) in self.IMPLIED_PROPERTIES.items():
            if props.get(flag) and state_prop not in props:
                props[state_prop] = default

    def _init_state(self) -> GameState:
        """Initialize game state from world definition."""
        state = GameState()

        # Initialize rooms (flags become boolean properties)
        for room_name, room in self.world.rooms.items():
            state.rooms.add(room_name)
            props = dict(room.properties)
            # Convert flags to boolean properties
            for flag in room.flags:
                props[flag] = True
            self._add_implied_properties(props)
            state.objects[room_name] = ObjectState(
                name=room_name,
                location=None,  # Rooms don't have locations
                properties=props,
            )

        # Initialize objects (flags become boolean properties)
        for name, obj in self.world.objects.items():
            props = dict(obj.properties)
            # Convert flags to boolean properties
            for flag in obj.flags:
                props[flag] = True
            self._add_implied_properties(props)
            state.objects[name] = ObjectState(
                name=name,
                location=obj.location,
                properties=props,
            )

        # Queue always-on background events (world :start-events) indefinitely,
        # so persistent hazards/clocks (e.g. the ever-lurking grue) are live from
        # turn 1 without a game having to bootstrap them from a room :on-enter.
        for event_name in self.world.start_events:
            state.queues[event_name] = None  # None = indefinite (ZIL -1)

        return state

    def _increment_moves(self) -> None:
        """Increment the moves counter on the player."""
        if self.player_name in self.state.objects:
            props = self.state.objects[self.player_name].properties
            props["moves"] = props.get("moves", 0) + 1

    def reset(self) -> None:
        """Reset game state to initial state."""
        self.state = self._init_state()
        self.bindings = {}
        self._functions = self._init_functions()

    # -------------------------------------------------------------------------
    # MutableWorldState interface - used by ExprEvaluator and EffectExecutor
    # -------------------------------------------------------------------------

    def get_object_location(self, obj: str) -> str | None:
        if obj == self.player_name:
            return self.get_player_location()
        if obj not in self.state.objects:
            return None
        return self.state.objects[obj].location

    def _get_declared_properties(self, obj: str) -> set[str]:
        """Get the set of declared properties for an object.

        Properties are declared via:
        - :properties in the object/room definition
        - :flags in the object/room definition (converted to boolean props)
        - Implied properties from capability flags (e.g., :openable implies :open)
        - Built-in properties: description, location
        """
        declared: set[str] = {"description", "location"}

        props: dict[str, Any] = {}

        # Check world.objects (includes player, NPCs, items)
        if obj in self.world.objects:
            world_obj = self.world.objects[obj]
            declared.update(world_obj.properties.keys())
            declared.update(world_obj.flags)
            props.update(world_obj.properties)
            for flag in world_obj.flags:
                props[flag] = True

        # Check world.rooms
        if obj in self.world.rooms:
            room = self.world.rooms[obj]
            declared.update(room.properties.keys())
            declared.update(room.flags)
            props.update(room.properties)
            for flag in room.flags:
                props[flag] = True

        # Add implied state properties from capability flags
        for flag, (state_prop, _) in self.IMPLIED_PROPERTIES.items():
            if props.get(flag):
                declared.add(state_prop)

        return declared

    def _check_property_declared(self, obj: str, prop: str, operation: str) -> None:
        """Raise error if property is not declared on object.

        Args:
            obj: Object name
            prop: Property name
            operation: "read" or "write" for error message
        """
        declared = self._get_declared_properties(obj)
        if prop not in declared:
            raise ValueError(
                f"Undeclared property {operation}: (:{prop} {obj}). "
                f"Declared properties: {sorted(declared)}"
            )

    def get_object_property(self, obj: str, prop: str) -> Any:
        if obj not in self.state.objects:
            return None

        # Strict mode: check property is declared
        self._check_property_declared(obj, prop, "read")

        # First check runtime state properties (None is a valid value)
        state_props = self.state.objects[obj].properties
        if prop in state_props:
            return state_props[prop]
        # Fall back to world definition properties
        if obj in self.world.objects:
            world_obj = self.world.objects[obj]
            # Check world definition properties too
            if world_obj.properties:
                return world_obj.properties.get(prop)
        return None

    def has_object_property(self, obj: str, prop: str) -> bool:
        """Check if object has a declared property.

        With strict property initialization, this now checks whether the property
        is declared in the world definition, not whether it has a runtime value.
        All declared properties always have values (their initial values).
        """
        if obj not in self.state.objects:
            return False
        return prop in self._get_declared_properties(obj)

    def get_global(self, name: str) -> Any:
        # Check bindings first (for ?self, ?actor, ?with, ?on, etc.)
        if name.startswith("?"):
            binding_name = name[1:]  # Remove ?
            if binding_name in self.bindings:
                return self.bindings[binding_name]
            return None

        # Check entity-scoped values (from (def ...) inside objects/events)
        if name in self.bindings:
            return self.bindings[name]

        # score/moves are player properties
        if name.lower() in ("score", "moves"):
            return self.get_object_property(self.player_name, name.lower()) or 0

        # Check constants (from top-level (def name value))
        if name in self.world.constants:
            const_expr = self.world.constants[name]
            # Evaluate the constant expression (lazy evaluation on first access)
            # Use a temporary evaluator to evaluate the constant
            evaluator = ExprEvaluator(self, self._functions)
            return evaluator.eval(const_expr)

        raise KeyError(f"Unknown global: {name}")

    def get_player_location(self) -> str:
        """Get the player's immediate location (may be a vehicle/container, not room)."""
        player = self.state.objects.get(self.player_name)
        if player:
            return player.location or ""
        return ""

    def get_meta_location(self, obj: str) -> str:
        """Walk up the containment hierarchy to find the room containing an object.

        Like ZIL's META-LOC routine - keeps going up through containers
        until it reaches a room.
        """
        current = obj
        visited = set()  # Prevent infinite loops
        while current and current not in visited:
            visited.add(current)
            # Is this a room?
            if current in self.state.rooms:
                return current
            # Get the location of this object/container
            obj_state = self.state.objects.get(current)
            if not obj_state or not obj_state.location:
                return ""
            # Global objects
            if obj_state.location == "@global":
                return "@global"
            current = obj_state.location
        return ""

    def get_player_room(self) -> str:
        """Get the room the player is in (walking up through any vehicles/containers)."""
        player_loc = self.get_player_location()
        if not player_loc:
            return ""
        # If already in a room, return it
        if player_loc in self.state.rooms:
            return player_loc
        # Otherwise walk up to find the room
        return self.get_meta_location(player_loc)

    def get_player_vehicle(self) -> tuple[str, str] | None:
        """Get the vehicle the player is in, if any.

        Returns (vehicle_name, preposition) where preposition is "in" or "on"
        based on SURFACEBIT flag. Returns None if player is directly in a room.
        """
        player_loc = self.get_player_location()
        if not player_loc or player_loc in self.state.rooms:
            return None
        # Check if player's location is a vehicle
        obj_state = self.state.objects.get(player_loc)
        if obj_state and obj_state.properties.get("vehicle"):
            # Surface means "on", otherwise "in"
            prep = "on" if obj_state.properties.get("surface") else "in"
            return (player_loc, prep)
        return None

    def get_player_name(self) -> str:
        """Get the player entity name."""
        return self.player_name

    def get_inventory(self) -> list[str]:
        """Get objects the player is carrying (excludes INVISIBLE items)."""
        return [
            name for name, obj in self.state.objects.items()
            if obj.location == self.player_name
            and name != self.player_name
            and not obj.properties.get("invisible")
        ]

    def is_visible(self, obj: str) -> bool:
        """Check if object is visible to player.

        Follows ZIL's visibility model (META-LOC pattern):
        - Object's containing room must match player's room
        - Or object is held by player
        - Or player is inside the object (e.g., sitting in a chair)
        - Room :visible list overrides INVISIBLE
        - Contents of open containers/surfaces are visible recursively
        """
        if obj not in self.state.objects:
            return False
        obj_state = self.state.objects[obj]
        loc = obj_state.location

        player_room = self.get_player_room()  # Walk up to actual room
        player_loc = self.get_player_location()  # Immediate location (may be vehicle)

        # Check if object is in current room's :visible list first
        # Room :visible overrides INVISIBLE - they represent "known" scenery
        room_def = self.world.rooms.get(player_room)
        if room_def and obj in room_def.visible:
            return True

        # Check invisible property (only for non-visible objects)
        if obj_state.properties.get("invisible"):
            return False

        if loc is None:
            return False
        # Global objects are always visible
        if loc == "@global":
            return True
        if loc == self.player_name:
            return True
        # Player is inside this object (e.g., sitting in chair)
        if player_loc == obj:
            return True
        # Object's META-LOC must match player's room
        obj_meta_loc = self.get_meta_location(obj)
        if obj_meta_loc != player_room:
            return False
        # Direct location checks: object in room, or in player's vehicle
        if loc == player_room or loc == player_loc:
            return True
        # Check if in a container/on a surface
        if loc in self.state.objects:
            container = self.state.objects[loc]
            # Surface objects make contents always visible
            if container.properties.get("surface") and self.is_visible(loc):
                return True
            # Transparent containers make contents visible even when closed
            if container.properties.get("transparent") and self.is_visible(loc):
                return True
            # Container objects require open to see contents
            if container.properties.get("open") and self.is_visible(loc):
                return True
        return False

    def is_room(self, loc: str) -> bool:
        return loc in self.state.rooms

    def is_object(self, name: str) -> bool:
        """Check if name refers to a known object."""
        return name in self.state.objects

    def get_contents(self, container: str) -> list[str]:
        # TODO: Do we really have to search through everything?!
        return [
            name for name, obj in self.state.objects.items()
            if obj.location == container
        ]

    def get_exit(self, actor: str, direction: str) -> tuple[str, str | None] | None:
        """Get exit info for direction from actor's room. Returns (destination, via) or None."""
        actor_loc = self.get_object_location(actor)
        res = self._get_exit_from_room(actor_loc, direction)
        return (res[0], res[1]) if res else None

    def _get_exit_from_room(
        self, room_name: str | None, direction: str
    ) -> tuple[str | None, str | None, str | None] | None:
        """Get exit info for direction from a specific room.

        Returns (destination, via, blocked_message) or None. For a message-only
        blocked exit (ZIL string/SORRY exit) destination is None and
        blocked_message carries the refusal text.
        """
        room = self.world.rooms.get(room_name) if room_name else None
        if not room:
            return None
        # Normalize both sides so a stored "ne" matches a queried "northeast"
        # (and vice versa for games authored with the long form).
        target = normalize_direction(direction)
        for exit_def in room.exits:
            if normalize_direction(exit_def.direction) == target:
                return (exit_def.to, exit_def.via, exit_def.blocked)
        return None

    def set_object_property(self, obj: str, prop: str, value: Any) -> None:
        if obj in self.state.objects:
            # Strict mode: check property is declared
            self._check_property_declared(obj, prop, "write")
            self.state.objects[obj].properties[prop] = value

    def move_object(self, obj: str, dest: str) -> None:
        if obj in self.state.objects:
            self.state.objects[obj].location = dest

    # -------------------------------------------------------------------------
    # Event queue interface
    # -------------------------------------------------------------------------

    def is_queued(self, event: str) -> bool:
        """Check if an event is currently queued."""
        return event in self.state.queues

    def queue_event(self, event: str, countdown: int | None = None) -> None:
        """Queue an event. countdown=None means indefinite, countdown=N means N turns."""
        self.state.queues[event] = countdown

    def dequeue_event(self, event: str) -> None:
        """Remove an event from the queue."""
        self.state.queues.pop(event, None)

    def get_queue_countdown(self, event: str) -> int | None:
        """Get countdown for queued event, or None if not queued or indefinite."""
        return self.state.queues.get(event)

    # -------------------------------------------------------------------------
    # Turn-based event processing
    # -------------------------------------------------------------------------

    def process_events(self) -> list[ActionResult]:
        """
        Process all queued events that should fire this turn.

        Called at the end of each turn (after action resolution).
        Returns a list of ActionResults from events that fired.

        Events fire if:
        - They are queued (in state.queues)
        - They have a handler defined (in world.events)
        - Location constraint is satisfied (if specified)
        """
        results: list[ActionResult] = []
        player_room = self.get_player_room()

        # Process each queued event
        # Copy queue keys since events may modify the queue
        for event_name in list(self.state.queues.keys()):
            event_def = self.world.events.get(event_name)
            if event_def is None:
                # No handler defined for this event
                continue

            # Check location constraint (compare against room, not immediate location)
            if event_def.location is not None and event_def.location != player_room:
                continue

            # Decrement countdown if present and check if ready to fire.
            #
            # Contract (ZIL CLOCKER-faithful; see games/lurkinghorror/source/
            # misc.zil and yak gnusto-aab0):
            #   countdown=N (N>=1): ONE-SHOT. Decrement each turn; countdown=1
            #     fires this turn, then the event AUTO-DEQUEUES. To repeat, the
            #     event body re-queues itself (the chain idiom).
            #   countdown=0: ONE-SHOT, fires this turn, then auto-dequeues.
            #   countdown=None or negative (ZIL -1): INDEFINITE. Fires every
            #     turn and is never auto-dequeued; the body must (dequeue X).
            countdown = self.state.queues.get(event_name)
            if countdown is not None and countdown > 1:
                self.state.queues[event_name] = countdown - 1
                continue

            # One-shot events auto-dequeue on fire. Remove BEFORE evaluating so
            # that a body which re-queues itself (chain idiom) survives -- this
            # mirrors ZIL clearing C-RTN before APPLY. queue/dequeue effects
            # mutate state.queues synchronously during body evaluation.
            if countdown is not None and countdown >= 0:
                del self.state.queues[event_name]

            # Fire the event. Tag the result with the event name so debug views
            # (agent compact formatter, REPL) can attribute otherwise-causeless
            # effects/output to the event that produced them (gnusto-0bf7.3).
            result = self._evaluate_event(event_def)
            result.event_name = event_name
            results.append(result)

        return results

    def _evaluate_event(self, event: "GrueEvent") -> ActionResult:
        """Evaluate an event's body atomically and return the result.

        Like actions, an event that errors (mid-effect-list, inline mutation, or
        uncaught exception) rolls back to leave NO partial state (gnusto-160b).
        """
        if event.body is None:
            return ActionResult(
                outcome="error",
                error=f"Event {event.name} has no body"
            )

        snapshot = self.state.copy()

        # Build entity scope from nested forms (def, defn)
        entity_scope = None
        if event.nested_forms:
            entity_scope = self._build_entity_scope(event.nested_forms)
            scoped_fns, scoped_vals = entity_scope
            merged_functions = {**self._functions, **scoped_fns}
        else:
            merged_functions = self._functions

        # Events use simple bindings (no direct object)
        bindings = {"actor": self.player_name}
        # Merge scoped values into bindings
        if entity_scope:
            bindings = {**entity_scope[1], **bindings}

        old_bindings = self.bindings
        self.bindings = bindings
        try:
            # NOTE: allow_mutations=True is temporary during migration.
            # Once all events are migrated to pure effect lists (Phase 4),
            # this will become allow_mutations=False.
            evaluator = ExprEvaluator(self, merged_functions, allow_mutations=True)

            try:
                result = evaluator.eval(event.body)
            except Exception as e:
                return self._rollback_if_error(
                    snapshot,
                    ActionResult(
                        outcome="error",
                        error=f"Error evaluating event {event.name}: {e}",
                    ),
                )

            # Convert behavior result to ActionResult (same as behaviors)
            action_result = self._behavior_result_to_action_result(result, evaluator)

            # Check for death in context
            self._check_death_context(action_result)

            return self._rollback_if_error(snapshot, action_result)
        finally:
            self.bindings = old_bindings

    # -------------------------------------------------------------------------
    # High-level convenience methods
    # -------------------------------------------------------------------------

    def is_room_lit(self, room_name: str | None = None) -> bool:
        """Is the given room lit?

        Delegates to the Grue ``(lit? …)`` predicate in builtins.grue (the room's
        own ``:lit`` — defaulting *lit* — OR an accessible light source that is on).
        Darkness is therefore opt-in: a room only goes dark if it declares
        ``:lit false`` and no light source is present. Fails open (lit) so a
        missing/erroring predicate never plunges a game into darkness.
        """
        if room_name is None:
            room_name = self.get_player_room()
        if not room_name:
            return True
        evaluator = ExprEvaluator(self, self._functions)
        env = Environment(bindings={"room": room_name})
        expr = SList([Symbol("lit?"), Symbol("?room")])
        try:
            return is_truthy(evaluator.eval(expr, env))
        except Exception:
            return True

    def get_room_description(self, room_name: str | None = None) -> str:
        """Get a room's description.

        Checks for :describe behavior first (for dynamic descriptions),
        then falls back to ldesc, then description.
        """
        if room_name is None:
            room_name = self.get_player_room()  # Use room, not immediate location
        room = self.world.rooms.get(room_name)
        if not room:
            return ""

        # Darkness: if the player can't see, the room's own prose is replaced by
        # the (game-customizable) dark message. Only affects the player's room.
        if room_name == self.get_player_room() and not self.is_room_lit(room_name):
            return self.world.dark_message

        # Check for :describe behavior (dynamic description)
        describe_behavior = None
        for b in room.behaviors:
            if b.verb == "describe":
                describe_behavior = b
                break

        if describe_behavior is not None:
            # Evaluate the :describe behavior
            bindings = {"self": room_name}
            entity_scope = self._build_entity_scope(room.nested_forms)
            result = self._evaluate_behavior(describe_behavior, bindings, entity_scope)

            # Extract description from context
            if result.context:
                for key, value in result.context:
                    if key == "description":
                        return str(value)

        # Fall back to ldesc (may be static string or dynamic fn)
        if room.ldesc:
            return self._evaluate_ldesc(room_name, room.ldesc)
        return room.description

    def get_object_description(self, obj_name: str) -> str:
        """Get an object's short description (name)."""
        obj = self.world.objects.get(obj_name)
        if obj:
            return obj.description
        return ""

    def get_ldesc(self, entity: str) -> SExpr | None:
        """Get entity's raw ldesc (string or fn expression).

        Returns the unevaluated ldesc - caller is responsible for
        evaluating if it's a function.
        """
        # Check rooms first
        if entity in self.world.rooms:
            return self.world.rooms[entity].ldesc
        # Then objects
        if entity in self.world.objects:
            return self.world.objects[entity].ldesc
        return None

    def get_description(self, entity: str) -> SExpr | None:
        """Get entity's raw description (string or fn expression).

        Returns the unevaluated description - caller is responsible for
        evaluating if it's a function.
        """
        # Check rooms first
        if entity in self.world.rooms:
            return self.world.rooms[entity].description
        # Then objects
        if entity in self.world.objects:
            return self.world.objects[entity].description
        return None

    def _evaluate_ldesc(self, entity_name: str, ldesc: SExpr) -> str:
        """Evaluate an ldesc value (string or fn) to produce a string.

        Args:
            entity_name: The entity whose ldesc this is (for ?self binding)
            ldesc: The ldesc value - either a string or (fn () body)

        Returns:
            The evaluated description string
        """
        # String: return directly
        if isinstance(ldesc, str):
            return ldesc

        # Function: evaluate with ?self bound
        if isinstance(ldesc, SList) and len(ldesc) >= 1:
            first = ldesc[0]
            if isinstance(first, Symbol) and first.name == "fn":
                # Parse and evaluate the fn
                if len(ldesc) >= 3:
                    body = ldesc[2]
                    evaluator = ExprEvaluator(self, self._functions)
                    env = Environment(bindings={"self": entity_name})
                    result = evaluator.eval(body, env)
                    return str(result) if result is not None else ""

        # Other expression: try to evaluate it
        evaluator = ExprEvaluator(self, self._functions)
        env = Environment(bindings={"self": entity_name})
        result = evaluator.eval(ldesc, env)
        return str(result) if result is not None else ""

    def get_object_fdesc(self, obj_name: str) -> str:
        """Get an object's description for room listings.

        Checks for :describe behavior first (for dynamic descriptions),
        then falls back to ldesc.
        """
        obj = self.world.objects.get(obj_name)
        if not obj:
            return ""

        # Check for :describe behavior (dynamic description)
        describe_behavior = None
        for b in obj.behaviors:
            if b.verb == "describe":
                describe_behavior = b
                break

        if describe_behavior is not None:
            # Evaluate the :describe behavior
            bindings = {"self": obj_name}
            entity_scope = self._build_entity_scope(obj.nested_forms)
            result = self._evaluate_behavior(describe_behavior, bindings, entity_scope)

            # Extract description from context
            if result.context:
                for key, value in result.context:
                    if key == "description":
                        return str(value)

        # Fall back to ldesc (which may be dynamic)
        if obj.ldesc:
            return self._evaluate_ldesc(obj_name, obj.ldesc)
        return ""

    def get_visible_objects(self, for_description: bool = True) -> list[str]:
        """Get objects visible to the player.

        Returns a flat list of ALL visible objects, including container contents.
        For room-level display (excluding inventory and nested contents), use
        get_room_level_objects() instead.

        Args:
            for_description: If True, exclude NDESCBIT objects (for room listings).
                            If False, include all visible objects (for interaction).
        """
        # Darkness only suppresses the *room listing* (for_description); it does
        # not change raw accessibility (is_visible), so a game/player can still
        # act on known objects by name in the dark — the deterrent is the grue.
        if for_description and not self.is_room_lit():
            return []
        result = []
        for name in self.state.objects:
            if name == self.player_name:
                continue
            if not self.is_visible(name):
                continue
            if for_description:
                obj_state = self.state.objects[name]
                if obj_state.properties.get("nodesc"):
                    continue
            result.append(name)
        return result

    def get_room_level_objects(self, for_description: bool = True) -> list[str]:
        """Get objects visible at room level, excluding inventory and nested contents.

        Follows ZIL's DESCRIBE-OBJECTS pattern: only objects directly in the room,
        in the player's vehicle, or in the room's :visible list. Contents of held
        containers are NOT included (they belong to the inventory tree).

        Args:
            for_description: If True, exclude NDESCBIT objects (for room listings).
                            If False, include all visible objects (for interaction).
        """
        room = self.get_player_room()
        player_loc = self.get_player_location()
        top_level_locs = {room}
        if player_loc and player_loc != room:
            top_level_locs.add(player_loc)

        room_def = self.world.rooms.get(room)
        room_visible = set(room_def.visible) if room_def else set()

        inventory = set(self.get_inventory())

        result = []
        for name in self.get_visible_objects(for_description=for_description):
            if name in inventory:
                continue
            obj_state = self.state.objects.get(name)
            if not obj_state:
                continue
            if obj_state.location in top_level_locs or name in room_visible:
                result.append(name)
        return result

    def get_exits(self) -> dict[str, str]:
        """Get available exits from the current room."""
        room = self.world.rooms.get(self.get_player_room())  # Use room, not immediate location
        if not room:
            return {}
        # Message-only blocked exits (no destination) aren't traversable exits.
        return {exit.direction: exit.to for exit in room.exits if exit.to}

    def _resolve_symbol(self, sym: Symbol) -> str:
        """Resolve a symbol, looking up ?-prefixed names in bindings."""
        name = sym.name
        if name.startswith("?"):
            # Look up in current bindings
            binding_name = name[1:]  # Strip the ?
            if binding_name in self.bindings:
                return self.bindings[binding_name]
        return name

    def _parse_action_sexpr(self, action: SExpr | list) -> tuple[str, str, list[Any]]:
        """Parse an action S-expression into (target, verb, args).

        Format: (do TARGET :verb arg1 arg2 ...)

        Examples:
            (do @hacker :give @food)  -> ("@hacker", "give", ["@food"])
            (do @lamp :examine)       -> ("@lamp", "examine", [])
            (do (loc @player) :go up) -> evaluates (loc @player) first
            (do ?self :login ?value)  -> resolves ?self and ?value from bindings

        Accepts both SList (from parsed code) and Python lists (from quoted expressions).
        """
        # Handle both SList and Python lists
        if isinstance(action, SList):
            items = list(action.items)
        elif isinstance(action, list):
            items = action
        else:
            raise ValueError(f"Invalid action format: {action}")

        if len(items) < 3:
            raise ValueError(f"Invalid action format: {action}")

        # First item should be 'do' (Symbol or string)
        first = items[0]
        if isinstance(first, Symbol):
            if first.name != "do":
                raise ValueError(f"Action must start with 'do': {first}")
        elif isinstance(first, str):
            if first != "do":
                raise ValueError(f"Action must start with 'do': {first}")
        else:
            raise ValueError(f"Action must start with 'do': {first}")

        # Second item is target - evaluate if it's an expression or resolve symbol
        if isinstance(items[1], Symbol):
            target = self._resolve_symbol(items[1])
        elif isinstance(items[1], str):
            # String target (from quoted expressions)
            target = items[1]
        elif isinstance(items[1], SList):
            # Evaluate the expression to get the target
            evaluator = ExprEvaluator(self, self._functions)
            target = evaluator.eval(items[1])
            if not isinstance(target, str):
                raise ValueError(f"Target expression must evaluate to a string: {items[1]} -> {target}")
        else:
            raise ValueError(f"Target must be a symbol or expression: {items[1]}")

        # Third item is verb (keyword)
        if not isinstance(items[2], Keyword):
            raise ValueError(f"Verb must be a keyword: {items[2]}")
        verb = items[2].name

        # Remaining items are positional args - evaluate expressions and resolve symbols
        args: list[Any] = []
        evaluator = ExprEvaluator(self, self._functions)
        for i in range(3, len(items)):
            item = items[i]
            if isinstance(item, Symbol):
                args.append(self._resolve_symbol(item))
            elif isinstance(item, SList):
                # Evaluate expression
                args.append(evaluator.eval(item))
            else:
                args.append(item)

        return target, verb, args

    def _rollback_if_error(self, snapshot: "GameState", result: ActionResult) -> ActionResult:
        """Restore ``snapshot`` if ``result`` is an error, so a failed action or
        event leaves NO partial state (gnusto-160b). A mid-list effect error would
        otherwise commit the effects that ran before it (e.g. the hacker-returns
        bug advanced :lair-cnt before the undeclared :invisible write aborted)."""
        if result.outcome == "error":
            self.state = snapshot
        return result

    def do(
        self,
        target: str,
        verb: str,
        *args,
        _redirects: list[SExpr] | None = None,
        _max_redirects: int = 10,
    ) -> ActionResult:
        """Execute a player action atomically (all-or-nothing).

        Only the outermost call is a transaction boundary; nested redirect calls
        share it, so a redirect chain that errors part-way rolls back entirely.
        On an uncaught exception or an error outcome, state is restored to the
        pre-action snapshot (gnusto-160b).
        """
        if _redirects is not None:
            return self._do_impl(
                target, verb, *args, _redirects=_redirects, _max_redirects=_max_redirects
            )
        snapshot = self.state.copy()
        try:
            result = self._do_impl(
                target, verb, *args, _redirects=[], _max_redirects=_max_redirects
            )
        except Exception as e:
            self.state = snapshot
            return ActionResult(
                outcome="error", error=f"Uncaught error in ({verb} {target}): {e}"
            )
        return self._rollback_if_error(snapshot, result)

    def _do_impl(
        self,
        target: str,
        verb: str,
        *args,
        _redirects: list[SExpr] | None = None,
        _max_redirects: int = 10,
    ) -> ActionResult:
        """
        Execute an action, following any redirects automatically.

        New signature: (do TARGET :verb arg1 arg2 ...)

        Args:
            target: The object whose behavior to invoke (e.g., "HACKER", "DOOR")
            verb: The verb (e.g., "give", "examine", "go")
            *args: Positional arguments bound to behavior params
            _redirects: Internal - chain of redirects followed (for loop detection)
            _max_redirects: Internal - maximum redirect depth

        Auto-bound symbols:
            ?self  - The target object
            ?actor - Who is performing the action (currently always player)

        Returns:
            ActionResult with outcome and details. The 'redirects' field contains
            the chain of redirected actions for narrative purposes.
        """
        if _redirects is None:
            _redirects = []

        result = self._do_single(target, verb, *args)

        # Follow redirects automatically
        if result.outcome == "redirect" and result.default_action is not None:
            # Check for redirect loops
            action_str = to_string(result.default_action)
            for prev in _redirects:
                if to_string(prev) == action_str:
                    return ActionResult(
                        outcome="error",
                        error=f"Redirect loop detected: {action_str}",
                        redirects=_redirects
                    )

            # Check max redirects
            if len(_redirects) >= _max_redirects:
                return ActionResult(
                    outcome="error",
                    error=f"Too many redirects (max {_max_redirects})",
                    redirects=_redirects
                )

            # Record this redirect
            _redirects.append(result.default_action)

            # Parse the redirect action and follow it
            try:
                new_target, new_verb, new_args = self._parse_action_sexpr(result.default_action)
                final_result = self.do(
                    new_target,
                    new_verb,
                    *new_args,
                    _redirects=_redirects,
                    _max_redirects=_max_redirects,
                )
                # Preserve redirect chain and merge context
                final_result.redirects = _redirects
                # Prepend redirect context to final context
                if result.context:
                    final_result.context = result.context + final_result.context
                return final_result
            except ValueError as e:
                return ActionResult(
                    outcome="error",
                    error=f"Invalid redirect action: {e}",
                    redirects=_redirects
                )

        # Not a redirect - return result with any accumulated redirects
        result.redirects = _redirects

        # Check for death in context and set player:dead automatically
        self._check_death_context(result)

        return result

    def _do_single(
        self,
        target: str,
        verb: str,
        *args,
    ) -> ActionResult:
        """Execute a single action without following redirects.

        Args:
            target: The object whose behavior to invoke
            verb: The verb (behavior name)
            *args: Positional arguments for the behavior's params
        """
        actor = self.player_name

        # Handle movement specially - target is a pseudo-object
        if verb == "go":
            if not args:
                return ActionResult(
                    outcome="error",
                    error="go requires a direction"
                )
            # Normalize synonyms (northeast->ne, n->north, inside->in, ...) up
            # front so both the room :before-action check and exit resolution
            # see the canonical token.
            direction = normalize_direction(args[0])
            # Check room's :before-action for movement (verb="go", target=direction)
            # Only short-circuit if result is blocking (blocked, error, redirect)
            # A 'success' from before-action means "proceed with the movement"
            room_result = self._check_room_before_action("go", direction, actor, ())
            if room_result is not None and room_result.outcome in ("blocked", "error", "redirect"):
                return room_result
            return self._do_go(direction, actor=actor)

        # Check room's :before-action behavior (if any)
        # Only short-circuit if result is blocking (blocked, error, redirect)
        # A 'success' from before-action means "proceed with the main action"
        room_result = self._check_room_before_action(verb, target, actor, args)
        if room_result is not None and room_result.outcome in ("blocked", "error", "redirect"):
            return room_result

        # Check visibility - object must be accessible to the player
        # Skip check for: player acting on self, :through (barrier checks)
        if target != actor and verb != "through" and not self.is_visible(target):
            return ActionResult(
                outcome="blocked",
                reason="not-here",
                context=[("object", target), ("message", "You can't see any such thing.")]
            )

        # Get the object's definition
        obj_def = self.world.objects.get(target)
        if obj_def is None:
            return ActionResult(
                outcome="error",
                error=f"Unknown object: {target}"
            )

        # Find the behavior for this verb
        behavior = None
        for b in obj_def.behaviors:
            if b.verb == verb:
                behavior = b
                break

        if behavior is None:
            # Try default behaviors based on flags
            default_result = self._try_default_behavior(verb, target, actor, args)
            if default_result is not None:
                return default_result

            return ActionResult(
                outcome="blocked",
                reason="no-behavior",
                context=[("verb", verb), ("object", target)]
            )

        # Check arity
        if len(args) < len(behavior.params):
            return ActionResult(
                outcome="error",
                error=f"{verb} on {target} requires {len(behavior.params)} args, got {len(args)}"
            )

        # Set up bindings for evaluation
        # Auto-bound: ?self, ?actor, ?value (first positional arg for convenience)
        # Positional: behavior.params[i] = args[i]
        bindings = {
            "self": target,
            "actor": actor,
        }
        # Bind ?value to first positional arg if any (convenience for simple behaviors)
        if args:
            bindings["value"] = args[0]
        for i, param in enumerate(behavior.params):
            bindings[param] = args[i]

        # Build entity scope from nested forms
        entity_scope = self._build_entity_scope(obj_def.nested_forms)

        # Evaluate behavior cases
        result = self._evaluate_behavior(behavior, bindings, entity_scope)

        # If behavior returns 'default' with no action, fall through to default behavior
        if result.outcome == "default" and result.default_action is None:
            default_result = self._try_default_behavior(verb, target, actor, args)
            if default_result is not None:
                return default_result

        return result

    def _check_room_before_action(
        self,
        verb: str,
        target: str,
        actor: str,
        args: tuple,
    ) -> ActionResult | None:
        """Check if current room has a :before-action behavior that intercepts this action.

        Args:
            verb: The action verb
            target: The target object
            actor: Who is performing the action
            args: Additional arguments to the action

        Returns:
            ActionResult if room behavior intercepts (blocked/redirect/etc),
            ActionResult with outcome="default" to proceed normally,
            or None if room has no :before-action behavior.
        """
        # Get current room
        player_loc = self.get_player_location()
        room = self.world.rooms.get(player_loc)
        if room is None:
            return None

        # Find :before-action behavior
        before_action = None
        for b in room.behaviors:
            if b.verb == "before-action":
                before_action = b
                break

        if before_action is None:
            return None

        # Set up bindings
        # :before-action (fn (?verb ?target) ...) or (fn (?verb ?target ?args) ...)
        bindings = {
            "actor": actor,
        }

        # Bind positional params
        param_values = [verb, target] + list(args)
        for i, param in enumerate(before_action.params):
            if i < len(param_values):
                bindings[param] = param_values[i]

        # Build entity scope from nested forms
        entity_scope = self._build_entity_scope(room.nested_forms)

        # Evaluate the behavior
        return self._evaluate_behavior(before_action, bindings, entity_scope)

    def _check_room_on_enter(
        self,
        room_name: str,
        from_room: str,
        actor: str,
    ) -> ActionResult | None:
        """Check if a room has an :on-enter behavior and execute it.

        Args:
            room_name: The room being entered
            from_room: The room being left
            actor: Who is entering

        Returns:
            ActionResult if room has :on-enter behavior,
            or None if room has no :on-enter behavior.
        """
        room = self.world.rooms.get(room_name)
        if room is None:
            return None

        # Find :on-enter behavior
        on_enter = None
        for b in room.behaviors:
            if b.verb == "on-enter":
                on_enter = b
                break

        if on_enter is None:
            return None

        # Set up bindings
        # :on-enter (fn (?from-room) ...)
        # ?self is the room being entered
        bindings = {
            "self": room_name,
            "actor": actor,
        }

        # Bind positional params (typically just ?from-room)
        param_values = [from_room]
        for i, param in enumerate(on_enter.params):
            if i < len(param_values):
                bindings[param] = param_values[i]

        # Build entity scope from nested forms
        entity_scope = self._build_entity_scope(room.nested_forms)

        # Evaluate the behavior
        return self._evaluate_behavior(on_enter, bindings, entity_scope)

    def _try_default_behavior(
        self,
        verb: str,
        obj_name: str,
        actor: str | None = None,
        args: tuple = ()
    ) -> ActionResult | None:
        """
        Try default behaviors defined in world.defaults.

        Args:
            verb: The action verb
            obj_name: Target object
            actor: Who is performing the action (default: player entity)
            args: Additional positional arguments (e.g., container for 'put')

        Returns ActionResult if a default applies, None otherwise.
        """
        if actor is None:
            actor = self.player_name

        # Check if there's a default behavior for this verb
        default_behavior = self.world.defaults.get(verb)
        if default_behavior is None:
            return None

        # Set up bindings for evaluation
        bindings = {
            "self": obj_name,
            "actor": actor,
        }
        # Bind ?value to first positional arg if any (convenience for simple behaviors)
        if args:
            bindings["value"] = args[0]

        # Evaluate the default behavior
        return self._evaluate_behavior(default_behavior, bindings)

    def _do_go(self, direction: str, actor: str | None = None) -> ActionResult:
        """Handle movement.

        Vehicle handling:
        - Portable vehicles (boats, etc.): vehicle moves with actor inside
        - Furniture vehicles (chairs, etc.): actor auto-exits first, then walks

        The :furniture property distinguishes stationary vehicles from portable ones.
        """
        if actor is None:
            actor = self.player_name

        # Idempotent for calls routed through _do_single; normalizes synonyms
        # for any direct caller (REPL, tests).
        direction = normalize_direction(direction)

        # Check if actor is in a vehicle
        vehicle_info = self.get_player_vehicle() if actor == self.player_name else None
        in_vehicle = vehicle_info is not None
        auto_exit_message = None  # Track if we auto-exited furniture

        if in_vehicle:
            vehicle_name = vehicle_info[0]
            vehicle_obj = self.state.objects.get(vehicle_name)
            if not vehicle_obj:
                return ActionResult(
                    outcome="error",
                    error=f"Vehicle {vehicle_name} not found"
                )

            # Check if this is furniture (stationary vehicle)
            # Furniture requires the actor to exit before walking
            if vehicle_obj.properties.get("furniture"):
                # Auto-exit: move actor to vehicle's location
                vehicle_room = vehicle_obj.location
                self.state.objects[actor].location = vehicle_room
                # Get description for message
                vehicle_def = self.world.objects.get(vehicle_name)
                vehicle_desc = vehicle_def.description if vehicle_def else vehicle_name
                auto_exit_message = f"First, you arise from the {vehicle_desc}."
                # Now actor is no longer in a vehicle
                in_vehicle = False
                from_room = vehicle_room
            else:
                # Portable vehicle - will move with actor
                from_room = vehicle_obj.location
                if not from_room:
                    return ActionResult(
                        outcome="error",
                        error=f"Vehicle {vehicle_name} has no location"
                    )
        else:
            # Capture current location before move (for :on-enter)
            from_room = self.state.objects[actor].location

        # Get exit - use vehicle's room if in vehicle
        exit_info = self._get_exit_from_room(from_room, direction)
        if exit_info is None:
            return ActionResult(
                outcome="blocked",
                reason="no-exit",
                context=[("direction", direction)]
            )

        dest, via, blocked_msg = exit_info

        # Message-only blocked exit (ZIL string/SORRY exit): refuse with the
        # authored message and no destination.
        if dest is None and blocked_msg is not None:
            return ActionResult(
                outcome="blocked",
                reason="no-exit",
                context=[("direction", direction), ("message", blocked_msg)],
            )

        # Check if exit has a :via door
        if via:
            # Call barrier's :through behavior with destination info
            # Bindings: ?dest = destination room, ?from = current room
            result = self._do_single(via, "through", dest, from_room)
            if result.outcome == "blocked":
                return result
            if result.outcome == "redirect":
                # Check for redirect_to in context - this redirects the destination
                redirect_dest = None
                for key, val in result.context:
                    if key == "redirect_to":
                        redirect_dest = val
                        break
                if redirect_dest:
                    # Use the redirected destination instead of the original
                    dest = redirect_dest
                    # Filter out redirect_to from context
                    context = [(k, v) for k, v in result.context if k != "redirect_to"]
                else:
                    # Redirect to a do action - not allowed in :through
                    return ActionResult(
                        outcome="error",
                        error=f":through behaviors should use (redirect :to @room), not action redirects"
                    )
            elif result.outcome not in ("success", "default"):
                return result  # Pass through errors
            else:
                # Door approved - continue to movement below
                context = list(result.context) if result.context else []
        else:
            context = []

        # Add auto-exit message if we exited furniture
        if auto_exit_message:
            context = [("auto_exit", auto_exit_message)] + context

        # Move the appropriate entity
        if in_vehicle:
            # Move the vehicle; actor stays in the vehicle
            vehicle_name = vehicle_info[0]
            self.state.objects[vehicle_name].location = dest
            effects = [f"{vehicle_name} moved to {dest}" + (f" (via {via})" if via else "")]
        else:
            # Move actor directly
            self.state.objects[actor].location = dest
            effects = [f"{actor} moved to {dest}" + (f" (via {via})" if via else "")]

        self._increment_moves()

        # Check for :on-enter behavior in destination room
        output: list = []
        on_enter_result = self._check_room_on_enter(dest, from_room, actor)
        if on_enter_result is not None:
            # Merge on-enter effects, context, and player-facing output. The
            # output stream matters: a room's :on-enter (narrate ...) (e.g. the
            # cellar trap door slamming shut) would otherwise be silently lost.
            if on_enter_result.effects_applied:
                effects.extend(on_enter_result.effects_applied)
            if on_enter_result.context:
                context = context + on_enter_result.context
            if on_enter_result.output:
                output.extend(on_enter_result.output)

        return ActionResult(
            outcome="success",
            effects_applied=effects,
            context=context,
            output=output,
        )

    def _evaluate_behavior(
        self,
        behavior: GrueBehavior,
        bindings: dict[str, Any],
        entity_scope: tuple[dict[str, GrueFn], dict[str, Any]] | None = None
    ) -> ActionResult:
        """Evaluate a behavior's body and return the result.

        Args:
            behavior: The behavior to evaluate
            bindings: Variable bindings (?self, ?actor, params)
            entity_scope: Optional (scoped_functions, scoped_values) from entity's nested forms
        """
        if behavior.body is None:
            return ActionResult(
                outcome="error",
                error=f"Behavior {behavior.verb} has no body"
            )

        # Build merged functions dict: entity scope overrides global
        if entity_scope:
            scoped_fns, scoped_vals = entity_scope
            merged_functions = {**self._functions, **scoped_fns}
            # Add scoped values to bindings
            bindings = {**scoped_vals, **bindings}
        else:
            merged_functions = self._functions

        # Set bindings for this evaluation (restored after)
        old_bindings = self.bindings
        self.bindings = bindings
        try:
            # NOTE: allow_mutations=True is temporary during migration.
            # Once all behaviors are migrated to pure effect lists (Phase 4),
            # this will become allow_mutations=False.
            evaluator = ExprEvaluator(self, merged_functions, allow_mutations=True)
            return self._evaluate_behavior_body(behavior, bindings, evaluator)
        finally:
            self.bindings = old_bindings

    def _evaluate_behavior_body(
        self,
        behavior: GrueBehavior,
        bindings: dict[str, Any],
        evaluator: ExprEvaluator
    ) -> ActionResult:
        """Evaluate a behavior using its body expression."""
        # Create a GrueFn from the behavior with captured environment
        # This allows ?self, ?actor, and other bindings to be accessible
        fn = GrueFn(
            params=behavior.params,
            body=behavior.body,
            captured_env=Environment(bindings=dict(bindings))
        )

        # Build argument list from bindings in param order
        args = [bindings.get(p) for p in behavior.params]

        try:
            result = evaluator.call_fn(fn, args)
        except Exception as e:
            return ActionResult(
                outcome="error",
                error=f"Error evaluating behavior: {e}"
            )

        # Convert behavior result to ActionResult
        return self._behavior_result_to_action_result(result, evaluator)

    def _behavior_result_to_action_result(
        self,
        result: Any,
        evaluator: ExprEvaluator
    ) -> ActionResult:
        """Convert a BehaviorSuccess/Blocked/etc. or effect list to ActionResult.

        Supports two formats:
        1. Simple outcomes: BehaviorSuccess/Blocked/Redirect/Default objects
        2. Effect lists: Quoted list of effect descriptors '((move @x @y) (success))
        """
        # Effect list syntax: behavior returned a quoted list
        if isinstance(result, (list, SList)):
            return self._process_effect_list(result)

        if isinstance(result, BehaviorSuccess):
            self._increment_moves()
            return ActionResult(
                outcome="success",
                context=list(result.context.items()),
            )

        if isinstance(result, BehaviorBlocked):
            return ActionResult(
                outcome="blocked",
                reason=result.reason,
                context=list(result.context.items()),
            )

        if isinstance(result, BehaviorRedirect):
            return ActionResult(
                outcome="redirect",
                default_action=result.action,
                context=list(result.context.items())
            )

        if isinstance(result, BehaviorDefault):
            return ActionResult(
                outcome="default",
                default_action=result.action,
                context=list(result.context.items())
            )

        # Unknown result type - treat as error
        return ActionResult(
            outcome="error",
            error=f"Behavior returned unexpected type: {type(result).__name__}"
        )

    def _process_effect_list(self, effects: list | SList) -> ActionResult:
        """Process a list of effect descriptors using EffectInterpreter.

        This is the new pure effects model where behaviors return quoted
        effect lists like: '((move @key @player) (success :message "Found!"))

        Args:
            effects: List of effect descriptors

        Returns:
            ActionResult with outcome and applied effects
        """
        # Capture player location before effects (for on-enter handling)
        player_loc_before = self.state.objects[self.player_name].location

        try:
            # Pass current bindings so ?actor, ?self, etc. get resolved
            # Pass functions so nested expressions like (door-at-elevator) can be evaluated
            interpreter = EffectInterpreter(self, self.bindings, self._functions)
            outcome = interpreter.interpret(list(effects))
        except Exception as e:
            return ActionResult(
                outcome="error",
                error=f"Error processing effect list: {e}"
            )

        # Check if player was moved - need to trigger on-enter
        player_loc_after = self.state.objects[self.player_name].location
        if player_loc_after != player_loc_before:
            on_enter_result = self._check_room_on_enter(
                player_loc_after, player_loc_before, self.player_name
            )
            if on_enter_result is not None:
                # Merge on-enter effects and context
                if on_enter_result.effects_applied:
                    outcome.effects_applied.extend(on_enter_result.effects_applied)
                if on_enter_result.context:
                    for key, value in on_enter_result.context:
                        outcome.context[key] = value

        # Increment moves for successful actions
        if outcome.outcome == "success":
            self._increment_moves()

        # Convert EffectOutcome to ActionResult
        # EffectOutcome stores message in context dict
        context = [(key, value) for key, value in outcome.context.items()]
        if outcome.reason:
            context.append(("reason", outcome.reason))

        return ActionResult(
            outcome=outcome.outcome,
            reason=outcome.reason,
            default_action=outcome.redirect_action,
            context=context,
            effects_applied=outcome.effects_applied,
            output=outcome.output
        )

    def _check_death_context(self, result: ActionResult):
        """Check if result context contains (death true) and set player:dead.

        This allows games to signal death via context without explicitly
        setting the player:dead property in every death case.
        """
        if not result.context:
            return

        for key, value in result.context:
            # Check for death=true (handles both boolean True and string "True")
            if key == "death" and value in (True, "True", "true"):
                # Set player dead property (stored without colon prefix)
                player = self.player_name
                if player and player in self.state.objects:
                    self.state.objects[player].properties["dead"] = True
                return

    def check_victory(self) -> bool:
        """Check if victory condition is met."""
        if self.world.victory is None:
            return False

        evaluator = ExprEvaluator(self, self._functions)

        try:
            return is_truthy(evaluator.eval(self.world.victory.when))
        except Exception:
            return False

    def check_defeat(self) -> str | None:
        """Check if any defeat condition is met. Returns defeat name or None."""
        evaluator = ExprEvaluator(self, self._functions)

        for name, defeat in self.world.defeat.items():
            try:
                if is_truthy(evaluator.eval(defeat.when)):
                    return name
            except Exception:
                continue

        return None
