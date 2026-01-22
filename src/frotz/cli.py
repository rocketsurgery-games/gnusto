"""
Frotz CLI - State space analysis for Grue games.

Usage:
    frotz <game_path> [options]

Examples:
    frotz games/testgame/testgame.grue
    frotz games/lurkinghorror/ --max-depth 50
    frotz games/testgame/testgame.grue --dot states.dot
"""

import argparse
import sys
from pathlib import Path

from grue import load_grue

from .effects import analyze_effects
from .relevance import analyze_relevance
from .explorer import explore_state_space, StateGraph, ExplorationMode
from .clustering import (
    build_hierarchy,
    cluster_state_graph,
    generate_cluster_dot,
    compute_dominators,
    generate_dominator_dot,
    generate_structure_dot,
    compute_regions,
    generate_region_dot,
)


def format_section(title: str) -> str:
    """Format a section header."""
    return f"\n{'=' * 60}\n{title}\n{'=' * 60}\n"


def generate_state_graph_dot(graph: StateGraph) -> str:
    """Generate DOT graph of the actual state transition graph."""
    lines = [
        "digraph states {",
        '  rankdir=LR;',
        '  node [shape=box fontsize=10];',
        '  edge [fontsize=9];',
        "",
    ]

    start_nodes = []
    victory_nodes = []
    defeat_nodes = []

    for node_id, node in graph.nodes.items():
        props = node.state.short_str().split(", ")
        player_loc = [p for p in props if p.startswith("player.loc=")]
        other_props = [p for p in props if not p.startswith("player.loc=")]

        label_lines = []
        if player_loc:
            label_lines.append(f"<b>{player_loc[0]}</b>")
        label_lines.extend(other_props)

        if node.is_victory:
            style = 'style=filled fillcolor=green'
            label_lines.insert(0, "<b>VICTORY</b>")
            victory_nodes.append(f"s{node_id}")
        elif node.is_defeat:
            style = 'style=filled fillcolor=red'
            label_lines.insert(0, "<b>DEFEAT</b>")
            defeat_nodes.append(f"s{node_id}")
        elif node_id == graph.initial_id:
            style = 'style=filled fillcolor=lightblue'
            label_lines.insert(0, "<b>START</b>")
            start_nodes.append(f"s{node_id}")
        else:
            style = ''

        html_label = "<br/>".join(label_lines)
        lines.append(f'  s{node_id} [label=<{html_label}> {style}];')

    lines.append("")
    if start_nodes:
        lines.append(f'  {{ rank=min; {"; ".join(start_nodes)}; }}')
    if victory_nodes or defeat_nodes:
        terminals = victory_nodes + defeat_nodes
        lines.append(f'  {{ rank=max; {"; ".join(terminals)}; }}')

    lines.append("")

    edge_actions: dict[tuple[int, int], list[str]] = {}
    for edge in graph.edges:
        key = (edge.from_id, edge.to_id)
        action_str = f"{edge.action.verb} {edge.action.target}"
        if edge.action.args:
            action_str += f" {' '.join(edge.action.args)}"
        action_str = action_str.replace("@", "")
        if key not in edge_actions:
            edge_actions[key] = []
        edge_actions[key].append(action_str)

    for (from_id, to_id), actions in edge_actions.items():
        label = "\\n".join(actions[:3])
        if len(actions) > 3:
            label += f"\\n+{len(actions) - 3} more"
        label = label.replace('"', '\\"')

        if from_id == to_id:
            lines.append(f'  s{from_id} -> s{to_id} [label="{label}" style=dashed color=gray];')
        else:
            lines.append(f'  s{from_id} -> s{to_id} [label="{label}"];')

    lines.append("}")
    return "\n".join(lines)


def main(args: list[str] | None = None):
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Frotz - State space analysis for Grue games",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "game_path",
        help="Path to .grue file or directory containing game",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=100,
        help="Maximum exploration depth (default: 100)",
    )
    parser.add_argument(
        "--max-states",
        type=int,
        default=None,
        help="Maximum states to explore (default: unlimited)",
    )
    parser.add_argument(
        "--dot",
        metavar="FILE",
        help="Output cluster graph in DOT format (states collapsed by constraint signature)",
    )
    parser.add_argument(
        "--dot-raw",
        metavar="FILE",
        help="Output raw state graph in DOT format (all states, no collapsing)",
    )
    parser.add_argument(
        "--effects-only",
        action="store_true",
        help="Only run effect analysis (skip exploration)",
    )
    parser.add_argument(
        "--relevance-only",
        action="store_true",
        help="Only run effect and relevance analysis (skip exploration)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Minimal output (just verdict)",
    )
    parser.add_argument(
        "--minimize",
        action="store_true",
        help="Apply bisimulation minimization to reduce equivalent states",
    )
    parser.add_argument(
        "--walkthrough",
        action="store_true",
        help="Output just the shortest victory path (walkthrough)",
    )
    parser.add_argument(
        "--black-holes",
        action="store_true",
        help="Analyze black holes (states from which victory is unreachable)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Stop at first victory (don't explore full state space)",
    )
    parser.add_argument(
        "--dominators",
        metavar="FILE",
        help="Output dominator tree in DOT format (shows mandatory progression structure)",
    )
    parser.add_argument(
        "--structure",
        metavar="FILE",
        help="Output simplified structure graph (just mandatory victory paths)",
    )
    parser.add_argument(
        "--regions",
        metavar="FILE",
        help="Output region graph in DOT format (SCCs as puzzle regions)",
    )

    opts = parser.parse_args(args)

    if opts.walkthrough:
        opts.quiet = True

    game_path = Path(opts.game_path)
    if not game_path.exists():
        print(f"Error: {game_path} not found", file=sys.stderr)
        return 1

    try:
        world = load_grue(str(game_path))
    except Exception as e:
        print(f"Error loading game: {e}", file=sys.stderr)
        return 1

    if not opts.quiet:
        print(f"Frotz - Analyzing: {world.name or game_path}")

    # Phase 1: Effect analysis
    effects = analyze_effects(world)

    if not opts.quiet:
        print(format_section("Phase 1: Effect Analysis"))
        print(effects.summary())

    if opts.effects_only:
        return 0

    # Phase 2: Relevance analysis
    relevance = analyze_relevance(world, effects)

    if not opts.quiet:
        print(format_section("Phase 2: Relevance Analysis"))
        print(relevance.summary())

    if not world.victory:
        print("\n⚠ No victory condition defined - skipping exploration")
        return 0

    if opts.relevance_only:
        return 0

    # Phase 3: State exploration (always constraint-guided)
    if not opts.quiet:
        print(format_section("Phase 3: State Space Exploration"))
        print(f"Exploring with max depth {opts.max_depth}...")

    hierarchy = build_hierarchy(world, effects, relevance)
    mode = ExplorationMode.GUIDED_FIRST_VICTORY if opts.fast else ExplorationMode.GUIDED
    graph, stats = explore_state_space(
        world, relevance, opts.max_depth, mode, hierarchy, opts.max_states
    )

    if not opts.quiet:
        print(stats.summary())
        print()
        print(graph.summary())

    # Bisimulation minimization
    if opts.minimize:
        original_states = len(graph.nodes)
        original_edges = len(graph.edges)
        graph = graph.minimize()
        if not opts.quiet:
            print(f"\nAfter bisimulation minimization:")
            print(f"  States: {original_states} → {len(graph.nodes)}")
            print(f"  Transitions: {original_edges} → {len(graph.edges)}")

    victory_path = graph.get_victory_path()
    victory_count = sum(1 for n in graph.nodes.values() if n.is_victory)
    defeat_count = sum(1 for n in graph.nodes.values() if n.is_defeat)

    # Walkthrough mode
    if opts.walkthrough:
        if victory_path is None:
            print("No victory path found.", file=sys.stderr)
            return 1
        print(f"# Walkthrough ({len(victory_path)} steps)\n")
        for i, action in enumerate(victory_path, 1):
            target = action.target.replace("@", "")
            if action.args:
                args_str = " ".join(a.replace("@", "") for a in action.args)
                print(f"{i:2}. {action.verb} {target} {args_str}")
            else:
                print(f"{i:2}. {action.verb} {target}")
        return 0

    print(format_section("Verdict"))
    if victory_path is not None:
        print(f"✓ WINNABLE - Victory reachable in {len(victory_path)} steps")
        print(f"  States: {len(graph.nodes)}")
        print(f"  Transitions: {len(graph.edges)}")
        if defeat_count:
            print(f"  Defeat states: {defeat_count}")
    else:
        print("✗ NO VICTORY PATH FOUND")
        print(f"  States explored: {len(graph.nodes)}")
        if defeat_count:
            print(f"  Defeat states: {defeat_count}")

    # Black hole analysis
    if opts.black_holes:
        black_holes = graph.get_black_holes()
        clusters = graph.cluster_black_hole_entries()

        print(format_section("Black Hole Analysis"))
        print(f"Black hole states: {len(black_holes)} (victory unreachable)")
        print(f"Entry point clusters: {len(clusters)}")

        for i, cluster in enumerate(clusters, 1):
            print(f"\n--- Failure Mode {i} ({len(cluster['entries'])} entry points) ---")

            if cluster['delta']:
                print("  What changed:")
                for prop, val in sorted(cluster['delta'].items()):
                    prop_short = prop.replace("@", "").replace(":location", ".loc").replace(":", ".")
                    if isinstance(val, str):
                        val_short = val.replace("@", "")
                    else:
                        val_short = val
                    print(f"    {prop_short} → {val_short}")

            print(f"  Triggered by: {', '.join(sorted(cluster['actions']))}")

            if cluster['entries']:
                edge, from_props, to_props = cluster['entries'][0]
                print(f"  Example: {edge.action}")

    # Generate DOT if requested
    if opts.dot:
        # Cluster graph (collapsed by constraint signature)
        clusters = cluster_state_graph(graph, hierarchy)
        dot_content = generate_cluster_dot(clusters)
        Path(opts.dot).write_text(dot_content)
        print(f"\nCluster graph written to: {opts.dot} ({len(clusters.clusters)} clusters from {len(graph.nodes)} states)")

    if opts.dot_raw:
        # Raw state graph (all states)
        dot_content = generate_state_graph_dot(graph)
        Path(opts.dot_raw).write_text(dot_content)
        print(f"\nRaw state graph written to: {opts.dot_raw} ({len(graph.nodes)} states)")

    if opts.dominators or opts.structure:
        # Compute clusters and dominators (needed for both outputs)
        clusters = cluster_state_graph(graph, hierarchy)
        dom_tree = compute_dominators(clusters)
        victory_sigs = {s for s, c in clusters.clusters.items() if c.is_victory}
        mandatory_count = sum(
            1 for sig in clusters.clusters
            if dom_tree.is_mandatory(sig, victory_sigs)
        )

    if opts.dominators:
        # Dominator tree (full mandatory progression structure)
        dot_content = generate_dominator_dot(clusters, dom_tree)
        Path(opts.dominators).write_text(dot_content)
        print(f"\nDominator tree written to: {opts.dominators}")
        print(f"  {len(clusters.clusters)} clusters, {mandatory_count} mandatory waypoints")
        if dom_tree.unreachable:
            print(f"  {len(dom_tree.unreachable)} unreachable clusters")

    if opts.structure:
        # Simplified structure graph (just mandatory paths)
        dot_content = generate_structure_dot(clusters, dom_tree)
        Path(opts.structure).write_text(dot_content)
        print(f"\nStructure graph written to: {opts.structure}")
        print(f"  {len(victory_sigs)} victory paths, {mandatory_count} mandatory waypoints")

    if opts.regions:
        # Region graph (SCCs as puzzle regions)
        clusters = cluster_state_graph(graph, hierarchy)
        region_graph = compute_regions(clusters)
        dot_content = generate_region_dot(region_graph, clusters)
        Path(opts.regions).write_text(dot_content)

        # Count region types
        multi_cluster = sum(1 for r in region_graph.regions.values() if r.size > 1)
        victories = sum(1 for r in region_graph.regions.values() if r.has_victory and r.is_terminal)
        defeats = sum(1 for r in region_graph.regions.values() if r.has_defeat and r.is_terminal)

        print(f"\nRegion graph written to: {opts.regions}")
        print(f"  {len(region_graph.regions)} regions ({multi_cluster} explorable, {victories} victories, {defeats} defeats)")
        print(f"  {len(region_graph.transitions)} inter-region transitions")

    return 0 if victory_path is not None else 1


if __name__ == "__main__":
    sys.exit(main())
