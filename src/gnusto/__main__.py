"""
Entry point for running Gnusto as a module.

Usage:
  python -m gnusto <game_path> --model nanobanana   # NanoBanana (cloud API)
  python -m gnusto <game_path> --model flux         # FLUX.2 Klein (local CUDA)
  python -m gnusto <game_path> --no-render          # Skip scene generation
  python -m gnusto <game_path> --plain              # Text only, no images or colors
  python -m gnusto <game_path> --web [--port]       # Web UI
"""

import argparse

from .tui import run_tui


def main() -> None:
    """Main entry point with argument parsing."""
    from filfre.cli import VALID_MODELS

    parser = argparse.ArgumentParser(
        description="Play a Grue game with an LLM-powered natural language agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  gnusto games/lurkinghorror/ --model nanobanana     # NanoBanana cloud API
  gnusto games/lurkinghorror/ --model flux           # Local FLUX.2 Klein
  gnusto games/lurkinghorror/ --no-render            # Use cached images only
  gnusto games/lurkinghorror/ --plain                # Text only mode
  gnusto games/lurkinghorror/ --web --model nanobanana  # Web UI
""",
    )
    parser.add_argument(
        "game_path",
        help="Path to game directory containing .grue files",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        required=True,
        choices=VALID_MODELS,
        help="Image generation model: flux (local CUDA) or nanobanana (Google cloud API)",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode to show agent tool calls and Grue I/O",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Disable scene generation (use frozen/cached images only)",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Text-only mode: no images, no colors (for automation/accessibility)",
    )
    parser.add_argument(
        "--web",
        "-w",
        action="store_true",
        help="Launch web UI instead of terminal UI",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8000,
        help="Port for web server (default: 8000)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for web server (default: 127.0.0.1)",
    )

    args = parser.parse_args()

    if args.web:
        from .web import run_server
        run_server(args.game_path, model=args.model, host=args.host, port=args.port, debug=args.debug)
    else:
        run_tui(
            args.game_path,
            model=args.model,
            debug=args.debug,
            no_render=args.no_render,
            plain=args.plain,
        )


if __name__ == "__main__":
    main()
