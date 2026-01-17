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
    BehaviorSuccess, BehaviorBlocked, BehaviorRedirect, BehaviorDefault
)
from .sexpr import SExpr, Symbol, SList, Keyword, to_string


@dataclass
class ObjectState:
    """Runtime state for an object."""
    name: str
    location: str | None
    flags: set[str]
    properties: dict[str, Any]


@dataclass
class GameState:
    """Complete runtime game state."""
    objects: dict[str, ObjectState] = field(default_factory=dict)
    rooms: set[str] = field(default_factory=set)
    globals: dict[str, Any] = field(default_factory=dict)
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


class GrueRuntime:
    """
    Runtime for executing GRUE world definitions.

    Manages game state and dispatches actions to object behaviors.
    Implements MutableWorldState interface for ExprEvaluator/EffectExecutor.
    """

    def __init__(self, world: GrueWorld):
        self.world = world
        self.state = self._init_state()
        self.bindings: dict[str, Any] = {}  # Current action bindings (?with, ?on, self, etc.)
        self.player_name = self._find_player_name()  # Detect player entity by PERSON flag
        self._functions = self._init_functions()  # User-defined functions from world.functions

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

    def _init_state(self) -> GameState:
        """Initialize game state from world definition."""
        state = GameState()

        # Initialize rooms (as objects with flags)
        for room_name, room in self.world.rooms.items():
            state.rooms.add(room_name)
            state.objects[room_name] = ObjectState(
                name=room_name,
                location=None,  # Rooms don't have locations
                flags=set(room.flags),
                properties=dict(room.properties),
            )

        # Initialize objects
        for name, obj in self.world.objects.items():
            state.objects[name] = ObjectState(
                name=name,
                location=obj.location,
                flags=set(obj.flags),
                properties=dict(obj.properties),
            )

        # Initialize globals from world definition
        state.globals.update(self.world.globals)

        # Set default globals if not already defined
        state.globals.setdefault("score", 0)
        state.globals.setdefault("moves", 0)

        return state

    def _find_player_name(self) -> str:
        """Find the player entity.

        Uses explicit :player declaration from world if present,
        otherwise falls back to finding object with PERSON flag.
        """
        # Prefer explicit declaration
        if self.world.player:
            return self.world.player

        # Fallback: find by PERSON flag (for backwards compatibility)
        for name, obj in self.state.objects.items():
            if "PERSON" in obj.flags and name not in self.state.rooms:
                return name
        return "PLAYER"  # Last resort fallback  # Fallback

    def reset(self) -> None:
        """Reset game state to initial state."""
        self.state = self._init_state()
        self.bindings = {}
        self._functions = self._init_functions()
        self.player_name = self._find_player_name()

    # -------------------------------------------------------------------------
    # MutableWorldState interface - used by ExprEvaluator and EffectExecutor
    # -------------------------------------------------------------------------

    def get_object_flag(self, obj: str, flag: str) -> bool:
        if obj not in self.state.objects:
            return False
        return flag in self.state.objects[obj].flags

    def get_object_location(self, obj: str) -> str | None:
        if obj == self.player_name:
            return self.get_player_location()
        if obj not in self.state.objects:
            return None
        return self.state.objects[obj].location

    def get_object_property(self, obj: str, prop: str) -> Any:
        if obj not in self.state.objects:
            return None
        # First check runtime state properties
        result = self.state.objects[obj].properties.get(prop)
        if result is not None:
            return result
        # Fall back to world definition for static properties like description
        if obj in self.world.objects:
            world_obj = self.world.objects[obj]
            if prop == "description":
                return world_obj.description
            # Check world definition properties too
            if world_obj.properties:
                return world_obj.properties.get(prop)
        return None

    def get_object_flags(self, obj: str) -> set[str]:
        if obj not in self.state.objects:
            return set()
        return self.state.objects[obj].flags

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

        # Then check globals
        if name.lower() in ("score", "moves"):
            return self.state.globals.get(name.lower(), 0)
        if name in self.state.globals:
            return self.state.globals[name]

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
        # Check if player's location has VEHBIT
        obj_state = self.state.objects.get(player_loc)
        if obj_state and "VEHBIT" in obj_state.flags:
            # SURFACEBIT means "on", otherwise "in"
            prep = "on" if "SURFACEBIT" in obj_state.flags else "in"
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
            and "INVISIBLE" not in obj.flags
        ]

    def is_visible(self, obj: str) -> bool:
        """Check if object is visible to player.

        Follows ZIL's visibility model (META-LOC pattern):
        - Object's containing room must match player's room
        - Or object is held by player
        - Or player is inside the object (e.g., sitting in a chair)
        - Room globals override INVISIBLE
        - Contents of open containers/surfaces are visible recursively
        """
        if obj not in self.state.objects:
            return False
        obj_state = self.state.objects[obj]
        loc = obj_state.location

        player_room = self.get_player_room()  # Walk up to actual room
        player_loc = self.get_player_location()  # Immediate location (may be vehicle)

        # Check if object is in current room's :globals list first
        # Room globals override INVISIBLE - they represent "known" scenery
        room_def = self.world.rooms.get(player_room)
        if room_def and obj in room_def.globals:
            return True

        # Check INVISIBLE flag (only for non-global objects)
        if "INVISIBLE" in obj_state.flags:
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
            # Surface objects (SURFACEBIT) make contents always visible
            if "SURFACEBIT" in container.flags and self.is_visible(loc):
                return True
            # Transparent containers (TRANSBIT) make contents visible even when closed
            if "TRANSBIT" in container.flags and self.is_visible(loc):
                return True
            # Container objects require OPENBIT to see contents
            if "OPENBIT" in container.flags and self.is_visible(loc):
                return True
        return False

    def is_room(self, loc: str) -> bool:
        return loc in self.state.rooms

    def is_object(self, name: str) -> bool:
        """Check if name refers to a known object."""
        return name in self.state.objects

    def get_contents(self, container: str) -> list[str]:
        return [
            name for name, obj in self.state.objects.items()
            if obj.location == container
        ]

    def get_exit(self, actor: str, direction: str) -> tuple[str, str | None] | None:
        """Get exit info for direction from actor's room. Returns (destination, via) or None."""
        actor_loc = self.get_object_location(actor)
        room = self.world.rooms.get(actor_loc) if actor_loc else None
        if not room:
            return None
        for exit_def in room.exits:
            if exit_def.direction == direction:
                return (exit_def.to, exit_def.via)
        return None

    def set_object_flag(self, obj: str, flag: str) -> None:
        if obj in self.state.objects:
            self.state.objects[obj].flags.add(flag)

    def clear_object_flag(self, obj: str, flag: str) -> None:
        if obj in self.state.objects:
            self.state.objects[obj].flags.discard(flag)

    def set_object_property(self, obj: str, prop: str, value: Any) -> None:
        if obj in self.state.objects:
            self.state.objects[obj].properties[prop] = value

    def set_global(self, name: str, value: Any) -> None:
        self.state.globals[name.lower() if name.lower() in ("score", "moves") else name] = value

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
        player_loc = self.get_player_location()

        # Process each queued event
        # Copy queue keys since events may modify the queue
        for event_name in list(self.state.queues.keys()):
            event_def = self.world.events.get(event_name)
            if event_def is None:
                # No handler defined for this event
                continue

            # Check location constraint
            if event_def.location is not None and event_def.location != player_loc:
                continue

            # Decrement countdown if present and check if ready to fire
            # countdown=N means "fire on the Nth turn" (1-indexed)
            # countdown=1 fires now, countdown=2 fires next turn, etc.
            # countdown=0 or countdown=None means indefinite (fire every turn)
            countdown = self.state.queues.get(event_name)
            if countdown is not None and countdown > 1:
                self.state.queues[event_name] = countdown - 1
                continue

            # Fire the event
            result = self._evaluate_event(event_def)
            results.append(result)

        return results

    def _evaluate_event(self, event: "GrueEvent") -> ActionResult:
        """Evaluate an event's body and return the result."""
        if event.body is None:
            return ActionResult(
                outcome="error",
                error=f"Event {event.name} has no body"
            )

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
                return ActionResult(
                    outcome="error",
                    error=f"Error evaluating event {event.name}: {e}"
                )

            # Convert behavior result to ActionResult (same as behaviors)
            return self._behavior_result_to_action_result(result, evaluator)
        finally:
            self.bindings = old_bindings

    # -------------------------------------------------------------------------
    # High-level convenience methods
    # -------------------------------------------------------------------------

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

        # Fall back to static description
        if room.ldesc:
            return room.ldesc
        return room.description

    def get_object_description(self, obj_name: str) -> str:
        """Get an object's description."""
        obj = self.world.objects.get(obj_name)
        if obj:
            return obj.description
        return ""

    def get_visible_objects(self, for_description: bool = True) -> list[str]:
        """Get objects visible to the player.

        Args:
            for_description: If True, exclude NDESCBIT objects (for room listings).
                            If False, include all visible objects (for interaction).
        """
        result = []
        for name in self.state.objects:
            if name == self.player_name:
                continue
            if not self.is_visible(name):
                continue
            if for_description:
                obj_state = self.state.objects[name]
                if "NDESCBIT" in obj_state.flags:
                    continue
            result.append(name)
        return result

    def get_exits(self) -> dict[str, str]:
        """Get available exits from the current room."""
        room = self.world.rooms.get(self.get_player_room())  # Use room, not immediate location
        if not room:
            return {}
        return {exit.direction: exit.to for exit in room.exits}

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

    def do(
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
            direction = args[0]
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
        """Handle movement."""
        if actor is None:
            actor = self.player_name

        # Capture current location before move (for :on-enter)
        from_room = self.state.objects[actor].location

        exit_info = self.get_exit(actor, direction)
        if exit_info is None:
            return ActionResult(
                outcome="blocked",
                reason="no-exit",
                context=[("direction", direction)]
            )

        dest, via = exit_info

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
                context = result.context
        else:
            context = []

        # Move actor
        self.state.objects[actor].location = dest
        self.state.globals["moves"] = self.state.globals.get("moves", 0) + 1

        effects = [f"{actor} moved to {dest}" + (f" (via {via})" if via else "")]

        # Check for :on-enter behavior in destination room
        on_enter_result = self._check_room_on_enter(dest, from_room, actor)
        if on_enter_result is not None:
            # Merge on-enter effects and context
            if on_enter_result.effects_applied:
                effects.extend(on_enter_result.effects_applied)
            if on_enter_result.context:
                context = context + on_enter_result.context

        return ActionResult(
            outcome="success",
            effects_applied=effects,
            context=context,
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
        1. Old syntax: BehaviorSuccess/Blocked/Redirect/Default objects with :effects
        2. New syntax: Quoted list of effect descriptors '((move @x @y) (success))
        """
        # New syntax: behavior returned an effect list
        if isinstance(result, (list, SList)):
            return self._process_effect_list(result)

        if isinstance(result, BehaviorSuccess):
            # Execute effects
            effects_applied = []
            if result.effects:
                executor = EffectExecutor(self, self._functions)
                for effect in result.effects:
                    try:
                        # Pass the captured environment so effects can access local variables
                        executor.execute(effect, result.env)
                        effects_applied.append(str(effect))
                    except Exception as e:
                        return ActionResult(
                            outcome="error",
                            error=f"Error executing effect: {e}"
                        )

            self.state.globals["moves"] = self.state.globals.get("moves", 0) + 1

            return ActionResult(
                outcome="success",
                context=list(result.context.items()),
                effects_applied=effects_applied
            )

        if isinstance(result, BehaviorBlocked):
            # Execute effects even when blocked (e.g., tracking failed attempts)
            effects_applied = []
            if result.effects:
                executor = EffectExecutor(self, self._functions)
                for effect in result.effects:
                    try:
                        executor.execute(effect, result.env)
                        effects_applied.append(str(effect))
                    except Exception as e:
                        return ActionResult(
                            outcome="error",
                            error=f"Error executing blocked effect: {e}"
                        )
            return ActionResult(
                outcome="blocked",
                reason=result.reason,
                context=list(result.context.items()),
                effects_applied=effects_applied
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
            self.state.globals["moves"] = self.state.globals.get("moves", 0) + 1

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
            effects_applied=outcome.effects_applied
        )

    def check_victory(self) -> bool:
        """Check if victory condition is met."""
        if self.world.victory is None:
            return False

        evaluator = ExprEvaluator(self, self._functions)

        try:
            return bool(evaluator.eval(self.world.victory.when))
        except Exception:
            return False

    def check_defeat(self) -> str | None:
        """Check if any defeat condition is met. Returns defeat name or None."""
        evaluator = ExprEvaluator(self, self._functions)

        for name, defeat in self.world.defeat.items():
            try:
                if evaluator.eval(defeat.when):
                    return name
            except Exception:
                continue

        return None
