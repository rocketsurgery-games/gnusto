"""
DSL Runtime - Execute actions against immutable world state.

This module provides:
- GameState: Immutable snapshot of game state
- Runtime: Action execution with preconditions, effects, and invariants
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from .sexpr import SExpr, SList, Symbol, to_string
from .expr import ExprEvaluator, EffectExecutor, WorldState, MutableWorldState
from .world import WorldDefinition, Action, Room


def substitute_bindings(expr: SExpr, bindings: dict[str, str]) -> SExpr:
    """Substitute variable bindings in an S-expression.

    Variables like ?obj get replaced with their bound values.
    """
    if not bindings:
        return expr

    if isinstance(expr, Symbol):
        if expr.name in bindings:
            return Symbol(bindings[expr.name])
        return expr
    elif isinstance(expr, SList):
        # Check for lambda that shadows variables
        if (
            len(expr) >= 2
            and isinstance(expr[0], Symbol)
            and expr[0].name == "lambda"
        ):
            params = expr[1]
            if isinstance(params, SList):
                # Remove shadowed variables from bindings
                shadowed = {
                    p.name for p in params if isinstance(p, Symbol) and p.name in bindings
                }
                if shadowed:
                    new_bindings = {k: v for k, v in bindings.items() if k not in shadowed}
                    return SList(
                        [expr[0], expr[1]]
                        + [substitute_bindings(e, new_bindings) for e in expr[2:]]
                    )
        return SList([substitute_bindings(e, bindings) for e in expr])
    else:
        return expr


@dataclass(frozen=True)
class ObjectState:
    """Immutable state of a single object."""

    name: str
    location: str | None
    flags: frozenset[str]
    properties: tuple[tuple[str, Any], ...]  # Immutable dict representation

    def with_location(self, loc: str | None) -> ObjectState:
        return replace(self, location=loc)

    def with_flag(self, flag: str) -> ObjectState:
        return replace(self, flags=self.flags | {flag})

    def without_flag(self, flag: str) -> ObjectState:
        return replace(self, flags=self.flags - {flag})

    def with_property(self, prop: str, value: Any) -> ObjectState:
        props = dict(self.properties)
        props[prop] = value
        return replace(self, properties=tuple(sorted(props.items())))

    def get_property(self, prop: str) -> Any:
        return dict(self.properties).get(prop)


@dataclass(frozen=True)
class GameState:
    """Immutable game state snapshot.

    All state changes produce a new GameState instance.
    """

    world: WorldDefinition
    objects: tuple[ObjectState, ...]  # Indexed by object name
    globals: tuple[tuple[str, Any], ...]
    player_location: str

    # Index for fast lookup (not part of equality)
    _object_index: dict[str, int] = field(
        default_factory=dict, compare=False, hash=False
    )

    def __post_init__(self):
        # Build index if empty
        if not self._object_index:
            index = {obj.name: i for i, obj in enumerate(self.objects)}
            object.__setattr__(self, "_object_index", index)

    @classmethod
    def from_world(cls, world: WorldDefinition) -> GameState:
        """Create initial game state from world definition."""
        objects = []
        for name, obj_def in world.objects.items():
            obj_state = ObjectState(
                name=name,
                location=obj_def.initial_location,
                flags=frozenset(obj_def.flags),
                properties=tuple(sorted(obj_def.properties.items())),
            )
            objects.append(obj_state)

        globals_list = list(world.globals.items()) if world.globals else []

        starting_room = world.meta.starting_room or next(iter(world.rooms.keys()), None)
        if not starting_room:
            raise ValueError("World has no rooms")

        return cls(
            world=world,
            objects=tuple(objects),
            globals=tuple(sorted(globals_list)),
            player_location=starting_room,
        )

    def get_object(self, name: str) -> ObjectState | None:
        """Get object state by name."""
        idx = self._object_index.get(name)
        if idx is not None:
            return self.objects[idx]
        return None

    def get_global(self, name: str) -> Any:
        """Get global variable value."""
        return dict(self.globals).get(name)

    def get_room(self, name: str) -> Room | None:
        """Get room definition."""
        return self.world.rooms.get(name)

    def with_object(self, obj: ObjectState) -> GameState:
        """Return new state with updated object."""
        idx = self._object_index.get(obj.name)
        if idx is None:
            raise ValueError(f"Unknown object: {obj.name}")

        objects = list(self.objects)
        objects[idx] = obj
        return replace(self, objects=tuple(objects))

    def with_global(self, name: str, value: Any) -> GameState:
        """Return new state with updated global."""
        globals_dict = dict(self.globals)
        globals_dict[name] = value
        return replace(self, globals=tuple(sorted(globals_dict.items())))

    def with_player_location(self, room: str) -> GameState:
        """Return new state with player in different room."""
        if room not in self.world.rooms:
            raise ValueError(f"Unknown room: {room}")
        return replace(self, player_location=room)


class GameStateAdapter:
    """Adapts GameState to WorldState/MutableWorldState protocols.

    Used by ExprEvaluator and EffectExecutor.
    """

    def __init__(self, state: GameState):
        self._state = state
        self._pending_changes: list[tuple[str, Any]] = []

    @property
    def state(self) -> GameState:
        """Get current state (with pending changes applied)."""
        return self._state

    # WorldState protocol

    def get_object_flag(self, obj: str, flag: str) -> bool:
        # Check if obj is a room first
        room = self._state.world.rooms.get(obj)
        if room is not None:
            return flag in room.flags
        # Check objects
        obj_state = self._state.get_object(obj)
        if obj_state is None:
            return False
        return flag in obj_state.flags

    def get_object_location(self, obj: str) -> str | None:
        # Special case: PLAYER returns the player's current room
        if obj == "PLAYER":
            return self._state.player_location
        obj_state = self._state.get_object(obj)
        if obj_state is None:
            return None
        return obj_state.location

    def get_object_property(self, obj: str, prop: str) -> Any:
        obj_state = self._state.get_object(obj)
        if obj_state is None:
            return None
        return obj_state.get_property(prop)

    def get_object_flags(self, obj: str) -> set[str]:
        obj_state = self._state.get_object(obj)
        if obj_state is None:
            return set()
        return set(obj_state.flags)

    def get_global(self, name: str) -> Any:
        value = self._state.get_global(name)
        if value is None:
            # Raise KeyError to signal to ExprEvaluator that this isn't a global
            # and the symbol should be treated as a literal name
            raise KeyError(name)
        return value

    def get_player_location(self) -> str:
        return self._state.player_location

    def get_inventory(self) -> list[str]:
        """Get objects held by player."""
        return [
            obj.name
            for obj in self._state.objects
            if obj.location == "PLAYER" or obj.location == "INVENTORY"
        ]

    def is_visible(self, obj: str) -> bool:
        """Check if object is visible to player."""
        obj_state = self._state.get_object(obj)
        if obj_state is None:
            return False

        # Object is visible if:
        # 1. In player's inventory
        if obj_state.location in ("PLAYER", "INVENTORY"):
            return True

        # 2. In player's current room
        if obj_state.location == self._state.player_location:
            return True

        # 3. In a container that is open and visible
        container = self._state.get_object(obj_state.location or "")
        if container and "OPENBIT" in container.flags:
            return self.is_visible(container.name)

        return False

    def is_room(self, loc: str) -> bool:
        return loc in self._state.world.rooms

    def get_contents(self, container: str) -> list[str]:
        """Get objects in container/room."""
        return [obj.name for obj in self._state.objects if obj.location == container]

    # MutableWorldState protocol

    def set_object_flag(self, obj: str, flag: str) -> None:
        obj_state = self._state.get_object(obj)
        if obj_state:
            new_obj = obj_state.with_flag(flag)
            self._state = self._state.with_object(new_obj)

    def clear_object_flag(self, obj: str, flag: str) -> None:
        obj_state = self._state.get_object(obj)
        if obj_state:
            new_obj = obj_state.without_flag(flag)
            self._state = self._state.with_object(new_obj)

    def set_object_property(self, obj: str, prop: str, value: Any) -> None:
        obj_state = self._state.get_object(obj)
        if obj_state:
            new_obj = obj_state.with_property(prop, value)
            self._state = self._state.with_object(new_obj)

    def set_global(self, name: str, value: Any) -> None:
        self._state = self._state.with_global(name, value)

    def move_object(self, obj: str, dest: str) -> None:
        obj_state = self._state.get_object(obj)
        if obj_state:
            new_obj = obj_state.with_location(dest)
            self._state = self._state.with_object(new_obj)


@dataclass
class ActionResult:
    """Result of attempting an action."""

    success: bool
    message: str
    new_state: GameState | None = None
    failed_precondition: str | None = None
    violated_invariant: str | None = None


@dataclass
class MoveResult:
    """Result of attempting movement."""

    success: bool
    message: str
    new_state: GameState | None = None
    blocked_by: str | None = None  # Transition name that blocked


class Runtime:
    """Execute actions against game state.

    Handles:
    - Precondition checking
    - Effect application
    - Invariant enforcement
    - Transition triggers
    """

    def __init__(self, state: GameState):
        self._state = state

    @property
    def state(self) -> GameState:
        return self._state

    @state.setter
    def state(self, new_state: GameState) -> None:
        self._state = new_state

    @property
    def world(self) -> WorldDefinition:
        return self._state.world

    def evaluate(self, expr: SExpr, bindings: dict[str, str] | None = None) -> Any:
        """Evaluate an S-expression against current state."""
        adapter = GameStateAdapter(self._state)
        evaluator = ExprEvaluator(adapter)
        if bindings:
            expr = substitute_bindings(expr, bindings)
        return evaluator.eval(expr)

    def execute_action(
        self, action_name: str, target: str | None = None
    ) -> ActionResult:
        """Execute a named action with optional target.

        Returns ActionResult with success status, message, and new state.
        """
        action = self.world.actions.get(action_name)
        if not action:
            return ActionResult(
                success=False,
                message=f"Unknown action: {action_name}",
            )

        # Build bindings for ?obj variable
        bindings = {}
        if target:
            bindings["?obj"] = target

        # Check preconditions
        adapter = GameStateAdapter(self._state)
        evaluator = ExprEvaluator(adapter)

        for precond in action.preconditions:
            try:
                # Substitute bindings into precondition
                bound_precond = substitute_bindings(precond, bindings)
                result = evaluator.eval(bound_precond)
                if not result:
                    return ActionResult(
                        success=False,
                        message=action.messages.failure
                        if action.messages
                        else "You can't do that.",
                        failed_precondition=to_string(precond),
                    )
            except Exception as e:
                return ActionResult(
                    success=False,
                    message=f"Error checking precondition: {e}",
                    failed_precondition=to_string(precond),
                )

        # Apply effects
        executor = EffectExecutor(adapter)
        for effect in action.effects:
            try:
                # Substitute bindings into effect
                bound_effect = substitute_bindings(effect, bindings)
                executor.execute(bound_effect)
            except Exception as e:
                return ActionResult(
                    success=False,
                    message=f"Error applying effect: {e}",
                )

        new_state = adapter.state

        # Check invariants
        invariant_result = self._check_invariants(new_state)
        if invariant_result:
            return ActionResult(
                success=False,
                message=invariant_result[1],
                violated_invariant=invariant_result[0],
            )

        return ActionResult(
            success=True,
            message=action.messages.success if action.messages else "Done.",
            new_state=new_state,
        )

    def move(self, direction: str) -> MoveResult:
        """Attempt to move in a direction.

        Checks:
        1. Exit exists in current room
        2. Exit conditions are met
        3. No blocking transitions
        4. Invariants after move
        """
        room = self.world.rooms.get(self._state.player_location)
        if not room:
            return MoveResult(
                success=False,
                message="You're in an unknown location.",
            )

        exit_def = room.exits.get(direction)
        if not exit_def:
            return MoveResult(
                success=False,
                message=f"You can't go {direction} from here.",
            )

        adapter = GameStateAdapter(self._state)
        evaluator = ExprEvaluator(adapter)

        # Check exit condition
        if exit_def.when:
            try:
                if not evaluator.eval(exit_def.when):
                    return MoveResult(
                        success=False,
                        message=f"You can't go {direction} right now.",
                    )
            except Exception as e:
                return MoveResult(
                    success=False,
                    message=f"Error checking exit condition: {e}",
                )

        # Check blocking transitions
        for trans_name, trans in self.world.transitions.items():
            trigger = trans.trigger
            if trigger.get("action") == "GO" and trigger.get("direction") == direction:
                if trans.when:
                    try:
                        if evaluator.eval(trans.when):
                            return MoveResult(
                                success=False,
                                message=trans.message or "Something blocks your way.",
                                blocked_by=trans_name,
                            )
                    except Exception:
                        pass  # If transition check fails, don't block

        # Perform move
        new_state = self._state.with_player_location(exit_def.to)

        # Apply transition effects (non-blocking ones)
        adapter = GameStateAdapter(new_state)
        for trans_name, trans in self.world.transitions.items():
            trigger = trans.trigger
            if trigger.get("action") == "GO" and trigger.get("direction") == direction:
                # Only apply effects for non-blocking transitions
                if trans.when:
                    try:
                        if not evaluator.eval(trans.when):
                            # Condition not met, apply effects
                            executor = EffectExecutor(adapter)
                            for effect in trans.effects:
                                executor.execute(effect)
                    except Exception:
                        pass

        new_state = adapter.state

        # Check invariants
        invariant_result = self._check_invariants(new_state)
        if invariant_result:
            return MoveResult(
                success=False,
                message=invariant_result[1],
            )

        dest_room = self.world.rooms.get(exit_def.to)
        desc = dest_room.description if dest_room else exit_def.to

        return MoveResult(
            success=True,
            message=desc,
            new_state=new_state,
        )

    def _check_invariants(self, state: GameState) -> tuple[str, str] | None:
        """Check all invariants against state.

        Returns (invariant_name, violation_message) if violated, None otherwise.
        """
        adapter = GameStateAdapter(state)
        evaluator = ExprEvaluator(adapter)

        for inv_name, inv in self.world.invariants.items():
            if inv.check:
                try:
                    if not evaluator.eval(inv.check):
                        return (inv_name, inv.on_violation or f"Invariant {inv_name} violated")
                except Exception:
                    pass  # Don't fail on invariant check errors

        return None

    def check_victory(self) -> tuple[bool, str | None]:
        """Check if victory condition is met.

        Returns (is_victory, message).
        """
        if not self.world.victory:
            return (False, None)

        adapter = GameStateAdapter(self._state)
        evaluator = ExprEvaluator(adapter)

        try:
            if evaluator.eval(self.world.victory.when):
                return (True, self.world.victory.message)
        except Exception:
            pass

        return (False, None)

    def check_defeat(self) -> tuple[str | None, str | None]:
        """Check if any defeat condition is met.

        Returns (defeat_name, message) or (None, None).
        """
        if not self.world.defeat:
            return (None, None)

        adapter = GameStateAdapter(self._state)
        evaluator = ExprEvaluator(adapter)

        for defeat_name, defeat in self.world.defeat.items():
            try:
                if evaluator.eval(defeat.when):
                    return (defeat_name, defeat.message)
            except Exception:
                pass

        return (None, None)

    def describe_room(self) -> str:
        """Get description of current room."""
        room = self.world.rooms.get(self._state.player_location)
        if not room:
            return "You are nowhere."

        lines = [room.long_description or room.description]

        # List visible objects
        objects_here = [
            obj
            for obj in self._state.objects
            if obj.location == self._state.player_location
        ]
        for obj in objects_here:
            obj_def = self.world.objects.get(obj.name)
            if obj_def and obj_def.long_description:
                lines.append(obj_def.long_description)

        return "\n".join(lines)

    def describe_exits(self) -> list[str]:
        """List available exits from current room."""
        room = self.world.rooms.get(self._state.player_location)
        if not room:
            return []
        return list(room.exits.keys())

    def get_visible_objects(self) -> list[str]:
        """Get names of objects visible to player."""
        adapter = GameStateAdapter(self._state)
        return [obj.name for obj in self._state.objects if adapter.is_visible(obj.name)]
