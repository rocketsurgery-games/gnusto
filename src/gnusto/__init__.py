"""
Gnusto - LLM-powered interactive fiction system.

Named after the write-magic-spell from Enchanter, Gnusto is an IF authoring
and playing system. It uses Grue as its world definition language.

Architecture:
- llm.py: Model interface and tool-calling infrastructure
- state.py: Game state serialization for agent context
- agent.py: Agent loop, session management, and UI
- tui.py: Fullscreen Textual terminal interface

Submodules:
- frotz/: State-space analyzer for winnability verification (future)
"""

from .agent import GameSession, play_game
from .state import GameState, ObjectInfo, RoomInfo

__all__ = ["GameSession", "play_game", "GameState", "ObjectInfo", "RoomInfo"]
