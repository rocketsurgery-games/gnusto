"""
Frotz - LLM-powered agent for playing interactive fiction.

Named after the iconic Infocom interpreter, this package provides the agent
layer that plays GRUE games using language models.

Architecture:
- llm.py: Model interface and tool-calling infrastructure
- state.py: Game state serialization for agent context
- agent.py: Agent loop, session management, and UI
"""

from .agent import GameSession, play_game
from .state import GameState, ObjectInfo, RoomInfo

__all__ = ["GameSession", "play_game", "GameState", "ObjectInfo", "RoomInfo"]
