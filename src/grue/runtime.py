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

from .parser import GrueWorld, GrueObject, GrueBehavior, GrueCase
from .expr import ExprEvaluator, EffectExecutor
from .sexpr import SExpr, Symbol, SList


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

    def copy(self) -> "GameState":
        """Create a deep copy of the state."""
        return deepcopy(self)


@dataclass
class ActionResult:
    """Result of executing an action."""
    outcome: str  # "success", "blocked", "redirect", "error"
    reason: str | None = None  # For blocked outcomes
    context: list[tuple[str, Any]] = field(default_factory=list)
    redirect_action: SExpr | None = None  # For redirects
    effects_applied: list[str] = field(default_factory=list)  # Description of effects
    error: str | None = None  # For errors


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

        # Initialize globals
        state.globals["score"] = 0
        state.globals["moves"] = 0

        return state

    def reset(self) -> None:
        """Reset game state to initial state."""
        self.state = self._init_state()
        self.bindings = {}

    # -------------------------------------------------------------------------
    # MutableWorldState interface - used by ExprEvaluator and EffectExecutor
    # -------------------------------------------------------------------------

    def _resolve_symbol(self, name: str) -> str:
        """Resolve 'self' and other special symbols via bindings."""
        if name == "self" and "self" in self.bindings:
            return self.bindings["self"]
        return name

    def get_object_flag(self, obj: str, flag: str) -> bool:
        obj = self._resolve_symbol(obj)
        if obj not in self.state.objects:
            return False
        return flag in self.state.objects[obj].flags

    def get_object_location(self, obj: str) -> str | None:
        obj = self._resolve_symbol(obj)
        if obj == "PLAYER":
            return self.get_player_location()
        if obj not in self.state.objects:
            return None
        return self.state.objects[obj].location

    def get_object_property(self, obj: str, prop: str) -> Any:
        obj = self._resolve_symbol(obj)
        if obj not in self.state.objects:
            return None
        return self.state.objects[obj].properties.get(prop)

    def get_object_flags(self, obj: str) -> set[str]:
        obj = self._resolve_symbol(obj)
        if obj not in self.state.objects:
            return set()
        return self.state.objects[obj].flags

    def get_global(self, name: str) -> Any:
        # Check bindings first (for ?with, ?on, etc.)
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
        player = self.state.objects.get("PLAYER")
        if player:
            return player.location or ""
        return ""

    def get_inventory(self) -> list[str]:
        """Get objects the player is carrying."""
        return [
            name for name, obj in self.state.objects.items()
            if obj.location == "PLAYER" and name != "PLAYER"
        ]

    def is_visible(self, obj: str) -> bool:
        obj = self._resolve_symbol(obj)
        if obj not in self.state.objects:
            return False
        obj_state = self.state.objects[obj]
        # Check INVISIBLE flag
        if "INVISIBLE" in obj_state.flags:
            return False
        loc = obj_state.location
        if loc is None:
            return False
        if loc == "PLAYER":
            return True
        return loc == self.get_player_location()

    def is_room(self, loc: str) -> bool:
        loc = self._resolve_symbol(loc)
        return loc in self.state.rooms

    def get_contents(self, container: str) -> list[str]:
        container = self._resolve_symbol(container)
        return [
            name for name, obj in self.state.objects.items()
            if obj.location == container
        ]

    def set_object_flag(self, obj: str, flag: str) -> None:
        obj = self._resolve_symbol(obj)
        if obj in self.state.objects:
            self.state.objects[obj].flags.add(flag)

    def clear_object_flag(self, obj: str, flag: str) -> None:
        obj = self._resolve_symbol(obj)
        if obj in self.state.objects:
            self.state.objects[obj].flags.discard(flag)

    def set_object_property(self, obj: str, prop: str, value: Any) -> None:
        obj = self._resolve_symbol(obj)
        if obj in self.state.objects:
            self.state.objects[obj].properties[prop] = value

    def set_global(self, name: str, value: Any) -> None:
        self.state.globals[name.lower() if name.lower() in ("score", "moves") else name] = value

    def move_object(self, obj: str, dest: str) -> None:
        obj = self._resolve_symbol(obj)
        dest = self._resolve_symbol(dest)
        if obj in self.state.objects:
            self.state.objects[obj].location = dest

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
            if name != "PLAYER" and self.is_visible(name)
        ]

    def get_exits(self) -> dict[str, str]:
        """Get available exits from the current room."""
        room = self.world.rooms.get(self.get_player_location())
        if not room:
            return {}
        return {exit.direction: exit.to for exit in room.exits}

    def do(
        self,
        verb: str,
        direct_object: str | None = None,
        **kwargs
    ) -> ActionResult:
        """
        Execute an action.

        Args:
            verb: The verb (e.g., "open", "take", "go")
            direct_object: The target object (e.g., "DOOR", "KEY")
            **kwargs: Additional arguments (with=..., on=..., direction=...)

        Returns:
            ActionResult with outcome and details.
        """
        # Handle movement specially
        if verb == "go":
            direction = kwargs.get("direction")
            if direction:
                return self._do_go(direction)
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
            default_result = self._try_default_behavior(verb, direct_object, obj_def)
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
            **kwargs
        }

        # Evaluate behavior cases
        return self._evaluate_behavior(behavior, bindings)

    def _try_default_behavior(
        self,
        verb: str,
        obj_name: str,
        obj_def: GrueObject
    ) -> ActionResult | None:
        """
        Try default behaviors based on object flags.

        Returns ActionResult if a default applies, None otherwise.
        """
        obj_state = self.state.objects.get(obj_name)
        if obj_state is None:
            return None

        player_loc = self.get_player_location()

        if verb == "take":
            # Check TAKEBIT flag
            if "TAKEBIT" not in obj_state.flags:
                return ActionResult(
                    outcome="blocked",
                    reason="not-takeable",
                    context=[("object", obj_name)]
                )

            # Check if object is here or visible
            if obj_state.location != player_loc and obj_state.location != "PLAYER":
                return ActionResult(
                    outcome="blocked",
                    reason="not-here",
                    context=[("object", obj_name), ("location", obj_state.location)]
                )

            # Already holding it?
            if obj_state.location == "PLAYER":
                return ActionResult(
                    outcome="blocked",
                    reason="already-held",
                    context=[("object", obj_name)]
                )

            # Take it
            obj_state.location = "PLAYER"
            return ActionResult(
                outcome="success",
                effects_applied=[f"{obj_name} moved to PLAYER"]
            )

        if verb == "drop":
            # Must be holding it
            if obj_state.location != "PLAYER":
                return ActionResult(
                    outcome="blocked",
                    reason="not-held",
                    context=[("object", obj_name)]
                )

            # Drop it in current room
            obj_state.location = player_loc
            return ActionResult(
                outcome="success",
                effects_applied=[f"{obj_name} moved to {player_loc}"]
            )

        return None

    def _do_go(self, direction: str) -> ActionResult:
        """Handle movement."""
        room = self.world.rooms.get(self.get_player_location())
        if not room:
            return ActionResult(
                outcome="error",
                error="Player is not in a valid room"
            )

        # Find the exit
        exit_def = None
        for e in room.exits:
            if e.direction == direction:
                exit_def = e
                break

        if exit_def is None:
            return ActionResult(
                outcome="blocked",
                reason="no-exit",
                context=[("direction", direction)]
            )

        # Check if exit has a :via door
        if exit_def.via:
            # Dispatch to door's "through" behavior
            result = self.do("through", exit_def.via, direction=direction, to=exit_def.to)

            # If door blocks passage, return that result
            if result.outcome == "blocked":
                return result

            # If door allows passage (success or redirect), complete the movement
            # The redirect indicates "yes, go that way" - we handle it here
            if result.outcome in ("success", "redirect"):
                self.state.objects["PLAYER"].location = exit_def.to
                self.state.globals["moves"] = self.state.globals.get("moves", 0) + 1
                return ActionResult(
                    outcome="success",
                    effects_applied=[f"PLAYER moved to {exit_def.to} (via {exit_def.via})"],
                    context=result.context,
                )

            # Pass through errors
            return result

        # Simple exit - just move
        self.state.objects["PLAYER"].location = exit_def.to
        self.state.globals["moves"] = self.state.globals.get("moves", 0) + 1

        return ActionResult(
            outcome="success",
            effects_applied=[f"PLAYER moved to {exit_def.to}"]
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
                    if case.outcome == "redirect":
                        return ActionResult(
                            outcome="redirect",
                            redirect_action=case.action,
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
