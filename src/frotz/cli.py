"""
Frotz CLI - State space analysis for Grue games.

Usage:
    frotz <game_path> [options]

Examples:
    frotz games/testgame/testgame.grue
    frotz games/lurkinghorror/ --max-depth 50
    frotz games/testgame/testgame.grue --dot puzzle.dot
"""

import argparse
import sys
from pathlib import Path

from grue import load_grue

from .effects import analyze_effects
from .relevance import analyze_relevance
from .explorer import explore_state_space


def format_section(title: str) -> str:
    """Format a section header."""
    return f"\n{'=' * 60}\n{title}\n{'=' * 60}\n"


def dot_id(s: str) -> str:
    """Convert a string to a valid DOT identifier (snake_case)."""
    return s.replace(":", "_").replace("@", "").replace("-", "_")


def generate_dot(world, effects, relevance, result) -> str:
    """Generate DOT graph of puzzle dependencies."""
    lines = [
        "digraph puzzle {",
        '  rankdir=BT;',  # Bottom to top (victory at top)
        '  node [shape=box];',
        "",
        "  // Victory condition",
        '  victory [label="VICTORY" shape=doubleoctagon style=filled fillcolor=green];',
        "",
        "  // Puzzle-relevant state",
    ]

    # Add nodes for relevant state
    for ref in sorted(relevance.relevant, key=str):
        ref_id = dot_id(str(ref))
        label = str(ref)
        lines.append(f'  {ref_id} [label="{label}"];')

    lines.append("")
    lines.append("  // Dependencies (what must change for victory)")

    # Add edges from victory condition refs
    for ref in relevance.victory_refs:
        ref_id = dot_id(str(ref))
        lines.append(f'  {ref_id} -> victory;')

    lines.append("")
    lines.append("  // Behavior dependencies (what behaviors read/modify)")

    # Add edges for behavior dependencies
    for ref in relevance.relevant:
        ref_id = dot_id(str(ref))
        # Find what this state depends on (behaviors that modify it read other state)
        modifiers = effects.modifies.get(ref, set())
        for behavior in modifiers:
            # What does this behavior read?
            for read_ref, readers in effects.reads.items():
                if behavior in readers and read_ref in relevance.relevant:
                    read_id = dot_id(str(read_ref))
                    if read_id != ref_id:  # Avoid self-loops
                        lines.append(f'  {read_id} -> {ref_id} [label="{behavior.verb}"];')

    lines.append("")
    lines.append("  // Winning path")

    if result.victory_path:
        lines.append('  subgraph cluster_path {')
        lines.append('    label="Winning Path";')
        lines.append('    style=dashed;')
        for i, action in enumerate(result.victory_path):
            node_id = f"step{i}"
            lines.append(f'    {node_id} [label="{i+1}. {action.verb} {action.target}" shape=ellipse];')
        # Chain the steps
        for i in range(len(result.victory_path) - 1):
            lines.append(f'    step{i} -> step{i+1};')
        if result.victory_path:
            lines.append(f'    step{len(result.victory_path)-1} -> victory [style=bold];')
        lines.append('  }')

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
        help="Output puzzle dependency graph in DOT format",
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

    result = explore_state_space(world, effects, relevance, opts.max_depth)

    if not opts.quiet:
        print(result.summary())

    # Verdict
    print(format_section("Verdict"))
    if result.victory_found:
        print(f"✓ WINNABLE - Victory reachable in {result.victory_depth} steps")
        print(f"  States explored: {result.states_explored}")
        print(f"  Unique states: {result.states_visited}")
    else:
        print("✗ NO VICTORY PATH FOUND")
        if result.dead_ends:
            print(f"  Dead ends: {len(result.dead_ends)}")
        if result.defeat_states:
            print(f"  Defeat states: {len(result.defeat_states)}")

    # Generate DOT if requested
    if opts.dot:
        dot_content = generate_dot(world, effects, relevance, result)
        Path(opts.dot).write_text(dot_content)
        print(f"\nPuzzle graph written to: {opts.dot}")

    return 0 if result.victory_found else 1


if __name__ == "__main__":
    sys.exit(main())
