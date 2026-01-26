"""
Entry point for running Gnusto as a module.

Usage: python -m gnusto <game_path> [--debug]
"""

import argparse

from .tui import run_tui


def main() -> None:
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Play a Grue game with an LLM-powered natural language agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example: python -m gnusto games/lurkinghorror/ --debug",
    )
    parser.add_argument(
        "game_path",
        help="Path to game directory containing .grue files",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode to show agent tool calls and Grue I/O",
    )

    args = parser.parse_args()
    run_tui(args.game_path, debug=args.debug)


if __name__ == "__main__":
    main()
