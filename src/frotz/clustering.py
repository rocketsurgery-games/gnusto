"""
Constraint-based hierarchical state clustering for Grue games.

This module enables:
1. State-independent constraint discovery from game definitions
2. Hierarchical clustering by constraint satisfaction
3. On-demand (lazy) state exploration guided by constraints
4. Anomaly detection for states outside expected progression

Key insight: The constraint tree is a MAP we can use to navigate the state
space, not just a summary built after exhaustive exploration.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from grue import GrueWorld
from grue.runtime import GrueRuntime

from .effects import EffectAnalysis, StateRef, PropertyRef, LocationRef
from .relevance import RelevanceAnalysis
from .backward import (
    BackwardAnalyzer,
    Constraint,
    ConstraintTree,
    ConstraintNode,
    build_victory_constraints,
    _extract_constraints_from_expr,
)
from .explorer import GameState, StateGraph, Action


@dataclass(frozen=True)
class ClusterSignature:
    """
    A bit vector representing which constraints are satisfied.

    Each bit position corresponds to a constraint in the hierarchy.
    This is the identity of a cluster - states with the same signature
    belong to the same cluster.
    """
    bits: tuple[bool, ...]

    def __str__(self) -> str:
        return "".join("1" if b else "0" for b in self.bits)

    def hamming_distance(self, other: "ClusterSignature") -> int:
        """Number of bits that differ between signatures."""
        return sum(a != b for a, b in zip(self.bits, other.bits))

    def satisfied_indices(self) -> list[int]:
        """Return indices of satisfied constraints."""
        return [i for i, b in enumerate(self.bits) if b]

    def unsatisfied_indices(self) -> list[int]:
        """Return indices of unsatisfied constraints."""
        return [i for i, b in enumerate(self.bits) if not b]

    def with_bit(self, index: int, value: bool) -> "ClusterSignature":
        """Return new signature with one bit changed."""
        bits = list(self.bits)
        bits[index] = value
        return ClusterSignature(tuple(bits))

    @property
    def all_satisfied(self) -> bool:
        """True if all constraints are satisfied."""
        return all(self.bits)

    @property
    def none_satisfied(self) -> bool:
        """True if no constraints are satisfied."""
        return not any(self.bits)


@dataclass
class ConstraintInfo:
    """Information about a single constraint in the hierarchy.

    The hierarchy represents forward progression:
    - prerequisite_groups: list of alternative prerequisite sets (OR of ANDs)
      Each group is a set of constraint indices that must ALL be satisfied
      At least ONE group must be satisfied
    - prerequisite_indices: flattened union of all groups (for backward compat)
    - dependent_indices: constraints that require THIS to be satisfied first

    Example for testgame:
    - key_held has no prerequisites (can be achieved immediately)
    - door_unlocked has TWO groups: [key_held] OR [lockpick_held, lockpick_not_broken]
    - door_open has door_unlocked as prerequisite (must unlock before open)
    - player_at_outside has door_open as prerequisite
    """
    index: int  # Position in the signature bit vector
    name: str  # Human-readable name
    constraint: Constraint  # The actual constraint
    depth: int  # Depth from victory (0 = victory condition, higher = earlier in progression)
    prerequisite_groups: list[list[int]] = field(default_factory=list)  # OR of AND groups
    prerequisite_indices: list[int] = field(default_factory=list)  # Flattened (for backward compat)
    dependent_indices: list[int] = field(default_factory=list)  # These require THIS first


@dataclass
class ConstraintHierarchy:
    """
    The hierarchical structure of constraints derived from backward analysis.

    This is built once from the game definition (no state exploration needed)
    and provides:
    - Ordered list of constraints for signature construction
    - Parent-child relationships (what must be achieved before what)
    - Constraint names for human-readable output
    """
    constraints: list[ConstraintInfo]

    # Maps constraint to its index
    _constraint_to_index: dict[Constraint, int] = field(default_factory=dict)

    # The constraint trees from backward analysis
    trees: list[ConstraintTree] = field(default_factory=list)

    def __post_init__(self):
        self._constraint_to_index = {c.constraint: c.index for c in self.constraints}

    def get_signature(self, state_values: dict[str, Any]) -> ClusterSignature:
        """Compute the cluster signature for a state."""
        bits = []
        for info in self.constraints:
            ref_str = str(info.constraint.ref)
            current_value = state_values.get(ref_str)
            bits.append(info.constraint.is_satisfied(current_value))
        return ClusterSignature(tuple(bits))

    def signature_to_description(self, sig: ClusterSignature) -> str:
        """Convert signature to human-readable description."""
        satisfied = [
            self.constraints[i].name
            for i in sig.satisfied_indices()
        ]
        if not satisfied:
            return "(no progress)"
        return ", ".join(satisfied)

    def get_expected_predecessors(self, sig: ClusterSignature) -> set[ClusterSignature]:
        """
        Get signatures that could validly precede this one.

        Based on the constraint hierarchy, we expect certain orderings.
        A signature with constraint C satisfied should have predecessors
        where either C or one of C's preconditions was just satisfied.
        """
        predecessors: set[ClusterSignature] = set()

        for i in sig.satisfied_indices():
            # Could have just satisfied constraint i
            pred = sig.with_bit(i, False)
            predecessors.add(pred)

            # Or could have satisfied i by first satisfying a prerequisite
            for prereq_idx in self.constraints[i].prerequisite_indices:
                if sig.bits[prereq_idx]:
                    # Prerequisite is also satisfied - could be part of the chain
                    pass  # This gets more complex with DAG structure

        return predecessors



@dataclass
class Cluster:
    """A cluster of states sharing the same constraint signature."""
    signature: ClusterSignature
    description: str
    state_ids: list[int] = field(default_factory=list)
    is_victory: bool = False
    is_defeat: bool = False

    @property
    def size(self) -> int:
        return len(self.state_ids)


@dataclass
class ClusterTransition:
    """A transition between clusters (puzzle-advancing action)."""
    from_sig: ClusterSignature
    to_sig: ClusterSignature
    actions: list[str] = field(default_factory=list)  # Actions that cause this transition

    @property
    def bits_flipped(self) -> list[int]:
        """Which constraint bits changed in this transition."""
        return [
            i for i, (a, b) in enumerate(zip(self.from_sig.bits, self.to_sig.bits))
            if a != b
        ]


@dataclass
class ClusterGraph:
    """
    The clustered view of the state space.

    This is a compressed representation where:
    - Nodes are clusters (equivalence classes of states)
    - Edges are inter-cluster transitions (puzzle-advancing actions)
    - Intra-cluster transitions are summarized but not enumerated
    """
    clusters: dict[ClusterSignature, Cluster] = field(default_factory=dict)
    transitions: list[ClusterTransition] = field(default_factory=list)
    hierarchy: ConstraintHierarchy | None = None

    # Statistics
    total_states: int = 0
    total_edges: int = 0
    intra_cluster_edges: int = 0

    def compression_ratio(self) -> float:
        """How much compression we achieved."""
        if not self.clusters:
            return 1.0
        return self.total_states / len(self.clusters)

    def get_victory_clusters(self) -> list[Cluster]:
        """Clusters containing victory states."""
        return [c for c in self.clusters.values() if c.is_victory]


    def get_progression_path(self) -> list[ClusterSignature]:
        """
        Find the expected progression from initial to victory.

        This follows the constraint hierarchy to show the intended
        puzzle sequence.
        """
        if not self.hierarchy:
            return []

        # Start with all-false (no progress)
        path = [ClusterSignature(tuple(False for _ in self.hierarchy.constraints))]

        # Build path by satisfying constraints in dependency order
        # (simplified - a full implementation would topologically sort)
        current = path[0]
        while not current.all_satisfied:
            # Find a constraint we can satisfy (all prerequisites satisfied)
            for i, info in enumerate(self.hierarchy.constraints):
                if not current.bits[i]:  # Not yet satisfied
                    # Check prerequisites
                    prereqs_satisfied = all(
                        current.bits[p] for p in info.prerequisite_indices
                    )
                    if prereqs_satisfied:
                        current = current.with_bit(i, True)
                        path.append(current)
                        break
            else:
                # No progress possible - break to avoid infinite loop
                break

        return path


def build_hierarchy(
    world: GrueWorld,
    effects: EffectAnalysis,
    relevance: RelevanceAnalysis,
) -> ConstraintHierarchy:
    """
    Build a constraint hierarchy from the game definition.

    This works entirely from static analysis - no state exploration needed.

    The backward constraint tree has:
    - Root = victory condition (player_at_outside)
    - Achievers = alternative ways to achieve a constraint (OR relationship)
    - Each achiever has preconditions (AND relationship)

    We convert this to forward progression with OR-of-ANDs:
    - prerequisite_groups = list of achiever precondition sets (any one suffices)
    - prerequisite_indices = flattened union (for backward compat)
    - dependent_indices = parent in backward tree (what needs this)
    """
    # Get constraint trees from backward analysis
    trees = build_victory_constraints(world, effects, relevance)

    # Collect all unique constraints and their achiever groups
    all_constraints: dict[Constraint, ConstraintInfo] = {}
    # achiever_groups[X] = list of (set of constraints) - each set is an alternative path
    achiever_groups: dict[Constraint, list[set[Constraint]]] = defaultdict(list)

    def walk_tree(node: ConstraintNode, depth: int, visited: set[Constraint]):
        if node.constraint in visited:
            return
        visited.add(node.constraint)

        # Record this constraint
        if node.constraint not in all_constraints:
            all_constraints[node.constraint] = ConstraintInfo(
                index=-1,  # Assigned later
                name=_constraint_name(node.constraint),
                constraint=node.constraint,
                depth=depth,
            )
        else:
            # Update depth to minimum seen
            all_constraints[node.constraint].depth = min(
                all_constraints[node.constraint].depth, depth
            )

        # Record achiever groups (OR relationship between achievers)
        # Each achiever's preconditions form an AND group
        for achiever in node.achievers:
            group: set[Constraint] = set()
            for precond in achiever.preconditions:
                group.add(precond)
            if group:  # Only add non-empty groups
                achiever_groups[node.constraint].append(group)

        # Recurse into children (all preconditions from all achievers)
        for child in node.children.values():
            walk_tree(child, depth + 1, visited)

    for tree in trees:
        walk_tree(tree.root, 0, set())

    # Sort constraints by depth (victory first, then its prereqs, etc.)
    sorted_constraints = sorted(
        all_constraints.values(),
        key=lambda c: (c.depth, str(c.constraint))
    )

    # Assign indices
    constraint_to_idx = {c.constraint: i for i, c in enumerate(sorted_constraints)}

    # Set up prerequisite groups and relationships
    for i, info in enumerate(sorted_constraints):
        info.index = i

        # Convert achiever groups to index groups
        groups = achiever_groups.get(info.constraint, [])
        for group in groups:
            idx_group = []
            for prereq_constraint in group:
                prereq_idx = constraint_to_idx.get(prereq_constraint)
                if prereq_idx is not None:
                    idx_group.append(prereq_idx)
            if idx_group:
                info.prerequisite_groups.append(idx_group)
                # Also add to flat list for backward compat
                for idx in idx_group:
                    if idx not in info.prerequisite_indices:
                        info.prerequisite_indices.append(idx)

        # Dependents = find all constraints that have this in any achiever group
        for other_constraint, other_groups in achiever_groups.items():
            for other_group in other_groups:
                if info.constraint in other_group:
                    other_idx = constraint_to_idx.get(other_constraint)
                    if other_idx is not None and other_idx not in info.dependent_indices:
                        info.dependent_indices.append(other_idx)

    return ConstraintHierarchy(
        constraints=sorted_constraints,
        trees=trees,
    )


def _constraint_name(constraint: Constraint) -> str:
    """Generate a human-readable name for a constraint."""
    ref = constraint.ref

    if isinstance(ref, LocationRef):
        obj = ref.object.replace("@", "")
        if constraint.value == "@player":
            return f"{obj}_held"
        else:
            loc = str(constraint.value).replace("@", "")
            return f"{obj}_at_{loc}"

    if isinstance(ref, PropertyRef):
        obj = ref.object.replace("@", "")
        prop = ref.property
        val = constraint.value

        if isinstance(val, bool):
            if val:
                return f"{obj}_{prop}"
            else:
                return f"{obj}_not_{prop}"
        else:
            return f"{obj}_{prop}_{val}"

    return str(constraint)


def cluster_state_graph(
    graph: StateGraph,
    hierarchy: ConstraintHierarchy,
) -> ClusterGraph:
    """
    Cluster an explored state graph using the constraint hierarchy.

    This is the "bottom-up" approach - we already have states and
    just need to classify them.
    """
    result = ClusterGraph(hierarchy=hierarchy)
    result.total_states = len(graph.nodes)
    result.total_edges = len(graph.edges)

    # Classify each state into a cluster
    state_to_sig: dict[int, ClusterSignature] = {}

    for node_id, node in graph.nodes.items():
        state_values = dict(node.state.values)
        sig = hierarchy.get_signature(state_values)
        state_to_sig[node_id] = sig

        # Create or update cluster
        if sig not in result.clusters:
            result.clusters[sig] = Cluster(
                signature=sig,
                description=hierarchy.signature_to_description(sig),
            )

        cluster = result.clusters[sig]
        cluster.state_ids.append(node_id)

        if node.is_victory:
            cluster.is_victory = True
        if node.is_defeat:
            cluster.is_defeat = True

    # Classify edges as inter-cluster or intra-cluster
    inter_transitions: dict[tuple[ClusterSignature, ClusterSignature], list[str]] = defaultdict(list)

    for edge in graph.edges:
        from_sig = state_to_sig[edge.from_id]
        to_sig = state_to_sig[edge.to_id]

        action_str = f"{edge.action.verb} {edge.action.target}"

        if from_sig == to_sig:
            result.intra_cluster_edges += 1
        else:
            inter_transitions[(from_sig, to_sig)].append(action_str)

    # Deduplicate inter-cluster transitions
    for (from_sig, to_sig), actions in inter_transitions.items():
        result.transitions.append(ClusterTransition(
            from_sig=from_sig,
            to_sig=to_sig,
            actions=sorted(set(actions)),
        ))

    return result


def print_cluster_report(cluster_graph: ClusterGraph) -> str:
    """Generate a human-readable clustering report."""
    lines = []

    lines.append("=" * 70)
    lines.append("CONSTRAINT-BASED CLUSTERING REPORT")
    lines.append("=" * 70)
    lines.append("")

    # Overview
    lines.append("OVERVIEW")
    lines.append("-" * 70)
    lines.append(f"Total states:        {cluster_graph.total_states}")
    lines.append(f"Total transitions:   {cluster_graph.total_edges}")
    lines.append(f"Clusters:            {len(cluster_graph.clusters)}")
    lines.append(f"Compression ratio:   {cluster_graph.compression_ratio():.1f}x")
    lines.append(f"Inter-cluster edges: {len(cluster_graph.transitions)}")
    lines.append(f"Intra-cluster edges: {cluster_graph.intra_cluster_edges}")
    lines.append("")

    # Constraints
    if cluster_graph.hierarchy:
        lines.append("CONSTRAINT HIERARCHY")
        lines.append("-" * 70)
        for info in cluster_graph.hierarchy.constraints:
            prereqs = ""
            if info.prerequisite_indices:
                prereq_names = [
                    cluster_graph.hierarchy.constraints[p].name
                    for p in info.prerequisite_indices
                ]
                prereqs = f" (requires: {', '.join(prereq_names)})"
            lines.append(f"  [{info.index}] {info.name}: {info.constraint}{prereqs}")
        lines.append("")

    # Clusters
    lines.append("CLUSTERS")
    lines.append("-" * 70)
    lines.append(f"{'Signature':<12} {'States':<8} {'V':<4} {'D':<4} {'Description'}")
    lines.append("-" * 70)

    for sig in sorted(cluster_graph.clusters.keys(), key=str):
        cluster = cluster_graph.clusters[sig]
        v = "✓" if cluster.is_victory else ""
        d = "✗" if cluster.is_defeat else ""
        desc = cluster.description
        lines.append(f"{str(sig):<12} {cluster.size:<8} {v:<4} {d:<4} {desc}")

    lines.append("")

    # Inter-cluster transitions
    lines.append("INTER-CLUSTER TRANSITIONS")
    lines.append("-" * 70)
    for trans in sorted(cluster_graph.transitions, key=lambda t: (str(t.from_sig), str(t.to_sig))):
        actions = ", ".join(trans.actions)
        lines.append(f"  {trans.from_sig} -> {trans.to_sig}: {actions}")

    lines.append("")

    # Expected progression
    if cluster_graph.hierarchy:
        lines.append("EXPECTED PROGRESSION")
        lines.append("-" * 70)
        path = cluster_graph.get_progression_path()
        for i, sig in enumerate(path):
            desc = cluster_graph.hierarchy.signature_to_description(sig)
            exists = "✓" if sig in cluster_graph.clusters else "?"
            lines.append(f"  {i}. {sig} {exists} {desc}")

    return "\n".join(lines)


def generate_cluster_dot(cluster_graph: ClusterGraph, rankdir: str = "LR") -> str:
    """Generate DOT format graph of clusters.

    Args:
        cluster_graph: The cluster graph to render
        rankdir: Graph direction - "LR" (left-right) or "TB" (top-bottom)
    """
    lines = ["digraph clusters {", f"  rankdir={rankdir};", "  node [shape=box fontsize=10];", ""]

    # Nodes
    for sig, cluster in cluster_graph.clusters.items():
        # Format description vertically (one constraint per line)
        desc_parts = cluster.description.split(", ")
        if desc_parts and desc_parts[0]:
            desc_vertical = "\\n".join(desc_parts)
        else:
            desc_vertical = "(no progress)"

        # Add state count
        label = f"{sig}\\n{desc_vertical}\\n({cluster.size} states)"

        if cluster.is_victory:
            style = 'style=filled fillcolor=green'
        elif cluster.is_defeat:
            style = 'style=filled fillcolor=red'
        else:
            style = 'style=filled fillcolor=lightblue'

        # Escape quotes in label
        label = label.replace('"', '\\"')
        lines.append(f'  c{sig} [label="{label}" {style}];')

    lines.append("")

    # Edges
    for trans in cluster_graph.transitions:
        label = trans.actions[0] if len(trans.actions) == 1 else f"{len(trans.actions)} actions"
        label = label.replace('"', '\\"')
        lines.append(f'  c{trans.from_sig} -> c{trans.to_sig} [label="{label}"];')

    lines.append("}")
    return "\n".join(lines)
