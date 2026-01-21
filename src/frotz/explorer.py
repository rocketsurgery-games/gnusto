"""
State space explorer for Grue games.

Performs BFS exploration of the game state space, building an explicit
state transition graph. Uses only puzzle-relevant state for state identity.
"""

from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

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
            # Convert lists to tuples for hashability
            if isinstance(val, list):
                val = tuple(val)
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
    path: list[Action] = field(default_factory=list)  # Actions to reach this state


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
                 is_defeat: bool = False, depth: int = 0,
                 path: list[Action] | None = None) -> int:
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
            path=path or [],
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

    def get_victory_reachable(self) -> set[int]:
        """Find all states from which victory is reachable (backward reachability)."""
        victory_ids = {n.id for n in self.nodes.values() if n.is_victory}
        if not victory_ids:
            return set()

        # Build reverse adjacency list (who can reach whom)
        reverse_adj: dict[int, list[int]] = {i: [] for i in self.nodes}
        for edge in self.edges:
            reverse_adj[edge.to_id].append(edge.from_id)

        # BFS backwards from victory states
        reachable = set(victory_ids)
        queue = deque(victory_ids)

        while queue:
            node_id = queue.popleft()
            for prev_id in reverse_adj[node_id]:
                if prev_id not in reachable:
                    reachable.add(prev_id)
                    queue.append(prev_id)

        return reachable

    def get_black_holes(self) -> set[int]:
        """Find all states from which victory is unreachable (P(doom)=1)."""
        victory_reachable = self.get_victory_reachable()
        return set(self.nodes.keys()) - victory_reachable

    def get_black_hole_entries(self) -> list[tuple[StateEdge, dict, dict]]:
        """
        Find all entry points into black holes.

        Returns list of (edge, from_state_props, to_state_props) tuples where:
        - edge crosses from victory-reachable to black hole
        - from_state_props: dict of property name -> value for the safe state
        - to_state_props: dict of property name -> value for the doomed state
        """
        victory_reachable = self.get_victory_reachable()
        black_holes = set(self.nodes.keys()) - victory_reachable

        entries = []
        for edge in self.edges:
            if edge.from_id in victory_reachable and edge.to_id in black_holes:
                from_props = dict(self.nodes[edge.from_id].state.values)
                to_props = dict(self.nodes[edge.to_id].state.values)
                entries.append((edge, from_props, to_props))

        return entries

    def cluster_black_hole_entries(self) -> list[dict]:
        """
        Cluster black hole entry points by what changed when entering doom.

        Returns list of clusters, each containing:
        - 'delta': dict of properties that changed (prop -> new_value)
        - 'entries': list of (edge, from_props, to_props) tuples
        - 'actions': set of action types that lead to this cluster
        """
        entries = self.get_black_hole_entries()
        if not entries:
            return []

        # For each entry, compute the delta (what changed)
        # Group by delta to find common "doom triggers"
        by_delta: dict[tuple, list] = {}
        for entry in entries:
            edge, from_props, to_props = entry
            # Compute delta: properties that changed
            delta = {}
            for prop, new_val in to_props.items():
                old_val = from_props.get(prop)
                if old_val != new_val:
                    delta[prop] = new_val

            key = tuple(sorted(delta.items()))
            if key not in by_delta:
                by_delta[key] = []
            by_delta[key].append(entry)

        # Convert to cluster format
        clusters = []
        for delta_key, delta_entries in by_delta.items():
            delta = dict(delta_key)
            actions = {e[0].action.verb for e in delta_entries}
            clusters.append({
                'delta': delta,
                'entries': delta_entries,
                'actions': actions,
            })

        # Sort by number of entries (most common first)
        result = sorted(clusters, key=lambda c: -len(c['entries']))
        return result

    def minimize(self) -> "StateGraph":
        """
        Return a bisimulation-minimized version of this graph.

        Uses Hopcroft-style partition refinement:
        1. Initial partition: {Victory}, {Defeat}, {Others}
        2. Refine by signature: (action, target_partition) pairs
        3. Stop at fixed point

        Terminal states (victory/defeat) are sinks with no outgoing transitions,
        so all same-type terminals are bisimilar.
        """
        if not self.nodes:
            return StateGraph()

        # Build adjacency list for outgoing edges
        edges_from: dict[int, list[StateEdge]] = {i: [] for i in self.nodes}
        for edge in self.edges:
            edges_from[edge.from_id].append(edge)

        # Initial partition: victory, defeat, others
        victory_ids = {n.id for n in self.nodes.values() if n.is_victory}
        defeat_ids = {n.id for n in self.nodes.values() if n.is_defeat}
        other_ids = set(self.nodes.keys()) - victory_ids - defeat_ids

        partitions: list[set[int]] = []
        if victory_ids:
            partitions.append(victory_ids)
        if defeat_ids:
            partitions.append(defeat_ids)
        if other_ids:
            partitions.append(other_ids)

        def get_signature(state_id: int) -> frozenset:
            """Compute signature: set of (action_key, target_partition_idx) pairs."""
            # Build state -> partition index mapping
            state_to_part = {}
            for i, part in enumerate(partitions):
                for s in part:
                    state_to_part[s] = i

            sig = set()
            for edge in edges_from[state_id]:
                target_part = state_to_part[edge.to_id]
                action_key = (edge.action.verb, edge.action.target, edge.action.args)
                sig.add((action_key, target_part))
            return frozenset(sig)

        # Partition refinement loop
        changed = True
        while changed:
            changed = False
            new_partitions = []

            for part in partitions:
                if len(part) <= 1:
                    new_partitions.append(part)
                    continue

                # Group by signature
                sig_groups: dict[frozenset, set[int]] = {}
                for state_id in part:
                    sig = get_signature(state_id)
                    if sig not in sig_groups:
                        sig_groups[sig] = set()
                    sig_groups[sig].add(state_id)

                # If partition splits, we made progress
                if len(sig_groups) > 1:
                    changed = True

                new_partitions.extend(sig_groups.values())

            partitions = new_partitions

        # Build minimized graph
        # Pick representative from each partition (prefer initial state if present)
        part_to_rep: dict[int, int] = {}
        state_to_part: dict[int, int] = {}

        for i, part in enumerate(partitions):
            for s in part:
                state_to_part[s] = i
            # Prefer initial state as representative
            if self.initial_id in part:
                part_to_rep[i] = self.initial_id
            else:
                part_to_rep[i] = min(part)  # Deterministic choice

        # Create new graph with representatives only
        minimized = StateGraph()

        # Map old rep ids to new sequential ids
        rep_to_new_id: dict[int, int] = {}

        for i, part in enumerate(partitions):
            rep = part_to_rep[i]
            old_node = self.nodes[rep]

            # Create merged state label
            if len(part) > 1:
                # Merged node - note how many states collapsed
                merged_state = GameState(values=old_node.state.values)
            else:
                merged_state = old_node.state

            new_id = minimized.add_node(
                merged_state,
                is_victory=old_node.is_victory,
                is_defeat=old_node.is_defeat,
                depth=old_node.depth,
            )
            rep_to_new_id[rep] = new_id

            # Track initial state
            if self.initial_id in part:
                minimized.initial_id = new_id

        # Add edges (deduplicated by from/to/action)
        seen_edges: set[tuple[int, int, str, str, tuple]] = set()
        for edge in self.edges:
            from_part = state_to_part[edge.from_id]
            to_part = state_to_part[edge.to_id]

            from_rep = part_to_rep[from_part]
            to_rep = part_to_rep[to_part]

            new_from = rep_to_new_id[from_rep]
            new_to = rep_to_new_id[to_rep]

            edge_key = (new_from, new_to, edge.action.verb, edge.action.target, edge.action.args)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                minimized.add_edge(new_from, new_to, edge.action)

        return minimized

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
            path=[],
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

            # Restore to this state by replaying the path
            self._replay_path(node.path)

            # Enumerate and try all actions
            for action in self._enumerate_actions():
                saved = self._save_state()

                result = self._runtime.do(action.target, action.verb, *action.args)

                if result.outcome == "success":
                    self._runtime.process_events()

                    new_state = GameState.from_runtime(
                        self._runtime, self.relevance.relevant
                    )

                    # Build new path (only for new states)
                    new_path = node.path + [action] if new_state not in graph.state_to_id else None

                    # Add node (or get existing)
                    new_id = graph.add_node(
                        new_state,
                        is_victory=self._runtime.check_victory(),
                        is_defeat=self._runtime.check_defeat(),
                        depth=depth + 1,
                        path=new_path,
                    )

                    # Add edge
                    graph.add_edge(node_id, new_id, action)

                    # Queue for exploration if new
                    if new_id not in processed:
                        queue.append((new_id, depth + 1))

                self._restore_state(saved)

        return graph

    def _replay_path(self, path: list[Action]):
        """Restore runtime to a state by replaying actions from initial."""
        self._runtime.reset()
        for action in path:
            self._runtime.do(action.target, action.verb, *action.args)
            self._runtime.process_events()

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

    def _save_state(self) -> dict:
        """Save runtime state for later restoration."""
        return {
            "objects": deepcopy(self._runtime.state.objects),
            "queues": deepcopy(self._runtime.state.queues),
        }

    def _restore_state(self, saved: dict):
        """Restore runtime state from a saved snapshot."""
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
