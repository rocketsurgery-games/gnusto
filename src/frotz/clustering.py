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
    build_defeat_constraints,
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
    initial_sig: ClusterSignature | None = None  # Signature of the initial state's cluster
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


@dataclass
class Region:
    """
    A strongly connected component in the cluster graph.

    Regions represent sets of clusters where the player can freely move
    between any two clusters (possibly through intermediate steps).
    """
    id: int
    clusters: list[ClusterSignature]

    # Computed properties
    has_victory: bool = False
    has_defeat: bool = False
    is_terminal: bool = False  # True if this is a singleton victory/defeat

    @property
    def size(self) -> int:
        return len(self.clusters)

    def description(self, hierarchy: ConstraintHierarchy | None) -> str:
        """Generate a human-readable description of what defines this region."""
        if not self.clusters:
            return "(empty)"

        # Find bits that are the same across all clusters in the region
        first = self.clusters[0]
        common_true = set(first.satisfied_indices())
        common_false = set(first.unsatisfied_indices())

        for sig in self.clusters[1:]:
            common_true &= set(sig.satisfied_indices())
            common_false &= set(sig.unsatisfied_indices())

        if hierarchy:
            parts = []
            for i in sorted(common_true):
                parts.append(hierarchy.constraints[i].name)
            for i in sorted(common_false):
                parts.append(f"!{hierarchy.constraints[i].name}")
            return ", ".join(parts) if parts else "(no common constraints)"
        else:
            return f"common_true={common_true}, common_false={common_false}"


@dataclass
class RegionTransition:
    """A transition between regions."""
    from_region: int
    to_region: int
    actions: list[str]  # Actions that cause this transition
    cluster_transitions: list[tuple[ClusterSignature, ClusterSignature]]  # The actual cluster-level transitions

    def compute_context(
        self,
        source_region: "Region",
        hierarchy: "ConstraintHierarchy | None",
    ) -> tuple[list[str], list[str]]:
        """
        Compute the preconditions and effects for this transition.

        Returns:
            (preconditions, effects) where:
            - preconditions: constraint names that had to be satisfied BEFORE
              this action, beyond what the source region guarantees
            - effects: constraint changes caused by this transition (the
              irreversible state change that creates the region boundary)
        """
        if not self.cluster_transitions:
            return [], []

        # Get the source region's "base" - bits that are always true/false in the region
        region_common_true = set(source_region.clusters[0].satisfied_indices())
        region_common_false = set(source_region.clusters[0].unsatisfied_indices())
        for sig in source_region.clusters[1:]:
            region_common_true &= set(sig.satisfied_indices())
            region_common_false &= set(sig.unsatisfied_indices())

        # Find bits that are ALWAYS true in from_sigs (preconditions)
        # These are what the player "achieved" before taking the boundary action
        from_sigs = [t[0] for t in self.cluster_transitions]
        precondition_bits = set(from_sigs[0].satisfied_indices())
        for sig in from_sigs[1:]:
            precondition_bits &= set(sig.satisfied_indices())

        # Preconditions = bits required by from_sig but NOT guaranteed by region
        # (i.e., things that had to be achieved within the region first)
        extra_preconditions = precondition_bits - region_common_true

        # Find bits that CHANGE consistently across all transitions (effects)
        # These are the irreversible changes that create the region boundary
        to_sigs = [t[1] for t in self.cluster_transitions]

        # Check each bit for consistent changes
        effect_bits_0_to_1: set[int] = set()  # bits that go 0->1
        effect_bits_1_to_0: set[int] = set()  # bits that go 1->0

        n_bits = len(from_sigs[0].bits)
        for i in range(n_bits):
            from_vals = [sig.bits[i] for sig in from_sigs]
            to_vals = [sig.bits[i] for sig in to_sigs]

            # Only count as effect if ALL transitions show the same change
            if all(not f and t for f, t in zip(from_vals, to_vals)):
                effect_bits_0_to_1.add(i)
            elif all(f and not t for f, t in zip(from_vals, to_vals)):
                effect_bits_1_to_0.add(i)

        # Convert to names
        if hierarchy:
            precondition_names = [
                hierarchy.constraints[i].name for i in sorted(extra_preconditions)
            ]
            effect_names = []
            for i in sorted(effect_bits_0_to_1):
                effect_names.append(f"+{hierarchy.constraints[i].name}")
            for i in sorted(effect_bits_1_to_0):
                effect_names.append(f"-{hierarchy.constraints[i].name}")
        else:
            precondition_names = [f"bit{i}" for i in sorted(extra_preconditions)]
            effect_names = []
            for i in sorted(effect_bits_0_to_1):
                effect_names.append(f"+bit{i}")
            for i in sorted(effect_bits_1_to_0):
                effect_names.append(f"-bit{i}")

        return precondition_names, effect_names


@dataclass
class RegionGraph:
    """
    The region-level view of the game structure.

    This is the "meta-graph" where:
    - Nodes are regions (SCCs of the cluster graph)
    - Edges are one-way transitions between regions
    """
    regions: dict[int, Region]
    transitions: list[RegionTransition]
    initial_region: int | None = None
    hierarchy: ConstraintHierarchy | None = None

    # Map from cluster signature to region ID
    cluster_to_region: dict[ClusterSignature, int] = field(default_factory=dict)


def compute_regions(cluster_graph: ClusterGraph) -> RegionGraph:
    """
    Compute strongly connected components of the cluster graph.

    Each SCC becomes a "region" - a set of clusters the player can
    freely explore without making irreversible progress.
    """
    # Build directed adjacency
    successors: dict[ClusterSignature, set[ClusterSignature]] = {
        sig: set() for sig in cluster_graph.clusters
    }
    predecessors: dict[ClusterSignature, set[ClusterSignature]] = {
        sig: set() for sig in cluster_graph.clusters
    }

    # Also track actions for each transition
    transition_actions: dict[tuple[ClusterSignature, ClusterSignature], list[str]] = {}

    for trans in cluster_graph.transitions:
        successors[trans.from_sig].add(trans.to_sig)
        predecessors[trans.to_sig].add(trans.from_sig)
        transition_actions[(trans.from_sig, trans.to_sig)] = trans.actions

    # Kosaraju's algorithm for SCCs
    def dfs_forward(node: ClusterSignature, visited: set, stack: list):
        visited.add(node)
        for succ in successors[node]:
            if succ not in visited:
                dfs_forward(succ, visited, stack)
        stack.append(node)

    def dfs_backward(node: ClusterSignature, visited: set, component: list):
        visited.add(node)
        component.append(node)
        for pred in predecessors[node]:
            if pred not in visited:
                dfs_backward(pred, visited, component)

    # First pass: get finish order
    visited: set[ClusterSignature] = set()
    stack: list[ClusterSignature] = []
    for node in cluster_graph.clusters:
        if node not in visited:
            dfs_forward(node, visited, stack)

    # Second pass: find SCCs in reverse finish order
    visited = set()
    sccs: list[list[ClusterSignature]] = []
    while stack:
        node = stack.pop()
        if node not in visited:
            component: list[ClusterSignature] = []
            dfs_backward(node, visited, component)
            sccs.append(component)

    # Build regions
    regions: dict[int, Region] = {}
    cluster_to_region: dict[ClusterSignature, int] = {}

    for i, scc in enumerate(sccs):
        has_victory = any(cluster_graph.clusters[sig].is_victory for sig in scc)
        has_defeat = any(cluster_graph.clusters[sig].is_defeat for sig in scc)
        is_terminal = len(scc) == 1 and (has_victory or has_defeat)

        region = Region(
            id=i,
            clusters=scc,
            has_victory=has_victory,
            has_defeat=has_defeat,
            is_terminal=is_terminal,
        )
        regions[i] = region

        for sig in scc:
            cluster_to_region[sig] = i

    # Find initial region
    initial_region = None
    if cluster_graph.initial_sig is not None:
        initial_region = cluster_to_region.get(cluster_graph.initial_sig)

    # Build region transitions
    region_transitions: dict[tuple[int, int], RegionTransition] = {}

    for trans in cluster_graph.transitions:
        from_region = cluster_to_region[trans.from_sig]
        to_region = cluster_to_region[trans.to_sig]

        if from_region != to_region:
            key = (from_region, to_region)
            if key not in region_transitions:
                region_transitions[key] = RegionTransition(
                    from_region=from_region,
                    to_region=to_region,
                    actions=[],
                    cluster_transitions=[],
                )
            rt = region_transitions[key]
            rt.cluster_transitions.append((trans.from_sig, trans.to_sig))
            for action in trans.actions:
                if action not in rt.actions:
                    rt.actions.append(action)

    return RegionGraph(
        regions=regions,
        transitions=list(region_transitions.values()),
        initial_region=initial_region,
        hierarchy=cluster_graph.hierarchy,
        cluster_to_region=cluster_to_region,
    )


def _merge_signatures(sigs: list[ClusterSignature]) -> str:
    """
    Merge multiple signatures, showing ? for bits that differ.

    Example: [1010, 1011, 1000] -> "10??"
    """
    if not sigs:
        return ""
    if len(sigs) == 1:
        return str(sigs[0])

    n_bits = len(sigs[0].bits)
    result = []
    for i in range(n_bits):
        values = set(sig.bits[i] for sig in sigs)
        if len(values) == 1:
            result.append("1" if values.pop() else "0")
        else:
            result.append("?")
    return "".join(result)


def _build_edge_label(
    trans: RegionTransition,
    source_region: Region,
    hierarchy: ConstraintHierarchy | None,
) -> str:
    """
    Build a descriptive edge label showing actions, preconditions, and effects.

    Format:
        action_name
        [after: precondition1, precondition2]
        [→ +effect1, -effect2]
    """
    # Base action label
    if len(trans.actions) == 1:
        action_label = trans.actions[0].replace("@", "")
    elif len(trans.actions) <= 3:
        action_label = "\\n".join(a.replace("@", "") for a in trans.actions[:3])
    else:
        action_label = f"{len(trans.actions)} actions"

    # Get preconditions and effects
    preconditions, effects = trans.compute_context(source_region, hierarchy)

    # Build label parts
    parts = [action_label]

    if preconditions:
        # Simplify constraint names for display
        short_preconds = [_shorten_constraint_name(p) for p in preconditions]
        if len(short_preconds) <= 2:
            parts.append(f"[after: {', '.join(short_preconds)}]")
        else:
            parts.append(f"[after: {len(short_preconds)} steps]")

    if effects:
        # Effects already have +/- prefix
        short_effects = [_shorten_constraint_name(e) for e in effects]
        parts.append(f"[→ {', '.join(short_effects)}]")

    label = "\\n".join(parts)
    return label.replace('"', '\\"')


def _shorten_constraint_name(name: str) -> str:
    """
    Shorten a constraint name for edge labels.

    Removes common suffixes and the leading + or - if present.
    """
    # Preserve the +/- prefix
    prefix = ""
    if name.startswith("+") or name.startswith("-"):
        prefix = name[0]
        name = name[1:]

    # Common suffixes to remove for brevity
    for suffix in ["_not_broken", "_not_locked", "_bribed"]:
        if name.endswith(suffix):
            # Keep the semantic: "lockpick_not_broken" -> "lockpick ok"
            base = name[: -len(suffix)]
            if suffix == "_not_broken":
                return prefix + base + " ok"
            elif suffix == "_not_locked":
                return prefix + base + " unlocked"
            elif suffix == "_bribed":
                return prefix + base + " bribed"

    # Try to shorten object_property to just property if unambiguous
    if "_" in name:
        parts = name.split("_")
        # Keep last part if it's meaningful
        if parts[-1] in ["open", "held", "dead", "bribed", "locked", "broken"]:
            return prefix + "_".join(parts[-2:]) if len(parts) > 1 else prefix + name

    return prefix + name


def generate_region_dot(
    region_graph: RegionGraph,
    cluster_graph: ClusterGraph,
    collapse_terminals: bool = True,
) -> str:
    """
    Generate DOT format of the region meta-graph.

    This shows the high-level structure:
    - Large nodes for multi-cluster regions (freely explorable)
    - Small nodes for terminal states (victory/defeat)
    - Edges labeled with actions that cross region boundaries

    If collapse_terminals is True, terminal states (victories/defeats) are
    grouped by their source region, showing merged signatures with ? for
    bits that vary.
    """
    lines = ["digraph regions {", "  rankdir=TB;", "  node [shape=box fontsize=11];", ""]

    if collapse_terminals:
        # Group terminal regions by (source_region, is_victory)
        # Find which non-terminal region each terminal is reached from
        terminal_groups: dict[tuple[int, bool], list[Region]] = {}

        for trans in region_graph.transitions:
            to_region = region_graph.regions[trans.to_region]
            from_region = region_graph.regions[trans.from_region]

            if to_region.is_terminal and not from_region.is_terminal:
                key = (trans.from_region, to_region.has_victory)
                if key not in terminal_groups:
                    terminal_groups[key] = []
                if to_region not in terminal_groups[key]:
                    terminal_groups[key].append(to_region)

        # Track which terminal regions we've grouped
        grouped_terminals: set[int] = set()
        for regions_list in terminal_groups.values():
            for r in regions_list:
                grouped_terminals.add(r.id)

        # Emit non-terminal regions
        for region_id, region in region_graph.regions.items():
            if region.is_terminal:
                continue

            desc = region.description(region_graph.hierarchy)
            label_parts = [f"Region {region_id}", f"({region.size} clusters)", desc]
            label = "\\n".join(label_parts)

            if region_id == region_graph.initial_region:
                style = 'style="filled,bold" fillcolor=yellow penwidth=3'
            else:
                style = 'style=filled fillcolor=lightblue'

            label = label.replace('"', '\\"')
            lines.append(f'  r{region_id} [label="{label}" {style}];')

        lines.append("")

        # Emit collapsed terminal groups
        for (source_id, is_victory), regions_list in terminal_groups.items():
            all_sigs = [r.clusters[0] for r in regions_list]
            merged_sig = _merge_signatures(all_sigs)
            count = len(regions_list)

            group_id = f"t{source_id}_{'v' if is_victory else 'd'}"

            if is_victory:
                label = f"VICTORY ({count})\\n{merged_sig}"
                style = 'style=filled fillcolor=green shape=ellipse'
            else:
                label = f"DEFEAT ({count})\\n{merged_sig}"
                style = 'style=filled fillcolor=red shape=ellipse'

            lines.append(f'  {group_id} [label="{label}" {style}];')

        lines.append("")

        # Emit edges - collapse edges to terminal groups
        # For terminal edges, just collect action names (no context - there are too many variations)
        # For region-to-region edges, show full context
        terminal_edge_actions: dict[tuple[str, str], set[str]] = {}
        emitted_edges: set[tuple[str, str]] = set()

        for trans in region_graph.transitions:
            from_region = region_graph.regions[trans.from_region]
            to_region = region_graph.regions[trans.to_region]

            # Determine node IDs
            if from_region.is_terminal:
                continue  # Skip edges from terminals
            from_id = f"r{trans.from_region}"

            if to_region.is_terminal:
                # Point to collapsed group - collect actions without context
                to_id = f"t{trans.from_region}_{'v' if to_region.has_victory else 'd'}"
                key = (from_id, to_id)
                if key not in terminal_edge_actions:
                    terminal_edge_actions[key] = set()
                for action in trans.actions:
                    terminal_edge_actions[key].add(action.replace("@", ""))
            else:
                # Region-to-region edge - show full context
                to_id = f"r{trans.to_region}"
                edge_key = (from_id, to_id)
                if edge_key not in emitted_edges:
                    label = _build_edge_label(trans, from_region, region_graph.hierarchy)
                    lines.append(f'  {from_id} -> {to_id} [label="{label}"];')
                    emitted_edges.add(edge_key)

        # Emit collapsed terminal edges
        for (from_id, to_id), actions in terminal_edge_actions.items():
            if len(actions) <= 3:
                label = "\\n".join(sorted(actions))
            else:
                label = f"{len(actions)} actions"
            label = label.replace('"', '\\"')
            lines.append(f'  {from_id} -> {to_id} [label="{label}"];')

    else:
        # Original behavior - show all terminals individually
        for region_id, region in region_graph.regions.items():
            desc = region.description(region_graph.hierarchy)

            if region.is_terminal:
                if region.has_victory:
                    sig = region.clusters[0]
                    label = f"VICTORY\\n{sig}"
                    style = 'style=filled fillcolor=green shape=ellipse'
                else:
                    sig = region.clusters[0]
                    label = f"DEFEAT\\n{sig}"
                    style = 'style=filled fillcolor=red shape=ellipse'
            else:
                label_parts = [f"Region {region_id}", f"({region.size} clusters)", desc]
                label = "\\n".join(label_parts)

                if region_id == region_graph.initial_region:
                    style = 'style="filled,bold" fillcolor=yellow penwidth=3'
                else:
                    style = 'style=filled fillcolor=lightblue'

            label = label.replace('"', '\\"')
            lines.append(f'  r{region_id} [label="{label}" {style}];')

        lines.append("")

        for trans in region_graph.transitions:
            from_region = region_graph.regions[trans.from_region]
            label = _build_edge_label(trans, from_region, region_graph.hierarchy)
            lines.append(f'  r{trans.from_region} -> r{trans.to_region} [label="{label}"];')

    lines.append("}")
    return "\n".join(lines)


def build_hierarchy(
    world: GrueWorld,
    effects: EffectAnalysis,
    relevance: RelevanceAnalysis,
    include_defeat: bool = True,
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

    If include_defeat is True, defeat constraints are also included in the hierarchy.
    """
    # Get constraint trees from backward analysis
    trees = build_victory_constraints(world, effects, relevance)

    # Also include defeat constraints if requested
    if include_defeat:
        defeat_trees = build_defeat_constraints(world, effects, relevance)
        trees.extend(defeat_trees)

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

    # Track initial state's cluster
    if graph.initial_id is not None:
        initial_node = graph.nodes[graph.initial_id]
        initial_values = dict(initial_node.state.values)
        result.initial_sig = hierarchy.get_signature(initial_values)

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


@dataclass
class DominatorTree:
    """
    Dominator tree for a cluster graph.

    A node D dominates node N if every path from START to N goes through D.
    The dominator tree reveals the mandatory progression structure:
    - Root = START (dominates all reachable nodes)
    - Children = nodes whose immediate dominator is the parent
    - Depth in tree = how many mandatory waypoints to reach this cluster

    Key insights this provides:
    - Nodes with many descendants are "major checkpoints"
    - Siblings in the tree are "parallel alternatives"
    - Leaf nodes are "end states" or "optional variations"
    """
    # Immediate dominator for each node (idom[n] = closest dominator of n)
    idom: dict[ClusterSignature, ClusterSignature | None]

    # Children in the dominator tree
    children: dict[ClusterSignature, list[ClusterSignature]]

    # Depth from root in dominator tree
    depth: dict[ClusterSignature, int]

    # The root (START cluster)
    root: ClusterSignature | None

    # Nodes not reachable from START (unreachable clusters)
    unreachable: set[ClusterSignature]

    def get_descendants(self, sig: ClusterSignature) -> set[ClusterSignature]:
        """Get all nodes dominated by sig (including indirect)."""
        result: set[ClusterSignature] = set()
        stack = list(self.children.get(sig, []))
        while stack:
            node = stack.pop()
            result.add(node)
            stack.extend(self.children.get(node, []))
        return result

    def is_mandatory(self, sig: ClusterSignature, victory_sigs: set[ClusterSignature]) -> bool:
        """Check if this cluster is on ALL paths to victory."""
        # A cluster is mandatory if it dominates at least one victory cluster
        descendants = self.get_descendants(sig)
        return bool(descendants & victory_sigs) or sig in victory_sigs

    def get_mandatory_path(self, victory_sig: ClusterSignature) -> list[ClusterSignature]:
        """Get the chain of mandatory clusters from START to a victory cluster."""
        path = []
        current: ClusterSignature | None = victory_sig
        while current is not None:
            path.append(current)
            current = self.idom.get(current)
        path.reverse()
        return path


def compute_dominators(cluster_graph: ClusterGraph) -> DominatorTree:
    """
    Compute the dominator tree for a cluster graph.

    Uses the iterative dataflow algorithm (simple and correct for small graphs).
    For each node N, find the intersection of dominators of all predecessors,
    then add N itself.
    """
    if cluster_graph.initial_sig is None:
        return DominatorTree(
            idom={},
            children={},
            depth={},
            root=None,
            unreachable=set(cluster_graph.clusters.keys()),
        )

    start = cluster_graph.initial_sig
    all_nodes = set(cluster_graph.clusters.keys())

    # Build predecessor map
    predecessors: dict[ClusterSignature, set[ClusterSignature]] = {
        sig: set() for sig in all_nodes
    }
    successors: dict[ClusterSignature, set[ClusterSignature]] = {
        sig: set() for sig in all_nodes
    }
    for trans in cluster_graph.transitions:
        predecessors[trans.to_sig].add(trans.from_sig)
        successors[trans.from_sig].add(trans.to_sig)

    # Initialize dominators: start dominates only itself, others dominated by all
    dom: dict[ClusterSignature, set[ClusterSignature]] = {}
    dom[start] = {start}
    for sig in all_nodes:
        if sig != start:
            dom[sig] = all_nodes.copy()

    # Iterative refinement (excluding start)
    changed = True
    iterations = 0
    while changed and iterations < 1000:
        changed = False
        iterations += 1
        for sig in all_nodes:
            if sig == start:
                continue
            preds = predecessors[sig]
            if not preds:
                # No predecessors - unreachable from start
                continue
            # New dom = intersection of all predecessors' dominators, plus self
            new_dom = all_nodes.copy()
            for pred in preds:
                new_dom &= dom[pred]
            new_dom.add(sig)
            if new_dom != dom[sig]:
                dom[sig] = new_dom
                changed = True

    # Find unreachable nodes (still dominated by all nodes)
    unreachable = {sig for sig in all_nodes if dom[sig] == all_nodes and sig != start}

    # Extract immediate dominators from dominator sets
    idom: dict[ClusterSignature, ClusterSignature | None] = {start: None}
    for sig in all_nodes:
        if sig == start or sig in unreachable:
            continue
        # idom is the dominator closest to sig (largest dom set excluding sig)
        dominators = dom[sig] - {sig}
        if not dominators:
            idom[sig] = None
            continue
        # idom has the largest dominator set among dominators
        idom[sig] = max(dominators, key=lambda d: len(dom[d]))

    # Build children map
    children: dict[ClusterSignature, list[ClusterSignature]] = {sig: [] for sig in all_nodes}
    for sig, parent in idom.items():
        if parent is not None:
            children[parent].append(sig)

    # Sort children for deterministic output
    for sig in children:
        children[sig].sort(key=str)

    # Compute depths
    depth: dict[ClusterSignature, int] = {start: 0}
    stack = [(start, 0)]
    while stack:
        node, d = stack.pop()
        for child in children[node]:
            depth[child] = d + 1
            stack.append((child, d + 1))

    return DominatorTree(
        idom=idom,
        children=children,
        depth=depth,
        root=start,
        unreachable=unreachable,
    )


def generate_dominator_dot(
    cluster_graph: ClusterGraph,
    dom_tree: DominatorTree,
    rankdir: str = "TB",
) -> str:
    """
    Generate DOT format of the dominator tree.

    This shows the mandatory progression structure:
    - Vertical depth = number of mandatory steps
    - Siblings = parallel alternatives
    - Node size/color based on how many clusters it dominates
    """
    lines = ["digraph dominators {", f"  rankdir={rankdir};", "  node [shape=box fontsize=10];", ""]

    if dom_tree.root is None:
        lines.append("  empty [label=\"No reachable clusters\"];")
        lines.append("}")
        return "\n".join(lines)

    victory_sigs = {
        sig for sig, cluster in cluster_graph.clusters.items()
        if cluster.is_victory
    }

    # Nodes
    for sig, cluster in cluster_graph.clusters.items():
        if sig in dom_tree.unreachable:
            continue

        desc_parts = cluster.description.split(", ")
        desc_short = "\\n".join(desc_parts[:3])
        if len(desc_parts) > 3:
            desc_short += f"\\n+{len(desc_parts) - 3} more"

        descendants = dom_tree.get_descendants(sig)
        is_mandatory = dom_tree.is_mandatory(sig, victory_sigs)

        # Label includes dominator info
        depth = dom_tree.depth.get(sig, 0)
        label_parts = []
        if sig == dom_tree.root:
            label_parts.append("START")
        label_parts.append(str(sig))
        label_parts.append(desc_short)
        label_parts.append(f"depth={depth}, dom={len(descendants)}")

        label = "\\n".join(label_parts)

        # Styling based on role
        if cluster.is_victory:
            style = 'style=filled fillcolor=green'
        elif sig == dom_tree.root:
            style = 'style="filled,bold" fillcolor=yellow penwidth=3'
        elif is_mandatory:
            # Mandatory waypoint - on all paths to victory
            style = 'style=filled fillcolor=orange'
        elif cluster.is_defeat:
            style = 'style=filled fillcolor=red'
        else:
            style = 'style=filled fillcolor=lightblue'

        label = label.replace('"', '\\"')
        lines.append(f'  d{sig} [label="{label}" {style}];')

    # Unreachable nodes (if any)
    if dom_tree.unreachable:
        lines.append("")
        lines.append("  // Unreachable clusters")
        for sig in sorted(dom_tree.unreachable, key=str):
            cluster = cluster_graph.clusters[sig]
            label = f"UNREACHABLE\\n{sig}"
            lines.append(f'  d{sig} [label="{label}" style=filled fillcolor=gray];')

    lines.append("")

    # Build lookup for direct transitions between clusters
    direct_transitions: dict[tuple[ClusterSignature, ClusterSignature], list[str]] = {}
    for trans in cluster_graph.transitions:
        key = (trans.from_sig, trans.to_sig)
        direct_transitions[key] = trans.actions

    # Edges (dominator tree edges with action labels where available)
    for sig, parent in dom_tree.idom.items():
        if parent is not None:
            key = (parent, sig)
            if key in direct_transitions:
                # Direct transition exists - show the action(s)
                actions = direct_transitions[key]
                if len(actions) == 1:
                    label = actions[0].replace("@", "").replace('"', '\\"')
                else:
                    label = f"{len(actions)} actions"
                lines.append(f'  d{parent} -> d{sig} [label="{label}"];')
            else:
                # No direct transition - this is an indirect dominator relationship
                lines.append(f'  d{parent} -> d{sig} [style=dashed color=gray label="indirect"];')

    lines.append("}")
    return "\n".join(lines)


def generate_structure_dot(
    cluster_graph: ClusterGraph,
    dom_tree: DominatorTree,
) -> str:
    """
    Generate a simplified structural view showing victory paths.

    This extracts the "skeleton" of the game - just the mandatory progression
    paths, hiding the optional variations.
    """
    lines = ["digraph structure {", "  rankdir=TB;", "  node [shape=box fontsize=10];", ""]

    if dom_tree.root is None:
        lines.append("  empty [label=\"No reachable clusters\"];")
        lines.append("}")
        return "\n".join(lines)

    victory_sigs = {
        sig for sig, cluster in cluster_graph.clusters.items()
        if cluster.is_victory
    }

    # Collect all clusters that are on mandatory paths
    on_mandatory_path: set[ClusterSignature] = set()
    victory_paths: dict[ClusterSignature, list[ClusterSignature]] = {}

    for victory_sig in victory_sigs:
        path = dom_tree.get_mandatory_path(victory_sig)
        victory_paths[victory_sig] = path
        on_mandatory_path.update(path)

    # Create subgraphs for each major path branch
    # Group victories by their second step (first non-START dominator)
    branches: dict[ClusterSignature | None, list[ClusterSignature]] = {}
    for victory_sig, path in victory_paths.items():
        branch_key = path[1] if len(path) > 1 else None
        if branch_key not in branches:
            branches[branch_key] = []
        branches[branch_key].append(victory_sig)

    # Emit nodes for clusters on mandatory paths
    for sig in on_mandatory_path:
        cluster = cluster_graph.clusters[sig]
        desc_parts = cluster.description.split(", ")
        desc_short = "\\n".join(desc_parts[:2])
        if len(desc_parts) > 2:
            desc_short += f"\\n+{len(desc_parts) - 2}"

        if cluster.is_victory:
            label = f"VICTORY\\n{sig}\\n{desc_short}"
            style = 'style=filled fillcolor=green'
        elif sig == dom_tree.root:
            label = f"START\\n{sig}\\n{desc_short}"
            style = 'style="filled,bold" fillcolor=yellow penwidth=3'
        else:
            label = f"{sig}\\n{desc_short}"
            style = 'style=filled fillcolor=orange'

        label = label.replace('"', '\\"')
        lines.append(f'  s{sig} [label="{label}" {style}];')

    lines.append("")

    # Emit edges (dominator tree edges for mandatory path nodes)
    emitted_edges: set[tuple[str, str]] = set()
    for sig in on_mandatory_path:
        parent = dom_tree.idom.get(sig)
        if parent is not None and parent in on_mandatory_path:
            edge = (str(parent), str(sig))
            if edge not in emitted_edges:
                lines.append(f'  s{parent} -> s{sig};')
                emitted_edges.add(edge)

    lines.append("")

    # Add legend
    lines.append("  // Legend")
    lines.append('  subgraph cluster_legend {')
    lines.append('    label="Victory Paths";')
    lines.append('    fontsize=12;')
    for i, (branch, victories) in enumerate(sorted(branches.items(), key=lambda x: str(x[0]))):
        branch_desc = cluster_graph.clusters[branch].description if branch else "direct"
        vic_count = len(victories)
        lines.append(f'    legend{i} [label="via {branch_desc}\\n({vic_count} victories)" shape=note style=filled fillcolor=lightyellow];')
    lines.append('  }')

    lines.append("}")
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

        # Mark initial cluster
        is_initial = (sig == cluster_graph.initial_sig)
        if is_initial:
            label = f"START\\n{sig}\\n{desc_vertical}\\n({cluster.size} states)"
        else:
            label = f"{sig}\\n{desc_vertical}\\n({cluster.size} states)"

        if cluster.is_victory:
            style = 'style=filled fillcolor=green'
        elif is_initial:
            style = 'style="filled,bold" fillcolor=yellow penwidth=3'
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
