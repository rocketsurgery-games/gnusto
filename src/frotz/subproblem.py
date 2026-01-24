"""
Subproblem exploration for hierarchical state space analysis.

This module provides tools for defining and exploring isolated subproblems
of a larger game, enabling hierarchical winnability analysis.

Usage:
    from frotz.subproblem import Subproblem, explore_subproblem

    # Define a subproblem
    endgame = Subproblem(
        name="endgame",
        setup=lambda rt: (
            rt.move_object('@player', '@inner-lair'),
            rt.move_object('@frob', '@inner-lair'),
            ...
        ),
        goal=lambda rt: rt.check_victory(),
        refs={LocationRef('@player'), LocationRef('@frob'), ...},
    )

    # Explore it
    result = explore_subproblem(world, endgame, max_depth=10)
    print(result.summary())

    # Generate DOT graph
    dot = result.to_dot()
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from grue import GrueWorld
from grue.runtime import GrueRuntime

from .effects import EffectAnalysis, StateRef, analyze_effects
from .explorer import StateExplorer, StateGraph


StateDict = dict[str, object]


# Helper functions for constructing state dict keys
# These match the format used by StateRef.__str__() in the explorer
def loc_key(obj: str) -> str:
    """Construct state dict key for an object's location.

    Example: loc_key('@player') -> '@player:location'
    """
    return f"{obj}:location"


def prop_key(obj: str, prop: str) -> str:
    """Construct state dict key for an object's property.

    Example: prop_key('@door', 'locked') -> '@door:locked'
    """
    return f"{obj}:{prop}"


def queue_key(event: str) -> str:
    """Construct state dict key for an event queue.

    Example: queue_key('frob-appears') -> 'queue:frob-appears'
    """
    return f"queue:{event}"


@dataclass
class Subproblem:
    """Definition of an isolated subproblem for exploration.

    The goal can be specified as either:
    - goal: A predicate that takes a GrueRuntime (checked only at initial state)
    - state_goal: A predicate that takes a state dict (checked for all states)

    If state_goal is provided, states matching it will be marked as victories.
    """

    name: str
    setup: Callable[[GrueRuntime], None]
    refs: set[StateRef]
    goal: Callable[[GrueRuntime], bool] | None = None
    state_goal: Callable[[StateDict], bool] | None = None
    description: str = ""


@dataclass
class SubproblemResult:
    """Result of exploring a subproblem."""

    subproblem: Subproblem
    graph: StateGraph
    victory_count: int
    defeat_count: int
    victory_path: list | None

    def summary(self) -> str:
        """Return a human-readable summary."""
        lines = [
            f"=== Subproblem: {self.subproblem.name} ===",
            f"States: {len(self.graph.nodes)}",
            f"Victory: {self.victory_count}",
            f"Defeat: {self.defeat_count}",
        ]
        if self.victory_path:
            lines.append(f"Shortest path: {len(self.victory_path)} steps")
            for i, action in enumerate(self.victory_path, 1):
                lines.append(f"  {i}. {action}")
        else:
            lines.append("No victory path found")
        return "\n".join(lines)

    def to_dot(
        self,
        highlight_path: bool = True,
        hide_self_loops: bool = True,
        hide_terminal_outgoing: bool = True,
        hide_regressing: bool = False,
    ) -> str:
        """Generate DOT graph visualization.

        Args:
            highlight_path: Highlight the victory path in green
            hide_self_loops: Remove edges that loop back to the same node (no-ops)
            hide_terminal_outgoing: Remove outgoing edges from victory/defeat nodes
            hide_regressing: Remove edges that go to lower-numbered nodes (backward)
        """
        lines = [
            "digraph subproblem {",
            f'  label="{self.subproblem.name}";',
            "  labelloc=t;",
            "  rankdir=LR;",
            '  node [shape=box fontsize=10 fontname="Helvetica"];',
            '  edge [fontsize=9 fontname="Helvetica"];',
            "",
        ]

        # Collect nodes on victory path for highlighting
        path_nodes = set()
        path_edges_set: set[tuple[int, int]] = set()
        if highlight_path and self.victory_path:
            # Trace path through graph to find node IDs
            path_nodes.add(self.graph.initial_id)
            current = self.graph.initial_id
            for action in self.victory_path:
                for edge in self.graph.edges:
                    if edge.from_id == current and edge.action == action:
                        path_nodes.add(edge.to_id)
                        path_edges_set.add((current, edge.to_id))
                        current = edge.to_id
                        break

        # Identify terminal nodes
        terminal_nodes = {
            node_id
            for node_id, node in self.graph.nodes.items()
            if node.is_victory or node.is_defeat
        }

        # Node definitions
        for node_id, node in sorted(self.graph.nodes.items()):
            # Build label from state
            state_parts = []
            for ref_key, val in node.state.values:
                # Keys are strings like '@frob:location', '@frob:count', 'queue:frob-appears'
                ref_str = str(ref_key)
                if ref_str.endswith(":location"):
                    obj = ref_str[:-9].replace("@", "")
                    val_str = str(val).replace("@", "") if val else "nil"
                    state_parts.append(f"{obj}@{val_str}")
                elif ":" in ref_str and not ref_str.startswith("queue:"):
                    # Property like '@frob:count'
                    parts = ref_str.split(":", 1)
                    obj = parts[0].replace("@", "")
                    prop = parts[1]
                    state_parts.append(f"{obj}.{prop}={val}")
                elif ref_str.startswith("queue:"):
                    event = ref_str[6:]
                    if val is not None:
                        state_parts.append(f"Q:{event}")

            label = "\\n".join(state_parts) if state_parts else f"s{node_id}"

            # Style based on node type
            styles = []
            if node.is_victory:
                styles.append("fillcolor=palegreen")
                styles.append("style=filled")
                label = "VICTORY\\n" + label
            elif node.is_defeat:
                styles.append("fillcolor=lightcoral")
                styles.append("style=filled")
                label = "DEFEAT\\n" + label
            elif node_id == self.graph.initial_id:
                styles.append("fillcolor=lightblue")
                styles.append("style=filled")
                label = "START\\n" + label

            if node_id in path_nodes and not (node.is_victory or node.is_defeat):
                styles.append("penwidth=3")
                styles.append("color=darkgreen")

            style_str = " ".join(styles)
            lines.append(f'  s{node_id} [label="{label}" {style_str}];')

        lines.append("")

        # Edge definitions - group by (from, to)
        edge_labels: dict[tuple[int, int], list[str]] = {}
        for edge in self.graph.edges:
            from_id, to_id = edge.from_id, edge.to_id

            # Skip self-loops (no-op actions)
            if hide_self_loops and from_id == to_id:
                continue

            # Skip outgoing edges from terminal states
            if hide_terminal_outgoing and from_id in terminal_nodes:
                continue

            # Skip regressing edges (unless on victory path)
            if hide_regressing and to_id < from_id:
                if (from_id, to_id) not in path_edges_set:
                    continue

            key = (from_id, to_id)
            action_str = f"{edge.action.verb} {edge.action.target}"
            if edge.action.args:
                action_str += f" {' '.join(edge.action.args)}"
            action_str = action_str.replace("@", "")
            if key not in edge_labels:
                edge_labels[key] = []
            edge_labels[key].append(action_str)

        for (from_id, to_id), labels in edge_labels.items():
            label = "\\n".join(labels[:3])
            if len(labels) > 3:
                label += f"\\n+{len(labels) - 3} more"

            # Check if edge is on the victory path
            on_path = (from_id, to_id) in path_edges_set

            styles = []
            if on_path:
                styles.append("penwidth=2")
                styles.append("color=darkgreen")
                # High weight pulls path nodes closer together
                styles.append("weight=10")
            else:
                # Low weight for non-path edges
                styles.append("weight=1")

            style_str = " ".join(styles)
            lines.append(f'  s{from_id} -> s{to_id} [label="{label}" {style_str}];')

        lines.append("}")
        return "\n".join(lines)


def explore_subproblem(
    world: GrueWorld,
    subproblem: Subproblem,
    max_depth: int = 20,
    max_states: int = 1000,
    effects: EffectAnalysis | None = None,
) -> SubproblemResult:
    """Explore a subproblem and return the result.

    If subproblem.state_goal is provided, states matching it will be marked
    as victories during exploration, enabling early termination when a goal
    state is found.
    """
    if effects is None:
        effects = analyze_effects(world)

    # Wrap state_goal to work with GameState instead of dict
    state_goal_check = None
    if subproblem.state_goal is not None:
        state_goal_check = lambda gs: subproblem.state_goal(dict(gs.values))

    explorer = StateExplorer(
        world,
        state_refs=subproblem.refs,
        max_depth=max_depth,
        max_states=max_states,
        setup=subproblem.setup,
        goal_check=subproblem.goal,
        state_goal_check=state_goal_check,
        effects=effects,
    )

    graph = explorer.explore()

    victory_count = sum(1 for n in graph.nodes.values() if n.is_victory)
    defeat_count = sum(1 for n in graph.nodes.values() if n.is_defeat)
    victory_path = graph.get_victory_path()

    return SubproblemResult(
        subproblem=subproblem,
        graph=graph,
        victory_count=victory_count,
        defeat_count=defeat_count,
        victory_path=victory_path,
    )


def save_dot(result: SubproblemResult, path: str | Path) -> None:
    """Save subproblem result as DOT file."""
    Path(path).write_text(result.to_dot())
