"""
State space explorer for Grue games.

Performs constraint-guided exploration of the game state space, building an
explicit state transition graph. Uses only puzzle-relevant state for identity.

Uses a priority queue where states closer to victory (more constraints satisfied)
are explored first. Can stop at first victory or explore the full state space.
"""

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from heapq import heappush, heappop
from typing import Any, Callable, TYPE_CHECKING

from grue import GrueWorld
from grue.runtime import GrueRuntime

from .effects import StateRef, PropertyRef, LocationRef, QueueRef, HeldRef, BehaviorRef, EffectAnalysis
from .state import StatePath
from .domains import AbstractionConfig

# Note: ConstraintHierarchy is from clustering.py which is in deferred/
# We keep the type hint but don't import the module
if TYPE_CHECKING:
    from .deferred.clustering import ConstraintHierarchy


def _extract_path_value(runtime: GrueRuntime, path: StatePath) -> Any:
    """Extract a value from runtime for a given StatePath."""
    kind = path.kind
    if kind == "loc":
        return runtime.get_object_location(path.object)
    elif kind == "prop":
        return runtime.get_object_property(path.object, path.property_name)
    elif kind == "queue":
        return runtime.get_queue_countdown(path.event_name)
    elif kind == "held":
        # Abstract held predicate: True if location is @player
        loc = runtime.get_object_location(path.object)
        return loc == runtime.player_name
    else:
        return None


class ExplorationMode(Enum):
    """How to explore the state space."""
    GUIDED = "guided"  # Priority queue by constraint satisfaction (full exploration)
    GUIDED_FIRST_VICTORY = "guided_first_victory"  # Stop at first victory
    SUBGOAL = "subgoal"  # Stop when goal_check returns True


@dataclass
class Subgoal:
    """A subgoal to achieve during exploration.

    A subgoal defines a target state condition. When the runtime reaches
    a state where check() returns True, exploration stops.

    Subgoals can be chained: once achieved, the path becomes the setup
    for the next subgoal exploration.

    Attributes:
        name: Human-readable description
        check: Function that takes runtime and returns True when goal is achieved
        state_refs: State refs to track for this subgoal exploration
    """
    name: str
    check: Callable[["GrueRuntime"], bool]
    state_refs: set[StateRef] = field(default_factory=set)

    @staticmethod
    def held(obj: str, name: str | None = None) -> "Subgoal":
        """Create a subgoal for holding an object.

        Always includes player location to enable navigation-based exploration.
        """
        return Subgoal(
            name=name or f"{obj} held",
            check=lambda rt: rt.get_object_location(obj) == "@player",
            state_refs={LocationRef(obj), LocationRef("@player")},
        )

    @staticmethod
    def property_equals(obj: str, prop: str, value: Any, name: str | None = None) -> "Subgoal":
        """Create a subgoal for a property having a specific value.

        Always includes player location to enable navigation-based exploration.
        """
        return Subgoal(
            name=name or f"{obj}:{prop} = {value}",
            check=lambda rt: rt.get_object_property(obj, prop) == value,
            state_refs={PropertyRef(obj, prop), LocationRef("@player")},
        )

    @staticmethod
    def location_not(obj: str, loc: str, name: str | None = None) -> "Subgoal":
        """Create a subgoal for an object NOT being at a location.

        Always includes player location to enable navigation-based exploration.
        """
        return Subgoal(
            name=name or f"{obj} not at {loc}",
            check=lambda rt: rt.get_object_location(obj) != loc,
            state_refs={LocationRef(obj), LocationRef("@player")},
        )


@dataclass
class SyntheticState:
    """A synthetic starting state for isolated puzzle testing.

    Instead of replaying actions to reach a state, directly set state values.
    This allows exploring puzzle segments in isolation, bypassing dependencies.

    Use cases:
    - Test if a subgoal is achievable given certain preconditions
    - Isolate puzzle segments from their prerequisites
    - Debug specific game states without full replay

    Example:
        # Test: can we sever the cord if we start with axe and gloves?
        synthetic = SyntheticState(
            locations={"@player": "@inf-5", "@axe": "@player", "@gloves": "@player"},
            properties={("@emergency-cabinet", "rmung"): True}
        )
        path, stats = explore_subgoal(
            world,
            Subgoal.property_equals("@power-cord", "severed", True),
            setup=synthetic.apply
        )
    """

    locations: dict[str, str] = field(default_factory=dict)
    properties: dict[tuple[str, str], Any] = field(default_factory=dict)

    def apply(self, runtime: "GrueRuntime") -> None:
        """Apply this synthetic state to a runtime."""
        for obj, loc in self.locations.items():
            runtime.move_object(obj, loc)
        for (obj, prop), value in self.properties.items():
            runtime.set_object_property(obj, prop, value)

    def __repr__(self) -> str:
        parts = []
        if self.locations:
            locs = ", ".join(f"{k}={v}" for k, v in sorted(self.locations.items()))
            parts.append(f"locations={{{locs}}}")
        if self.properties:
            props = ", ".join(f"{k[0]}.{k[1]}={v}" for k, v in sorted(self.properties.items()))
            parts.append(f"properties={{{props}}}")
        return f"SyntheticState({', '.join(parts)})"


@dataclass
class ExplorationStats:
    """Statistics from exploration."""
    states_explored: int = 0
    states_skipped_depth: int = 0
    states_skipped_victory_found: int = 0
    states_skipped_max_states: int = 0
    states_skipped_goal_found: int = 0
    victory_found_at_depth: int | None = None
    victory_found_after_states: int | None = None
    goal_found_at_depth: int | None = None
    goal_found_after_states: int | None = None

    def summary(self) -> str:
        lines = [
            f"States explored: {self.states_explored}",
            f"States skipped (depth limit): {self.states_skipped_depth}",
        ]
        if self.victory_found_at_depth is not None:
            lines.append(f"Victory found at depth: {self.victory_found_at_depth}")
            lines.append(f"Victory found after exploring: {self.victory_found_after_states} states")
        if self.goal_found_at_depth is not None:
            lines.append(f"Goal found at depth: {self.goal_found_at_depth}")
            lines.append(f"Goal found after exploring: {self.goal_found_after_states} states")
        if self.states_skipped_victory_found > 0:
            lines.append(f"States skipped (victory found): {self.states_skipped_victory_found}")
        if self.states_skipped_goal_found > 0:
            lines.append(f"States skipped (goal found): {self.states_skipped_goal_found}")
        if self.states_skipped_max_states > 0:
            lines.append(f"States skipped (max states reached): {self.states_skipped_max_states}")
        return "\n".join(lines)


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
        """Extract relevant state from a runtime (legacy StateRef API)."""
        values = []
        for ref in sorted(relevant, key=str):
            if isinstance(ref, PropertyRef):
                val = runtime.get_object_property(ref.object, ref.property)
            elif isinstance(ref, LocationRef):
                val = runtime.get_object_location(ref.object)
            elif isinstance(ref, QueueRef):
                val = runtime.get_queue_countdown(ref.event)
            elif isinstance(ref, HeldRef):
                # HeldRef is True if object's location is @player
                loc = runtime.get_object_location(ref.object)
                val = (loc == runtime.player_name)
            else:
                continue
            # Convert lists to tuples for hashability
            if isinstance(val, list):
                val = tuple(val)
            values.append((str(ref), val))
        return cls(values=tuple(values))

    @classmethod
    def from_abstraction_config(
        cls,
        runtime: GrueRuntime,
        config: AbstractionConfig,
    ) -> "GameState":
        """Extract state using AbstractionConfig with automatic abstraction.

        This is the new API that uses inferred value domains for optimal
        state space exploration. Abstraction functions are applied to
        produce minimal fingerprints.
        """
        # Extract concrete values for all tracked paths
        state_values: dict[StatePath, Any] = {}
        for path in config.tracked_paths:
            val = _extract_path_value(runtime, path)
            # Convert lists to tuples for hashability
            if isinstance(val, list):
                val = tuple(val)
            state_values[path] = val

        # Use AbstractionConfig.fingerprint() to apply abstraction
        fingerprint = config.fingerprint(state_values)

        # Convert StatePath keys to strings for consistency
        values = tuple((str(path), val) for path, val in fingerprint)
        return cls(values=values)

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
    """Explores the game state space using constraint-guided search.

    Uses a priority queue where priority is based on:
    1. Number of satisfied constraints (more = better = lower priority number)
    2. Depth (shallower = better, as tiebreaker)

    States closer to victory (more constraints satisfied) are explored first.

    Supports two APIs for state fingerprinting:
    - Legacy: set[StateRef] with manual state extraction
    - New: AbstractionConfig with automatic value abstraction
    """

    def __init__(
        self,
        world: GrueWorld,
        state_refs: set[StateRef] | None = None,
        max_depth: int = 100,
        mode: ExplorationMode = ExplorationMode.GUIDED,
        hierarchy: "ConstraintHierarchy | None" = None,
        max_states: int | None = None,
        abstraction_config: AbstractionConfig | None = None,
        setup: Callable[["GrueRuntime"], None] | None = None,
        goal_check: Callable[["GrueRuntime"], bool] | None = None,
        effects: EffectAnalysis | None = None,
    ):
        self.world = world
        self.state_refs = state_refs
        self.max_depth = max_depth
        self.max_states = max_states
        self.mode = mode
        self.hierarchy = hierarchy
        self.abstraction_config = abstraction_config
        self.setup = setup
        self.goal_check = goal_check
        self.effects = effects
        self._runtime = GrueRuntime(world)
        self.stats = ExplorationStats()
        self.goal_path: list[Action] | None = None  # Path to goal if found

        # Validate: must provide either state_refs or abstraction_config
        if state_refs is None and abstraction_config is None:
            raise ValueError("Must provide either state_refs or abstraction_config")

        # Compute relevant behaviors for action pruning
        # A behavior is relevant if it can modify any tracked state
        self._relevant_behaviors: set[tuple[str, str]] | None = None
        self._objects_with_tracked_location: set[str] | None = None
        if effects is not None and state_refs is not None:
            self._relevant_behaviors = set()
            self._objects_with_tracked_location = set()
            for ref in state_refs:
                # Track objects whose location is tracked (for runtime:take/drop)
                # Both LocationRef and HeldRef mean we care about the object's location
                if isinstance(ref, LocationRef):
                    self._objects_with_tracked_location.add(ref.object)
                elif isinstance(ref, HeldRef):
                    self._objects_with_tracked_location.add(ref.object)

                # For HeldRef, also check LocationRef since HeldRef is an abstraction
                # of location (held = location == @player)
                refs_to_check = [ref]
                if isinstance(ref, HeldRef):
                    refs_to_check.append(LocationRef(ref.object))

                for r in refs_to_check:
                    if r in effects.modifies:
                        for beh in effects.modifies[r]:
                            # beh is BehaviorRef with .object and .verb
                            self._relevant_behaviors.add((beh.object, beh.verb))

    def _extract_game_state(self) -> GameState:
        """Extract current game state using the appropriate API."""
        if self.abstraction_config is not None:
            return GameState.from_abstraction_config(self._runtime, self.abstraction_config)
        else:
            return GameState.from_runtime(self._runtime, self.state_refs)

    def explore(self) -> StateGraph:
        """Run constraint-guided exploration, returning the state transition graph.

        Priority is computed as: (-constraints_satisfied, depth)
        - Negative constraints so more satisfied = lower priority (explored first)
        - Depth as tiebreaker so shallower states are explored first

        If hierarchy is not provided, uses depth-only ordering (FIFO).

        In SUBGOAL mode, exploration stops when goal_check returns True.
        The path to the goal is stored in self.goal_path.
        """
        graph = StateGraph()
        victory_found = False
        goal_found = False

        # Initial state
        self._runtime.reset()

        # Apply setup function if provided (for puzzle isolation)
        if self.setup is not None:
            self.setup(self._runtime)

        initial_state = self._extract_game_state()
        is_victory = self._runtime.check_victory()
        is_defeat = self._runtime.check_defeat()

        initial_id = graph.add_node(
            initial_state,
            is_victory=is_victory,
            is_defeat=is_defeat,
            depth=0,
            path=[],
        )
        graph.initial_id = initial_id

        if is_victory:
            victory_found = True
            self.stats.victory_found_at_depth = 0
            self.stats.victory_found_after_states = 1

        # Check if initial state already satisfies goal
        if self.goal_check is not None and self.goal_check(self._runtime):
            goal_found = True
            self.goal_path = []
            self.stats.goal_found_at_depth = 0
            self.stats.goal_found_after_states = 1
            if self.mode == ExplorationMode.SUBGOAL:
                return graph

        # Priority queue: (priority, counter, node_id, depth)
        # counter breaks ties for equal priority (FIFO within priority level)
        counter = 0
        priority = self._compute_priority(initial_state, 0)
        pq: list[tuple[tuple[int, int], int, int, int]] = [(priority, counter, initial_id, 0)]
        processed: set[int] = set()

        while pq:
            _, _, node_id, depth = heappop(pq)

            if node_id in processed:
                continue
            processed.add(node_id)
            self.stats.states_explored += 1

            # Early termination for first-victory mode
            if self.mode == ExplorationMode.GUIDED_FIRST_VICTORY and victory_found:
                self.stats.states_skipped_victory_found += 1
                continue

            # Early termination for subgoal mode
            if self.mode == ExplorationMode.SUBGOAL and goal_found:
                self.stats.states_skipped_goal_found += 1
                continue

            # Max states limit
            if self.max_states is not None and self.stats.states_explored >= self.max_states:
                self.stats.states_skipped_max_states = len(pq)  # Track how many we're leaving unexplored
                break

            # Depth limit
            if depth >= self.max_depth:
                self.stats.states_skipped_depth += 1
                continue

            node = graph.nodes[node_id]

            # Don't explore from terminal states
            if node.is_victory or node.is_defeat:
                continue

            # Restore to this state by replaying the path, then enumerate actions
            self._replay_path(node.path)
            actions = self._enumerate_actions()

            # Try each action via replay (avoids expensive deepcopy save/restore)
            for action in actions:
                # Replay path + try action (cheaper than deepcopy save/restore)
                self._replay_path(node.path)

                # Handle wait action specially - just process events
                if action.target == "_wait":
                    self._runtime.process_events()
                    action_succeeded = True
                else:
                    result = self._runtime.do(action.target, action.verb, *action.args)
                    action_succeeded = result.outcome == "success"
                    if action_succeeded:
                        self._runtime.process_events()

                if action_succeeded:

                    new_state = self._extract_game_state()

                    is_victory = self._runtime.check_victory()
                    is_defeat = self._runtime.check_defeat()

                    # Build new path (only for new states)
                    new_path = node.path + [action] if new_state not in graph.state_to_id else None

                    # Add node (or get existing)
                    new_id = graph.add_node(
                        new_state,
                        is_victory=is_victory,
                        is_defeat=is_defeat,
                        depth=depth + 1,
                        path=new_path,
                    )

                    # Track victory discovery
                    if is_victory and not victory_found:
                        victory_found = True
                        self.stats.victory_found_at_depth = depth + 1
                        self.stats.victory_found_after_states = self.stats.states_explored

                    # Check goal condition
                    if self.goal_check is not None and not goal_found:
                        if self.goal_check(self._runtime):
                            goal_found = True
                            self.goal_path = node.path + [action]
                            self.stats.goal_found_at_depth = depth + 1
                            self.stats.goal_found_after_states = self.stats.states_explored

                    # Add edge
                    graph.add_edge(node_id, new_id, action)

                    # Queue for exploration if new
                    if new_id not in processed:
                        counter += 1
                        priority = self._compute_priority(new_state, depth + 1)
                        heappush(pq, (priority, counter, new_id, depth + 1))

        return graph

    def _compute_priority(self, state: GameState, depth: int) -> tuple[int, int]:
        """Compute priority for guided exploration.

        Returns (negative_satisfied_count, depth) so that:
        - States with more constraints satisfied are explored first (more negative)
        - Within same satisfaction level, shallower states come first
        """
        if self.hierarchy is None:
            # No hierarchy - use depth only (BFS-like behavior)
            return (0, depth)

        state_values = dict(state.values)
        signature = self.hierarchy.get_signature(state_values)
        satisfied_count = sum(signature.bits)

        # Negative so more satisfied = lower priority = explored first
        return (-satisfied_count, depth)

    def _replay_path(self, path: list[Action]):
        """Restore runtime to a state by replaying actions from initial."""
        self._runtime.reset()
        # Reapply setup function if provided
        if self.setup is not None:
            self.setup(self._runtime)
        for action in path:
            if action.target == "_wait":
                # Wait just processes events
                self._runtime.process_events()
            else:
                self._runtime.do(action.target, action.verb, *action.args)
                self._runtime.process_events()

    def _enumerate_actions(self) -> list[Action]:
        """Enumerate all valid actions from current state, including arguments.

        When effect analysis is provided, prunes actions that cannot modify
        any tracked state. This significantly reduces the branching factor
        by skipping observation-only behaviors like 'examine', 'ask-about', etc.
        """
        actions = []

        # Use for_description=False to include nodesc objects (like power-cord)
        # since exploration is about interaction possibilities, not room descriptions
        visible = self._runtime.get_visible_objects(for_description=False)
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

                # Action pruning: skip behaviors that don't modify tracked state
                if self._relevant_behaviors is not None:
                    if (obj_name, verb) not in self._relevant_behaviors:
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

        # Runtime default actions for takeable objects
        # Runtime:take modifies object location - only include for objects whose
        # location is tracked, or if no pruning is active
        for obj_name in visible:
            if obj_name not in self.world.objects:
                continue
            obj = self.world.objects[obj_name]
            # Add 'take' for takeable objects not in inventory
            if obj.properties.get("takeable") and obj_name not in inventory:
                # Check if this object's location is tracked
                if self._objects_with_tracked_location is None or \
                   obj_name in self._objects_with_tracked_location:
                    actions.append(Action(target=obj_name, verb="take"))

        # Runtime default actions for inventory items
        # Runtime:drop modifies object location - only include for objects whose
        # location is tracked, or if no pruning is active
        for obj_name in inventory:
            if obj_name not in self.world.objects:
                continue
            # Add 'drop' for items in inventory
            if self._objects_with_tracked_location is None or \
               obj_name in self._objects_with_tracked_location:
                actions.append(Action(target=obj_name, verb="drop"))

        # Movement actions - always relevant since they change player location
        if player_room and player_room in self.world.rooms:
            room_def = self.world.rooms[player_room]
            for exit_info in room_def.exits:
                actions.append(Action(
                    target=exit_info.to,  # Destination room, not source
                    verb="go",
                    args=(exit_info.direction,)
                ))

        # Wait action - always available to advance time (events may modify state)
        actions.append(Action(target="_wait", verb="wait"))

        return actions



def explore_state_space(
    world: GrueWorld,
    state_refs: set[StateRef] | None = None,
    max_depth: int = 100,
    mode: ExplorationMode = ExplorationMode.GUIDED,
    hierarchy: "ConstraintHierarchy | None" = None,
    max_states: int | None = None,
    abstraction_config: AbstractionConfig | None = None,
    effects: EffectAnalysis | None = None,
) -> tuple[StateGraph, ExplorationStats]:
    """Convenience function to explore a game's state space.

    Args:
        world: The game world to explore
        state_refs: Set of state refs to track for state fingerprinting (legacy API).
            Typically derived from constraint back-propagation.
        max_depth: Maximum exploration depth
        mode: GUIDED (full exploration) or GUIDED_FIRST_VICTORY (stop at first victory)
        hierarchy: Constraint hierarchy for prioritization (recommended)
        max_states: Maximum states to explore (None = unlimited)
        abstraction_config: AbstractionConfig for state fingerprinting (new API).
            When provided, uses automatic value abstraction.
        effects: EffectAnalysis for action pruning. When provided, only actions
            that can modify tracked state are enumerated, significantly reducing
            branching factor.

    Returns:
        Tuple of (state_graph, exploration_stats)

    Note:
        Must provide either state_refs (legacy) or abstraction_config (new).
    """
    explorer = StateExplorer(
        world, state_refs, max_depth, mode, hierarchy, max_states, abstraction_config,
        effects=effects,
    )
    graph = explorer.explore()
    return graph, explorer.stats


def explore_with_inferred_abstraction(
    world: GrueWorld,
    max_depth: int = 100,
    mode: ExplorationMode = ExplorationMode.GUIDED,
    hierarchy: "ConstraintHierarchy | None" = None,
    max_states: int | None = None,
    paths: set[StatePath] | None = None,
) -> tuple[StateGraph, ExplorationStats, AbstractionConfig]:
    """Explore using automatically inferred value domains.

    This is the new recommended API that:
    1. Runs effect analysis on the game
    2. Infers optimal value domains for state paths
    3. Explores using the inferred AbstractionConfig

    Args:
        world: The game world to explore
        max_depth: Maximum exploration depth
        mode: GUIDED (full exploration) or GUIDED_FIRST_VICTORY (stop at first victory)
        hierarchy: Constraint hierarchy for prioritization (recommended)
        max_states: Maximum states to explore (None = unlimited)
        paths: Optional subset of StatePaths to track. If None, tracks all relevant paths.

    Returns:
        Tuple of (state_graph, exploration_stats, abstraction_config)
    """
    from .effects import analyze_effects
    from .domains import infer_abstraction

    # Step 1: Effect analysis
    effects = analyze_effects(world)

    # Step 2: Infer value domains
    config = infer_abstraction(world, effects, paths)

    # Step 3: Explore with inferred config
    explorer = StateExplorer(
        world,
        state_refs=None,
        max_depth=max_depth,
        mode=mode,
        hierarchy=hierarchy,
        max_states=max_states,
        abstraction_config=config,
    )
    graph = explorer.explore()
    return graph, explorer.stats, config


def explore_subgoal(
    world: GrueWorld,
    subgoal: Subgoal,
    max_depth: int = 100,
    max_states: int | None = None,
    setup: Callable[["GrueRuntime"], None] | None = None,
) -> tuple[list[Action] | None, ExplorationStats]:
    """Explore to achieve a specific subgoal.

    This is a convenience function for subgoal-based exploration. It:
    1. Uses the subgoal's state_refs for fingerprinting
    2. Stops exploration as soon as the goal is achieved
    3. Returns the path to the goal (or None if not found)

    Args:
        world: The game world to explore
        subgoal: The Subgoal to achieve
        max_depth: Maximum exploration depth
        max_states: Maximum states to explore (None = unlimited)
        setup: Optional function to set up initial state (for puzzle isolation)

    Returns:
        Tuple of (path_to_goal, exploration_stats)
        path_to_goal is None if the goal was not found
    """
    explorer = StateExplorer(
        world,
        state_refs=subgoal.state_refs or {LocationRef("@player")},
        max_depth=max_depth,
        mode=ExplorationMode.SUBGOAL,
        max_states=max_states,
        setup=setup,
        goal_check=subgoal.check,
    )
    explorer.explore()
    return explorer.goal_path, explorer.stats


def explore_subgoals(
    world: GrueWorld,
    subgoals: list[Subgoal],
    max_depth_per_goal: int = 50,
    max_states_per_goal: int | None = None,
    initial_state: SyntheticState | Callable[["GrueRuntime"], None] | None = None,
) -> tuple[list[Action] | None, list[ExplorationStats]]:
    """Chain multiple subgoals, exploring each in sequence.

    Each subgoal is explored starting from the state reached by achieving
    the previous subgoal. This allows breaking a large puzzle into smaller,
    more tractable pieces.

    Args:
        world: The game world to explore
        subgoals: List of Subgoals to achieve in order
        max_depth_per_goal: Maximum exploration depth for each subgoal
        max_states_per_goal: Maximum states per subgoal exploration
        initial_state: Optional initial state for exploration. Can be:
            - SyntheticState: directly sets locations/properties
            - Callable: custom setup function (runtime -> None)
            - None: start from world's default initial state

    Returns:
        Tuple of (combined_path, list_of_stats)
        combined_path is None if any subgoal was not achievable
        list_of_stats contains stats for each subgoal exploration
    """
    combined_path: list[Action] = []
    all_stats: list[ExplorationStats] = []

    # Normalize initial_state to a callable
    if initial_state is None:
        base_setup: Callable[[GrueRuntime], None] | None = None
    elif isinstance(initial_state, SyntheticState):
        base_setup = initial_state.apply
    else:
        base_setup = initial_state

    for i, subgoal in enumerate(subgoals):
        # Create setup function that:
        # 1. Applies initial state (if any)
        # 2. Replays the combined path so far
        if combined_path or base_setup:
            prefix = list(combined_path)  # Copy to avoid closure issues
            initial = base_setup  # Capture for closure

            def setup(runtime: GrueRuntime, prefix=prefix, initial=initial):
                if initial:
                    initial(runtime)
                for action in prefix:
                    runtime.do(action.target, action.verb, *action.args)
                    runtime.process_events()
        else:
            setup = None

        path, stats = explore_subgoal(
            world,
            subgoal,
            max_depth=max_depth_per_goal,
            max_states=max_states_per_goal,
            setup=setup,
        )
        all_stats.append(stats)

        if path is None:
            # This subgoal was not achievable
            return None, all_stats

        combined_path.extend(path)

    return combined_path, all_stats
