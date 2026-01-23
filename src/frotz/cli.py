"""
Frotz CLI - State space analysis for Grue games.

Usage:
    frotz <game_path> [options]

Examples:
    frotz games/testgame/testgame.grue
    frotz games/lurkinghorror/ --max-depth 50
    frotz games/testgame/testgame.grue --dot states.dot

Note: This CLI has been simplified to focus on core constraint back-propagation
and state exploration. Clustering, dominators, regions, and relevance analysis
have been moved to frotz/deferred/ for later integration.
"""

import argparse
import sys
from pathlib import Path

from grue import load_grue

from .effects import analyze_effects, LocationRef
from .backward import build_victory_constraints, collect_constraint_refs
from .explorer import explore_state_space, StateGraph, ExplorationMode


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
        help="Output state graph in DOT format",
    )
    parser.add_argument(
        "--effects-only",
        action="store_true",
        help="Only run effect analysis (skip exploration)",
    )
    parser.add_argument(
        "--constraints-only",
        action="store_true",
        help="Only run effect and constraint analysis (skip exploration)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Minimal output (just verdict)",
    )
    parser.add_argument(
        "--walkthrough",
        action="store_true",
        help="Output just the shortest victory path (walkthrough)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Stop at first victory (don't explore full state space)",
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

    if not world.victory:
        print("\n⚠ No victory condition defined - skipping exploration")
        return 0

    # Phase 2: Constraint back-propagation
    victory_trees = build_victory_constraints(world, effects)

    if not opts.quiet:
        print(format_section("Phase 2: Constraint Back-Propagation"))
        print(f"Built {len(victory_trees)} constraint trees")
        for tree in victory_trees:
            print(f"\n{tree}")

    # Collect state refs from constraints
    constraint_refs = collect_constraint_refs(victory_trees)
    constraint_refs.add(LocationRef('@player'))  # Always track player location

    if not opts.quiet:
        print(f"\nTracking {len(constraint_refs)} state refs:")
        for ref in sorted(str(r) for r in constraint_refs):
            print(f"  {ref}")

    if opts.constraints_only:
        return 0

    # Phase 3: State exploration
    if not opts.quiet:
        print(format_section("Phase 3: State Space Exploration"))
        print(f"Exploring with max depth {opts.max_depth}...")

    mode = ExplorationMode.GUIDED_FIRST_VICTORY if opts.fast else ExplorationMode.GUIDED
    graph, stats = explore_state_space(
        world, constraint_refs, opts.max_depth, mode, None, opts.max_states
    )

    if not opts.quiet:
        print(stats.summary())
        print()
        print(graph.summary())

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

    # Generate DOT if requested
    if opts.dot:
        dot_content = generate_state_graph_dot(graph)
        Path(opts.dot).write_text(dot_content)
        print(f"\nState graph written to: {opts.dot} ({len(graph.nodes)} states)")

    return 0 if victory_path is not None else 1


if __name__ == "__main__":
    sys.exit(main())
