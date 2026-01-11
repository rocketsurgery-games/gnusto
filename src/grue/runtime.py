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

from .parser import GrueWorld, GrueBehavior, GrueCase
from .expr import ExprEvaluator, EffectExecutor
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
        """Find the player entity by looking for an object with the PERSON flag.

        Falls back to "PLAYER" for backwards compatibility.
        """
        for name, obj in self.state.objects.items():
            if "PERSON" in obj.flags and name not in self.state.rooms:
                return name
        return "PLAYER"  # Fallback

    def reset(self) -> None:
        """Reset game state to initial state."""
        self.state = self._init_state()
        self.bindings = {}
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
        """Evaluate an event's cases and return the result."""
        from .forms import GrueEvent  # Import here to avoid circular

        # Events use simple bindings (no direct object)
        bindings = {"actor": self.player_name}
        old_bindings = self.bindings
        self.bindings = bindings
        try:
            evaluator = ExprEvaluator(self)

            for case in event.cases:
                # Evaluate the condition
                try:
                    condition_met = evaluator.eval(case.when)
                except Exception as e:
                    return ActionResult(
                        outcome="error",
                        error=f"Error evaluating event {event.name} condition: {e}"
                    )

                if condition_met:
                    # Execute effects
                    if case.effects:
                        executor = EffectExecutor(self)
                        for effect in case.effects:
                            try:
                                executor.execute(effect)
                            except Exception as e:
                                return ActionResult(
                                    outcome="error",
                                    error=f"Error executing event {event.name} effect: {e}"
                                )

                    return ActionResult(
                        outcome=case.outcome or "success",
                        reason=case.reason,
                        context=case.context
                    )

            # No case matched - shouldn't happen with proper (true ...) fallback
            return ActionResult(
                outcome="success",
                context=[("event", event.name), ("note", "no case matched")]
            )
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

    def _parse_action_sexpr(self, action: SExpr) -> tuple[str, str | None, dict[str, Any]]:
        """Parse an action S-expression into (verb, direct_object, kwargs).

        Supports formats:
            (verb object)           -> ("verb", "object", {})
            (verb :key val ...)     -> ("verb", None, {"key": val, ...})
            (verb object :key val)  -> ("verb", "object", {"key": val})
        """
        if not isinstance(action, SList) or len(action) < 1:
            raise ValueError(f"Invalid action format: {action}")

        items = list(action.items)
        if not isinstance(items[0], Symbol):
            raise ValueError(f"Action verb must be a symbol: {items[0]}")

        verb = items[0].name
        direct_object = None
        kwargs: dict[str, Any] = {}

        i = 1
        # Check if second item is a direct object (not a keyword)
        if i < len(items) and isinstance(items[i], Symbol) and not isinstance(items[i], Keyword):
            direct_object = items[i].name
            i += 1

        # Parse keyword arguments
        while i < len(items):
            if isinstance(items[i], Keyword):
                key = items[i].name
                if i + 1 < len(items):
                    val = items[i + 1]
                    if isinstance(val, Symbol):
                        kwargs[key] = val.name
                    else:
                        kwargs[key] = val
                    i += 2
                else:
                    raise ValueError(f"Keyword :{key} has no value")
            else:
                raise ValueError(f"Expected keyword, got: {items[i]}")

        return verb, direct_object, kwargs

    def do(
        self,
        verb: str,
        direct_object: str | None = None,
        actor: str | None = None,
        _redirects: list[SExpr] | None = None,
        _max_redirects: int = 10,
        **kwargs
    ) -> ActionResult:
        """
        Execute an action, following any redirects automatically.

        Args:
            verb: The verb (e.g., "open", "take", "go")
            direct_object: The target object (e.g., "DOOR", "KEY")
            actor: Who is performing the action (default: player entity)
            _redirects: Internal - chain of redirects followed (for loop detection)
            _max_redirects: Internal - maximum redirect depth
            **kwargs: Additional arguments (with=..., on=..., direction=...)

        Returns:
            ActionResult with outcome and details. The 'redirects' field contains
            the chain of redirected actions for narrative purposes.
        """
        if actor is None:
            actor = self.player_name
        if _redirects is None:
            _redirects = []

        result = self._do_single(verb, direct_object, actor, **kwargs)

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
                new_verb, new_obj, new_kwargs = self._parse_action_sexpr(result.default_action)
                # Merge context from redirect into kwargs if not already set
                new_kwargs.setdefault("actor", actor)
                final_result = self.do(
                    new_verb,
                    new_obj,
                    _redirects=_redirects,
                    _max_redirects=_max_redirects,
                    **new_kwargs
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
        verb: str,
        direct_object: str | None = None,
        actor: str | None = None,
        **kwargs
    ) -> ActionResult:
        """Execute a single action without following redirects."""
        if actor is None:
            actor = self.player_name

        # Handle movement specially
        if verb == "go":
            direction = kwargs.get("direction")
            if direction:
                return self._do_go(direction, actor=actor)
            return ActionResult(
                outcome="error",
                error="go requires a direction"
            )

        # Find the target object
        if direct_object is None:
            return ActionResult(
                outcome="error",
                error=f"{verb} requires a target object"
            )

        # Get the object's definition
        obj_def = self.world.objects.get(direct_object)
        if obj_def is None:
            return ActionResult(
                outcome="error",
                error=f"Unknown object: {direct_object}"
            )

        # Find the behavior for this verb
        behavior = None
        for b in obj_def.behaviors:
            if b.verb == verb:
                behavior = b
                break

        if behavior is None:
            # Try default behaviors based on flags
            default_result = self._try_default_behavior(verb, direct_object, actor)
            if default_result is not None:
                return default_result

            return ActionResult(
                outcome="blocked",
                reason="no-behavior",
                context=[("verb", verb), ("object", direct_object)]
            )

        # Set up bindings for evaluation
        bindings = {
            "self": direct_object,
            "actor": actor,
            **kwargs
        }

        # Evaluate behavior cases
        result = self._evaluate_behavior(behavior, bindings)

        # If behavior returns 'default' with no action, fall through to default behavior
        if result.outcome == "default" and result.default_action is None:
            default_result = self._try_default_behavior(verb, direct_object, actor)
            if default_result is not None:
                return default_result

        return result

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
            result = self.do("through", via, actor=actor, direction=direction, to=dest)
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

        via_note = f" (via {via})" if via else ""
        return ActionResult(
            outcome="success",
            effects_applied=[f"{actor} moved to {dest}{via_note}"],
            context=context,
        )

    def _evaluate_behavior(
        self,
        behavior: GrueBehavior,
        bindings: dict[str, Any]
    ) -> ActionResult:
        """Evaluate a behavior's cases and return the result."""
        # Set bindings for this evaluation (restored after)
        old_bindings = self.bindings
        self.bindings = bindings
        try:
            evaluator = ExprEvaluator(self)

            for case in behavior.cases:
                # Evaluate the condition
                try:
                    condition_met = evaluator.eval(case.when)
                except Exception as e:
                    return ActionResult(
                        outcome="error",
                        error=f"Error evaluating condition: {e}"
                    )

                if condition_met:
                    # This case matches
                    if case.outcome == "default":
                        return ActionResult(
                            outcome="default",
                            default_action=case.action,
                            context=case.context
                        )

                    if case.outcome == "redirect":
                        return ActionResult(
                            outcome="redirect",
                            default_action=case.action,
                            context=case.context
                        )

                    if case.outcome == "blocked":
                        return ActionResult(
                            outcome="blocked",
                            reason=case.reason,
                            context=case.context
                        )

                    # Success - execute effects
                    effects_applied = []
                    if case.effects:
                        executor = EffectExecutor(self)
                        for effect in case.effects:
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
                        context=case.context,
                        effects_applied=effects_applied
                    )

            # No case matched - shouldn't happen if behaviors have a (case true ...) fallback
            return ActionResult(
                outcome="blocked",
                reason="no-matching-case"
            )
        finally:
            self.bindings = old_bindings

    def check_victory(self) -> bool:
        """Check if victory condition is met."""
        if self.world.victory is None:
            return False

        evaluator = ExprEvaluator(self)

        try:
            return bool(evaluator.eval(self.world.victory.when))
        except Exception:
            return False

    def check_defeat(self) -> str | None:
        """Check if any defeat condition is met. Returns defeat name or None."""
        evaluator = ExprEvaluator(self)

        for name, defeat in self.world.defeat.items():
            try:
                if evaluator.eval(defeat.when):
                    return name
            except Exception:
                continue

        return None
