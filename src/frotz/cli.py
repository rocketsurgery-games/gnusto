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
from .guided import GuidedExplorer, find_victory_path
from .clustering import build_hierarchy


def format_section(title: str) -> str:
    """Format a section header."""
    return f"\n{'=' * 60}\n{title}\n{'=' * 60}\n"


def dot_id(s: str) -> str:
    """Convert a string to a valid DOT identifier."""
    # Replace problematic characters
    result = s.replace("@", "").replace(":", "_").replace("-", "_")
    result = result.replace(" ", "_").replace(",", "_").replace("=", "_")
    result = result.replace("!", "not_").replace("{", "").replace("}", "")
    return result


def generate_state_graph_dot(graph: StateGraph) -> str:
    """Generate DOT graph of the actual state transition graph."""
    lines = [
        "digraph states {",
        '  rankdir=LR;',  # Left-to-right layout
        '  node [shape=box fontsize=10];',
        '  edge [fontsize=9];',
        "",
    ]

    # Collect node categories for rank constraints
    start_nodes = []
    victory_nodes = []
    defeat_nodes = []

    # Add nodes
    for node_id, node in graph.nodes.items():
        # Stack properties vertically, with player.loc at top in bold
        props = node.state.short_str().split(", ")
        player_loc = [p for p in props if p.startswith("player.loc=")]
        other_props = [p for p in props if not p.startswith("player.loc=")]

        # Build HTML label with player.loc in bold at top
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

        # Use HTML label format with <br/> for line breaks
        html_label = "<br/>".join(label_lines)
        lines.append(f'  s{node_id} [label=<{html_label}> {style}];')

    # Add rank constraints to position start on left, terminals on right
    lines.append("")
    if start_nodes:
        lines.append(f'  {{ rank=min; {"; ".join(start_nodes)}; }}')
    if victory_nodes or defeat_nodes:
        terminals = victory_nodes + defeat_nodes
        lines.append(f'  {{ rank=max; {"; ".join(terminals)}; }}')

    lines.append("")

    # Add edges, grouping by (from, to) to combine actions
    edge_actions: dict[tuple[int, int], list[str]] = {}
    for edge in graph.edges:
        key = (edge.from_id, edge.to_id)
        # Format: "verb target" or "verb target arg1 arg2"
        action_str = f"{edge.action.verb} {edge.action.target}"
        if edge.action.args:
            action_str += f" {' '.join(edge.action.args)}"
        # Shorten @-prefixed names
        action_str = action_str.replace("@", "")
        if key not in edge_actions:
            edge_actions[key] = []
        edge_actions[key].append(action_str)

    for (from_id, to_id), actions in edge_actions.items():
        # Combine multiple actions on same edge
        label = "\\n".join(actions[:3])  # Limit to 3 to avoid clutter
        if len(actions) > 3:
            label += f"\\n+{len(actions) - 3} more"
        label = label.replace('"', '\\"')

        # Self-loops (actions that don't change state)
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
        "--dot",
        metavar="FILE",
        help="Output state transition graph in DOT format",
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
        "--guided",
        action="store_true",
        help="Use heuristic-guided search (faster, but may not find optimal path)",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=50,
        help="Patience for guided search plateau detection (default: 50)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast mode: stop at first victory using constraint-guided exploration",
    )

    opts = parser.parse_args(args)

    # Walkthrough implies quiet
    if opts.walkthrough:
        opts.quiet = True

    # Load game
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

    # Phase 3: State exploration
    if opts.guided:
        # Guided (heuristic) search mode
        if not opts.quiet:
            print(format_section("Phase 3: Guided Search"))
            print(f"Searching with max depth {opts.max_depth}, patience {opts.patience}...")

        result = find_victory_path(world, relevance, effects, opts.max_depth, opts.patience)

        if not opts.quiet:
            print(f"States explored: {result.states_explored}")
            print(f"Max depth reached: {result.max_depth_reached}")
            if result.constraint_tree_nodes > 0:
                print(f"Backward constraint nodes: {result.constraint_tree_nodes}")
            if result.black_holes_pruned > 0:
                print(f"Black holes pruned: {result.black_holes_pruned}")

        # Convert to legacy format for rest of CLI
        victory_path = result.path if result.found_terminal else None
        victory_count = 1 if result.found_terminal else 0
        defeat_count = 0  # Not tracked in guided mode
        graph = None  # No full graph in guided mode

    elif opts.fast:
        # Fast constraint-guided mode (stop at first victory)
        if not opts.quiet:
            print(format_section("Phase 3: Fast Constraint-Guided Search"))
            print(f"Searching with max depth {opts.max_depth}...")

        hierarchy = build_hierarchy(world, effects, relevance)
        graph, stats = explore_state_space(
            world, relevance, opts.max_depth,
            mode=ExplorationMode.GUIDED_FIRST_VICTORY,
            hierarchy=hierarchy
        )

        if not opts.quiet:
            print(stats.summary())
            print()
            print(graph.summary())

        # Compute victory info
        victory_path = graph.get_victory_path()
        victory_count = sum(1 for n in graph.nodes.values() if n.is_victory)
        defeat_count = sum(1 for n in graph.nodes.values() if n.is_defeat)

    else:
        # Exhaustive BFS mode
        if not opts.quiet:
            print(format_section("Phase 3: State Space Exploration"))
            print(f"Exploring with max depth {opts.max_depth}...")

        graph, stats = explore_state_space(world, relevance, opts.max_depth)

        if not opts.quiet:
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

        # Verdict
        victory_path = graph.get_victory_path()
        victory_count = sum(1 for n in graph.nodes.values() if n.is_victory)
        defeat_count = sum(1 for n in graph.nodes.values() if n.is_defeat)

    # Walkthrough mode: just print the path
    if opts.walkthrough:
        if victory_path is None:
            print("No victory path found.", file=sys.stderr)
            return 1
        print(f"# Walkthrough ({len(victory_path)} steps)\n")
        for i, action in enumerate(victory_path, 1):
            # Format nicely: "1. unlock cell-door (with key)"
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
        if graph is not None:
            print(f"  States: {len(graph.nodes)}")
            print(f"  Transitions: {len(graph.edges)}")
        if defeat_count:
            print(f"  Defeat states: {defeat_count}")
    else:
        print("✗ NO VICTORY PATH FOUND")
        if graph is not None:
            print(f"  States explored: {len(graph.nodes)}")
        if defeat_count:
            print(f"  Defeat states: {defeat_count}")

    # Black hole analysis (requires exhaustive search)
    if opts.black_holes:
        if graph is None:
            print("\n⚠ Black hole analysis requires exhaustive search (don't use --guided)")
        else:
            black_holes = graph.get_black_holes()
            clusters = graph.cluster_black_hole_entries()

            print(format_section("Black Hole Analysis"))
            print(f"Black hole states: {len(black_holes)} (victory unreachable)")
            print(f"Entry point clusters: {len(clusters)}")

            for i, cluster in enumerate(clusters, 1):
                print(f"\n--- Failure Mode {i} ({len(cluster['entries'])} entry points) ---")

                # Show what changed (the delta that triggered doom)
                if cluster['delta']:
                    print("  What changed:")
                    for prop, val in sorted(cluster['delta'].items()):
                        prop_short = prop.replace("@", "").replace(":location", ".loc").replace(":", ".")
                        if isinstance(val, str):
                            val_short = val.replace("@", "")
                        else:
                            val_short = val
                        print(f"    {prop_short} → {val_short}")

                # Show the actions that trigger this
                print(f"  Triggered by: {', '.join(sorted(cluster['actions']))}")

                # Show a sample entry point
                if cluster['entries']:
                    edge, from_props, to_props = cluster['entries'][0]
                    print(f"  Example: {edge.action}")

    # Generate DOT if requested (requires exhaustive search)
    if opts.dot:
        if graph is None:
            print("\n⚠ DOT output requires exhaustive search (don't use --guided)")
        else:
            dot_content = generate_state_graph_dot(graph)
            Path(opts.dot).write_text(dot_content)
            print(f"\nState graph written to: {opts.dot}")

    return 0 if victory_path is not None else 1


if __name__ == "__main__":
    sys.exit(main())
