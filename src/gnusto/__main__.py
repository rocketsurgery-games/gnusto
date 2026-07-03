"""
Entry point for running Gnusto as a module.

Usage:
  python -m gnusto <game_path>              # Play a game
  python -m gnusto <game_path> --debug      # Show agent tool calls
  python -m gnusto <game_path> --plain      # Text only, no images or colors
  python -m gnusto <game_path> --web        # Web UI
  python -m gnusto <game_path> --model local  # Use local MLX model
"""

import argparse

from .llm import LLMConfig
from .tui import run_tui

# Well-known model aliases
MODEL_ALIASES = {
    "local": "openai/mlx-community/Qwen3-4B-4bit",
    "local8b": "openai/mlx-community/Qwen3-8B-4bit",
    "sonnet": "anthropic/claude-sonnet-4-20250514",
    "haiku": "anthropic/claude-haiku-4-5-20251001",
}

# Models that need a local server
LOCAL_API_BASE = "http://localhost:8800/v1"


def resolve_llm_config(model_arg: str | None) -> LLMConfig | None:
    """Resolve --model argument into an LLMConfig, or None for env/default."""
    if model_arg is None:
        return None  # Use env vars / defaults

    model = MODEL_ALIASES.get(model_arg, model_arg)

    # If model starts with openai/ and no GRUE_LLM_API_BASE is set,
    # assume a local server
    import os

    api_base = os.getenv("GRUE_LLM_API_BASE")
    if model.startswith("openai/") and not api_base:
        api_base = LOCAL_API_BASE
        # Set a dummy API key if none exists
        if not os.getenv("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = "not-needed"

    return LLMConfig(model=model, api_base=api_base)


def main() -> None:
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Play a Grue game with an LLM-powered natural language agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  gnusto games/lurkinghorror/                # Play a game
  gnusto games/lurkinghorror/ --debug        # Show agent tool calls
  gnusto games/lurkinghorror/ --plain        # Text only mode
  gnusto games/lurkinghorror/ --web          # Web UI
  gnusto games/lurkinghorror/ --model local  # Local Qwen3-4B via MLX
  gnusto games/lurkinghorror/ -m local8b    # Local Qwen3-8B via MLX
""",
    )
    parser.add_argument(
        "game_path",
        help="Path to game directory containing .grue files",
    )
    parser.add_argument(
        "--model",
        "-m",
        help="LLM model to use. Aliases: 'sonnet', 'haiku', 'local' (Qwen3-4B), "
        "'local8b' (Qwen3-8B). Or a litellm model ID "
        "(e.g., 'anthropic/claude-sonnet-4-20250514')",
    )
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="Parse-only mode: the LLM only chooses actions; the game engine "
        "emits all text (no model-authored prose). On by default for local models.",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode to show agent tool calls and Grue I/O",
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
    llm_config = resolve_llm_config(args.model)
    # Only force parse-only when the flag is given; otherwise leave it to the
    # per-model default (None -> auto-enabled for local models).
    parse_only = True if args.parse_only else None

    if args.web:
        from .web import run_server

        run_server(
            args.game_path,
            host=args.host,
            port=args.port,
            debug=args.debug,
            llm_config=llm_config,
            parsing_only=parse_only,
        )
    else:
        run_tui(
            args.game_path,
            debug=args.debug,
            plain=args.plain,
            llm_config=llm_config,
            parsing_only=parse_only,
        )


if __name__ == "__main__":
    main()
