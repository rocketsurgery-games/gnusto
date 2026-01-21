"""
State space explorer for Grue games.

Performs BFS/DFS exploration of the game state space, using only
puzzle-relevant state (from relevance analysis) for visited-set membership.

This is the core of Frotz's winnability verification.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Any
import copy

from grue import GrueWorld, load_grue
from grue.runtime import GrueRuntime

from .effects import EffectAnalysis, StateRef, PropertyRef, LocationRef, QueueRef
from .relevance import RelevanceAnalysis


@dataclass(frozen=True)
class Action:
    """An action that can be taken in the game."""
    target: str  # Object to act on (e.g., "@cell-door")
    verb: str    # Verb to use (e.g., "unlock")
    args: tuple[str, ...] = ()  # Additional arguments

    def __str__(self):
        if self.args:
            args_str = " ".join(self.args)
            return f"(do {self.target} :{self.verb} {args_str})"
        return f"(do {self.target} :{self.verb})"


@dataclass(frozen=True)
class GameState:
    """
    Hashable game state containing only puzzle-relevant properties.

    This is the "quotient" state - two full game states that have the
    same GameState are equivalent for winnability purposes.
    """
    # Tuple of (ref_str, value) pairs, sorted for consistent hashing
    values: tuple[tuple[str, Any], ...]

    @classmethod
    def from_runtime(
        cls,
        runtime: GrueRuntime,
        relevant: set[StateRef],
    ) -> "GameState":
        """Extract relevant state from a runtime."""
        values = []

        for ref in sorted(relevant, key=str):
            if isinstance(ref, PropertyRef):
                val = runtime.get_object_property(ref.object, ref.property)
                values.append((str(ref), val))
            elif isinstance(ref, LocationRef):
                val = runtime.get_object_location(ref.object)
                values.append((str(ref), val))
            elif isinstance(ref, QueueRef):
                val = runtime.get_queue_countdown(ref.event)
                values.append((str(ref), val))

        return cls(values=tuple(values))

    def __str__(self):
        parts = [f"{k}={v}" for k, v in self.values]
        return "{" + ", ".join(parts) + "}"


@dataclass
class ExplorationNode:
    """A node in the exploration graph."""
    state: GameState
    parent: "ExplorationNode | None" = None
    action: Action | None = None  # Action that led to this state
    depth: int = 0

    def path(self) -> list[Action]:
        """Reconstruct the path from root to this node."""
        actions = []
        node = self
        while node.parent is not None:
            if node.action:
                actions.append(node.action)
            node = node.parent
        return list(reversed(actions))


@dataclass
class ExplorationResult:
    """Results of state space exploration."""
    # Statistics
    states_explored: int = 0
    states_visited: int = 0  # Unique states (after quotient)
    max_depth: int = 0

    # Outcomes
    victory_found: bool = False
    victory_path: list[Action] = field(default_factory=list)
    victory_depth: int = 0

    defeat_states: list[tuple[GameState, list[Action]]] = field(default_factory=list)

    # Dead ends (no actions available, not victory/defeat)
    dead_ends: list[tuple[GameState, list[Action]]] = field(default_factory=list)

    def summary(self) -> str:
        """Return a human-readable summary."""
        lines = []
        lines.append(f"States explored: {self.states_explored}")
        lines.append(f"Unique states: {self.states_visited}")
        lines.append(f"Max depth: {self.max_depth}")
        lines.append("")

        if self.victory_found:
            lines.append(f"✓ Victory reachable in {self.victory_depth} steps:")
            for i, action in enumerate(self.victory_path, 1):
                lines.append(f"  {i}. {action}")
        else:
            lines.append("✗ No victory path found")

        if self.defeat_states:
            lines.append("")
            lines.append(f"Defeat states found: {len(self.defeat_states)}")

        if self.dead_ends:
            lines.append("")
            lines.append(f"Dead ends found: {len(self.dead_ends)}")

        return "\n".join(lines)


class StateExplorer:
    """Explores the game state space using BFS."""

    def __init__(
        self,
        world: GrueWorld,
        effects: EffectAnalysis,
        relevance: RelevanceAnalysis,
        max_depth: int = 100,
    ):
        self.world = world
        self.effects = effects
        self.relevance = relevance
        self.max_depth = max_depth

        # Runtime we'll use for simulation (will be reset/cloned)
        self._base_runtime = GrueRuntime(world)

    def explore(self) -> ExplorationResult:
        """Run BFS exploration from initial state."""
        result = ExplorationResult()

        # Get initial state
        self._base_runtime.reset()
        initial_state = GameState.from_runtime(
            self._base_runtime, self.relevance.relevant
        )

        # BFS setup
        visited: set[GameState] = {initial_state}
        queue: deque[ExplorationNode] = deque()
        queue.append(ExplorationNode(state=initial_state, depth=0))

        while queue:
            node = queue.popleft()
            result.states_explored += 1
            result.max_depth = max(result.max_depth, node.depth)

            # Depth limit
            if node.depth >= self.max_depth:
                continue

            # Restore state and check victory/defeat
            self._restore_state(node)

            if self._base_runtime.check_victory():
                result.victory_found = True
                result.victory_path = node.path()
                result.victory_depth = node.depth
                # Continue exploring to find all paths (or stop here for efficiency)
                break

            if self._base_runtime.check_defeat():
                result.defeat_states.append((node.state, node.path()))
                continue

            # Enumerate possible actions
            actions = self._enumerate_actions()

            if not actions:
                # Dead end - no actions and not victory/defeat
                result.dead_ends.append((node.state, node.path()))
                continue

            # Try each action
            for action in actions:
                # Save state before action
                saved_state = self._save_runtime_state()

                # Execute action
                action_result = self._base_runtime.do(
                    action.target, action.verb, *action.args
                )

                # Only follow successful actions
                if action_result.outcome == "success":
                    # Process any events (turn tick)
                    self._base_runtime.process_events()

                    # Get new state
                    new_state = GameState.from_runtime(
                        self._base_runtime, self.relevance.relevant
                    )

                    # Add to queue if not visited
                    if new_state not in visited:
                        visited.add(new_state)
                        queue.append(ExplorationNode(
                            state=new_state,
                            parent=node,
                            action=action,
                            depth=node.depth + 1,
                        ))

                # Restore state for next action
                self._restore_runtime_state(saved_state)

        result.states_visited = len(visited)
        return result

    def _enumerate_actions(self) -> list[Action]:
        """Enumerate all valid actions from current state."""
        actions = []

        # Get visible objects
        visible = self._base_runtime.get_visible_objects()

        for obj_name in visible:
            # Get object definition
            if obj_name in self.world.objects:
                obj = self.world.objects[obj_name]
                if hasattr(obj, 'behaviors') and obj.behaviors:
                    for behavior in obj.behaviors:
                        verb = behavior.verb
                        # Skip internal verbs
                        if verb in ("through", "describe", "fdesc"):
                            continue
                        actions.append(Action(target=obj_name, verb=verb))

        # Add movement actions (go direction)
        room = self._base_runtime.get_player_room()
        if room and room in self.world.rooms:
            room_def = self.world.rooms[room]
            for exit_info in room_def.exits:
                actions.append(Action(
                    target=room,
                    verb="go",
                    args=(exit_info.direction,)
                ))

        return actions

    def _restore_state(self, node: ExplorationNode):
        """Restore runtime to a given exploration node's state."""
        # Reset to initial
        self._base_runtime.reset()

        # Replay actions from root
        for action in node.path():
            self._base_runtime.do(action.target, action.verb, *action.args)
            self._base_runtime.process_events()

    def _save_runtime_state(self) -> dict:
        """Save runtime state for restoration."""
        # Deep copy the mutable state
        return {
            "objects": copy.deepcopy(self._base_runtime.state.objects),
            "queues": copy.deepcopy(self._base_runtime.state.queues),
        }

    def _restore_runtime_state(self, saved: dict):
        """Restore runtime state from save."""
        self._base_runtime.state.objects = saved["objects"]
        self._base_runtime.state.queues = saved["queues"]


def explore_state_space(
    world: GrueWorld,
    effects: EffectAnalysis,
    relevance: RelevanceAnalysis,
    max_depth: int = 100,
) -> ExplorationResult:
    """Convenience function to explore a game's state space."""
    explorer = StateExplorer(world, effects, relevance, max_depth)
    return explorer.explore()
