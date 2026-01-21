"""
State space explorer for Grue games.

Performs BFS exploration of the game state space, building an explicit
state transition graph. Uses only puzzle-relevant state for state identity.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Any
import copy

from grue import GrueWorld
from grue.runtime import GrueRuntime

from .effects import StateRef, PropertyRef, LocationRef, QueueRef
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

    Two states with the same GameState are considered identical for
    exploration purposes (visited-set deduplication).
    """
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
            elif isinstance(ref, LocationRef):
                val = runtime.get_object_location(ref.object)
            elif isinstance(ref, QueueRef):
                val = runtime.get_queue_countdown(ref.event)
            else:
                continue
            values.append((str(ref), val))
        return cls(values=tuple(values))

    def __str__(self):
        parts = [f"{k}={v}" for k, v in self.values]
        return "{" + ", ".join(parts) + "}"

    def short_str(self) -> str:
        """Compact representation for graph labels."""
        parts = []
        for k, v in self.values:
            # Shorten @object:property to just the key parts
            short_k = k.replace("@", "").replace(":location", ".loc").replace(":",".")
            if v is True:
                parts.append(short_k)
            elif v is False:
                parts.append(f"!{short_k}")
            elif isinstance(v, str) and v.startswith("@"):
                parts.append(f"{short_k}={v[1:]}")  # Remove @ from value
            else:
                parts.append(f"{short_k}={v}")
        return ", ".join(parts)


@dataclass
class StateNode:
    """A node in the state transition graph."""
    id: int
    state: GameState
    is_victory: bool = False
    is_defeat: bool = False
    depth: int = 0  # Shortest path from initial state


@dataclass
class StateEdge:
    """An edge (transition) in the state transition graph."""
    from_id: int
    to_id: int
    action: Action


@dataclass
class StateGraph:
    """The complete state transition graph."""
    nodes: dict[int, StateNode] = field(default_factory=dict)
    edges: list[StateEdge] = field(default_factory=list)
    initial_id: int = 0

    # Maps GameState to node id for deduplication
    state_to_id: dict[GameState, int] = field(default_factory=dict)

    def add_node(self, state: GameState, is_victory: bool = False,
                 is_defeat: bool = False, depth: int = 0) -> int:
        """Add a node, returning its id. Returns existing id if state seen before."""
        if state in self.state_to_id:
            return self.state_to_id[state]

        node_id = len(self.nodes)
        self.nodes[node_id] = StateNode(
            id=node_id,
            state=state,
            is_victory=is_victory,
            is_defeat=is_defeat,
            depth=depth,
        )
        self.state_to_id[state] = node_id
        return node_id

    def add_edge(self, from_id: int, to_id: int, action: Action):
        """Add a transition edge."""
        self.edges.append(StateEdge(from_id=from_id, to_id=to_id, action=action))

    def get_victory_path(self) -> list[Action] | None:
        """Find shortest path to victory using BFS."""
        victory_nodes = [n for n in self.nodes.values() if n.is_victory]
        if not victory_nodes:
            return None

        # BFS from initial state
        visited = {self.initial_id}
        queue = deque([(self.initial_id, [])])

        # Build adjacency list
        adj: dict[int, list[tuple[int, Action]]] = {i: [] for i in self.nodes}
        for edge in self.edges:
            adj[edge.from_id].append((edge.to_id, edge.action))

        while queue:
            node_id, path = queue.popleft()
            if self.nodes[node_id].is_victory:
                return path

            for next_id, action in adj[node_id]:
                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [action]))

        return None

    def summary(self) -> str:
        """Return a human-readable summary."""
        victory_count = sum(1 for n in self.nodes.values() if n.is_victory)
        defeat_count = sum(1 for n in self.nodes.values() if n.is_defeat)
        max_depth = max((n.depth for n in self.nodes.values()), default=0)

        lines = [
            f"States: {len(self.nodes)}",
            f"Transitions: {len(self.edges)}",
            f"Max depth: {max_depth}",
            f"Victory states: {victory_count}",
            f"Defeat states: {defeat_count}",
        ]

        path = self.get_victory_path()
        if path:
            lines.append("")
            lines.append(f"Shortest victory path ({len(path)} steps):")
            for i, action in enumerate(path, 1):
                lines.append(f"  {i}. {action}")

        return "\n".join(lines)


class StateExplorer:
    """Explores the game state space using BFS, building a transition graph."""

    def __init__(
        self,
        world: GrueWorld,
        relevance: RelevanceAnalysis,
        max_depth: int = 100,
    ):
        self.world = world
        self.relevance = relevance
        self.max_depth = max_depth
        self._runtime = GrueRuntime(world)

    def explore(self) -> StateGraph:
        """Run BFS exploration, returning the state transition graph."""
        graph = StateGraph()

        # Initial state
        self._runtime.reset()
        initial_state = GameState.from_runtime(self._runtime, self.relevance.relevant)
        initial_id = graph.add_node(
            initial_state,
            is_victory=self._runtime.check_victory(),
            is_defeat=self._runtime.check_defeat(),
            depth=0,
        )
        graph.initial_id = initial_id

        # BFS queue: (node_id, depth)
        queue: deque[tuple[int, int]] = deque([(initial_id, 0)])
        processed: set[int] = set()

        while queue:
            node_id, depth = queue.popleft()

            if node_id in processed:
                continue
            processed.add(node_id)

            # Depth limit
            if depth >= self.max_depth:
                continue

            node = graph.nodes[node_id]

            # Don't explore from terminal states
            if node.is_victory or node.is_defeat:
                continue

            # Restore to this state
            self._restore_to_state(node.state)

            # Enumerate and try all actions
            for action in self._enumerate_actions():
                saved = self._save_state()

                result = self._runtime.do(action.target, action.verb, *action.args)

                if result.outcome == "success":
                    self._runtime.process_events()

                    new_state = GameState.from_runtime(
                        self._runtime, self.relevance.relevant
                    )

                    # Add node (or get existing)
                    new_id = graph.add_node(
                        new_state,
                        is_victory=self._runtime.check_victory(),
                        is_defeat=self._runtime.check_defeat(),
                        depth=depth + 1,
                    )

                    # Add edge
                    graph.add_edge(node_id, new_id, action)

                    # Queue for exploration if new
                    if new_id not in processed:
                        queue.append((new_id, depth + 1))

                self._restore_state(saved)

        return graph

    def _enumerate_actions(self) -> list[Action]:
        """Enumerate all valid actions from current state, including arguments."""
        actions = []

        visible = self._runtime.get_visible_objects()
        inventory = self._runtime.get_inventory()
        player_room = self._runtime.get_player_room()

        for obj_name in visible:
            if obj_name not in self.world.objects:
                continue

            obj = self.world.objects[obj_name]
            if not hasattr(obj, 'behaviors') or not obj.behaviors:
                continue

            for behavior in obj.behaviors:
                verb = behavior.verb

                # Skip internal verbs
                if verb in ("through", "describe", "fdesc"):
                    continue

                if not behavior.params:
                    # No parameters - simple action
                    actions.append(Action(target=obj_name, verb=verb))
                else:
                    # Has parameters - enumerate argument combinations
                    # For now, assume object arguments come from visible + inventory
                    arg_candidates = list(set(visible) | set(inventory))

                    if len(behavior.params) == 1:
                        for arg in arg_candidates:
                            actions.append(Action(target=obj_name, verb=verb, args=(arg,)))
                    elif len(behavior.params) == 2:
                        for arg1 in arg_candidates:
                            for arg2 in arg_candidates:
                                actions.append(Action(target=obj_name, verb=verb, args=(arg1, arg2)))
                    # Could extend to more params if needed

        # Movement actions
        if player_room and player_room in self.world.rooms:
            room_def = self.world.rooms[player_room]
            for exit_info in room_def.exits:
                actions.append(Action(
                    target=player_room,
                    verb="go",
                    args=(exit_info.direction,)
                ))

        return actions

    def _restore_to_state(self, target_state: GameState):
        """Restore runtime to match a target state by BFS search."""
        # Simple approach: reset and BFS to find the state
        # (Could be optimized with state snapshots)
        self._runtime.reset()
        current = GameState.from_runtime(self._runtime, self.relevance.relevant)

        if current == target_state:
            return

        # BFS to find path to target state
        visited = {current}
        queue = deque([(current, [])])

        while queue:
            state, path = queue.popleft()

            # Restore to this state
            self._runtime.reset()
            for action in path:
                self._runtime.do(action.target, action.verb, *action.args)
                self._runtime.process_events()

            # Try all actions
            for action in self._enumerate_actions():
                saved = self._save_state()
                result = self._runtime.do(action.target, action.verb, *action.args)

                if result.outcome == "success":
                    self._runtime.process_events()
                    new_state = GameState.from_runtime(self._runtime, self.relevance.relevant)

                    if new_state == target_state:
                        return  # Found it, runtime is now in target state

                    if new_state not in visited:
                        visited.add(new_state)
                        queue.append((new_state, path + [action]))

                self._restore_state(saved)

    def _save_state(self) -> dict:
        """Save runtime state."""
        return {
            "objects": copy.deepcopy(self._runtime.state.objects),
            "queues": copy.deepcopy(self._runtime.state.queues),
        }

    def _restore_state(self, saved: dict):
        """Restore runtime state."""
        self._runtime.state.objects = saved["objects"]
        self._runtime.state.queues = saved["queues"]


def explore_state_space(
    world: GrueWorld,
    relevance: RelevanceAnalysis,
    max_depth: int = 100,
) -> StateGraph:
    """Convenience function to explore a game's state space."""
    explorer = StateExplorer(world, relevance, max_depth)
    return explorer.explore()
