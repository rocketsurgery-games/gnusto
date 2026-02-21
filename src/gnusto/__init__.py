"""
Gnusto - LLM-powered interactive fiction system.

Named after the write-magic-spell from Enchanter, Gnusto is an IF authoring
and playing system. It uses Grue as its world definition language.

Architecture:
- llm.py: Model interface and tool-calling infrastructure
- state.py: Game state serialization for agent context
- agent.py: Agent loop, session management, and UI
- tui.py: Terminal interface with Rich formatting
- terminal_images.py: Terminal image display (Kitty/iTerm2 protocols)

Submodules:
- frotz/: State-space analyzer for winnability verification (future)
"""

from .agent import GameSession, play_game
from .state import GameState, ObjectInfo, RoomInfo
from .terminal_images import display_image, is_supported as terminal_images_supported

__all__ = [
    "GameSession",
    "play_game",
    "GameState",
    "ObjectInfo",
    "RoomInfo",
    "display_image",
    "terminal_images_supported",
]
