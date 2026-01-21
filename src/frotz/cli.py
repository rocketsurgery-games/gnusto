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
from .explorer import explore_state_space, StateGraph


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
        '  rankdir=TB;',
        '  node [shape=box fontsize=10];',
        '  edge [fontsize=9];',
        "",
    ]

    # Add nodes
    for node_id, node in graph.nodes.items():
        label = node.state.short_str()
        # Escape quotes in label
        label = label.replace('"', '\\"')

        if node.is_victory:
            style = 'style=filled fillcolor=green'
            label = f"VICTORY\\n{label}"
        elif node.is_defeat:
            style = 'style=filled fillcolor=red'
            label = f"DEFEAT\\n{label}"
        elif node_id == graph.initial_id:
            style = 'style=filled fillcolor=lightblue'
            label = f"START\\n{label}"
        else:
            style = ''

        lines.append(f'  s{node_id} [label="{label}" {style}];')

    lines.append("")

    # Add edges, grouping by (from, to) to combine actions
    edge_actions: dict[tuple[int, int], list[str]] = {}
    for edge in graph.edges:
        key = (edge.from_id, edge.to_id)
        action_str = f"{edge.action.verb}"
        if edge.action.args:
            action_str += f" {' '.join(edge.action.args)}"
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

    opts = parser.parse_args(args)

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
    if not opts.quiet:
        print(format_section("Phase 3: State Space Exploration"))
        print(f"Exploring with max depth {opts.max_depth}...")

    graph = explore_state_space(world, relevance, opts.max_depth)

    if not opts.quiet:
        print(graph.summary())

    # Verdict
    victory_path = graph.get_victory_path()
    victory_count = sum(1 for n in graph.nodes.values() if n.is_victory)
    defeat_count = sum(1 for n in graph.nodes.values() if n.is_defeat)

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
        print(f"\nState graph written to: {opts.dot}")

    return 0 if victory_path is not None else 1


if __name__ == "__main__":
    sys.exit(main())
