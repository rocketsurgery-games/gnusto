"""
Entry point for running Frotz as a module.

Usage: python -m frotz <game_path> [--debug]
"""

import argparse

from .agent import play_game


def main() -> None:
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Play a GRUE game with an LLM-powered natural language agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example: python -m frotz games/lurkinghorror/ --debug",
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
    play_game(args.game_path, debug=args.debug)


if __name__ == "__main__":
    main()
