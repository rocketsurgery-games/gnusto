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
    ExprEvaluator, EffectExecutor, GrueFn,
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
        return self.state.objects[obj].properties.get(prop)

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

        # Then check globals
        if name.lower() in ("score", "moves"):
            return self.state.globals.get(name.lower(), 0)
        if name in self.state.globals:
            return self.state.globals[name]
        raise KeyError(f"Unknown global: {name}")

    def get_player_location(self) -> str:
        """Get the player's current room."""
        player = self.state.objects.get(self.player_name)
        if player:
            return player.location or ""
        return ""

    def get_player_name(self) -> str:
        """Get the player entity name."""
        return self.player_name

    def get_inventory(self) -> list[str]:
        """Get objects the player is carrying."""
        return [
            name for name, obj in self.state.objects.items()
            if obj.location == self.player_name and name != self.player_name
        ]

    def is_visible(self, obj: str) -> bool:
        if obj not in self.state.objects:
            return False
        obj_state = self.state.objects[obj]
        # Check INVISIBLE flag
        if "INVISIBLE" in obj_state.flags:
            return False
        loc = obj_state.location
        if loc is None:
            return False
        if loc == self.player_name:
            return True
        return loc == self.get_player_location()

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

            # Decrement countdown if present
            countdown = self.state.queues.get(event_name)
            if countdown is not None and countdown > 0:
                # Not ready to fire yet
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

        # Events use simple bindings (no direct object)
        bindings = {"actor": self.player_name}
        old_bindings = self.bindings
        self.bindings = bindings
        try:
            evaluator = ExprEvaluator(self, self._functions)

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
        """Get a room's description. Returns ldesc if available, otherwise description."""
        if room_name is None:
            room_name = self.get_player_location()
        room = self.world.rooms.get(room_name)
        if room:
            # Prefer ldesc (long description) if available
            if room.ldesc:
                return room.ldesc
            return room.description
        return ""

    def get_object_description(self, obj_name: str) -> str:
        """Get an object's description."""
        obj = self.world.objects.get(obj_name)
        if obj:
            return obj.description
        return ""

    def get_visible_objects(self) -> list[str]:
        """Get objects visible to the player."""
        return [
            name for name in self.state.objects
            if name != self.player_name and self.is_visible(name)
        ]

    def get_exits(self) -> dict[str, str]:
        """Get available exits from the current room."""
        room = self.world.rooms.get(self.get_player_location())
        if not room:
            return {}
        return {exit.direction: exit.to for exit in room.exits}

    def _parse_action_sexpr(self, action: SExpr) -> tuple[str, str, list[str]]:
        """Parse an action S-expression into (target, verb, args).

        Format: (do TARGET :verb arg1 arg2 ...)

        Examples:
            (do @hacker :give @food)  -> ("HACKER", "give", ["FOOD"])
            (do @lamp :examine)       -> ("LAMP", "examine", [])
            (do @door :unlock @key)   -> ("DOOR", "unlock", ["KEY"])
        """
        if not isinstance(action, SList) or len(action) < 3:
            raise ValueError(f"Invalid action format: {action}")

        items = list(action.items)

        # First item should be 'do'
        if not isinstance(items[0], Symbol) or items[0].name != "do":
            raise ValueError(f"Action must start with 'do': {items[0]}")

        # Second item is target
        if not isinstance(items[1], Symbol):
            raise ValueError(f"Target must be a symbol: {items[1]}")
        target = items[1].name

        # Third item is verb (keyword)
        if not isinstance(items[2], Keyword):
            raise ValueError(f"Verb must be a keyword: {items[2]}")
        verb = items[2].name

        # Remaining items are positional args
        args = []
        for i in range(3, len(items)):
            item = items[i]
            if isinstance(item, Symbol):
                args.append(item.name)
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
            if args:
                direction = args[0]
                return self._do_go(direction, actor=actor)
            return ActionResult(
                outcome="error",
                error="go requires a direction"
            )

        # Check room's :before-action behavior (if any)
        room_result = self._check_room_before_action(verb, target, actor, args)
        if room_result is not None and room_result.outcome != "default":
            return room_result

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
            default_result = self._try_default_behavior(verb, target, actor)
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
        # Auto-bound: ?self, ?actor
        # Positional: behavior.params[i] = args[i]
        bindings = {
            "self": target,
            "actor": actor,
        }
        for i, param in enumerate(behavior.params):
            bindings[param] = args[i]

        # Evaluate behavior cases
        result = self._evaluate_behavior(behavior, bindings)

        # If behavior returns 'default' with no action, fall through to default behavior
        if result.outcome == "default" and result.default_action is None:
            default_result = self._try_default_behavior(verb, target, actor)
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

        # Evaluate the behavior
        return self._evaluate_behavior(before_action, bindings)

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
        bindings = {
            "actor": actor,
        }

        # Bind positional params (typically just ?from-room)
        param_values = [from_room]
        for i, param in enumerate(on_enter.params):
            if i < len(param_values):
                bindings[param] = param_values[i]

        # Evaluate the behavior
        return self._evaluate_behavior(on_enter, bindings)

    def _try_default_behavior(
        self,
        verb: str,
        obj_name: str,
        actor: str | None = None
    ) -> ActionResult | None:
        """
        Try default behaviors defined in world.defaults.

        Args:
            verb: The action verb
            obj_name: Target object
            actor: Who is performing the action (default: player entity)

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
            result = self.do(via, "through")
            if result.outcome == "blocked":
                return result
            if result.outcome not in ("success", "default"):
                return result  # Pass through errors
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
        bindings: dict[str, Any]
    ) -> ActionResult:
        """Evaluate a behavior's body and return the result."""
        if behavior.body is None:
            return ActionResult(
                outcome="error",
                error=f"Behavior {behavior.verb} has no body"
            )

        # Set bindings for this evaluation (restored after)
        old_bindings = self.bindings
        self.bindings = bindings
        try:
            evaluator = ExprEvaluator(self, self._functions)
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
        # Create a GrueFn from the behavior
        fn = GrueFn(params=behavior.params, body=behavior.body)

        # Add auto-bound symbols to captured bindings
        fn.captured = dict(bindings)

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
        """Convert a BehaviorSuccess/Blocked/etc. to ActionResult."""
        if isinstance(result, BehaviorSuccess):
            # Execute effects
            effects_applied = []
            if result.effects:
                executor = EffectExecutor(self, self._functions)
                for effect in result.effects:
                    try:
                        executor.execute(effect)
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
            return ActionResult(
                outcome="blocked",
                reason=result.reason,
                context=list(result.context.items())
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
