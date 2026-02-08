"""
Shared slash command handling for TUI and web UI.

Provides a unified command processor that returns content blocks,
allowing both interfaces to handle commands identically.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from grue.save import save_game, load_game, list_saves

from .agent import GameSession, TurnRecord
from .render import ContentBlock, SystemMessage, RoomEnter, build_room_block
from .state import get_game_state


# Special actions that the UI must handle
CommandAction = Literal["quit", "clear", "reset"] | None


@dataclass
class CommandResult:
    """Result of processing a slash command."""
    blocks: list[ContentBlock] = field(default_factory=list)
    action: CommandAction = None


HELP_TEXT = """Available commands:
  /help, /h, /?     Show this help
  /look, /l         Show current room
  /save [slot]      Save game (default slot: "default")
  /load [slot]      Load game
  /saves            List saved games
  /debug, /d        Show debug context
  /clear            Clear screen
  /reset            Restart game
  /quit, /q         Quit game"""


def handle_command(
    command: str,
    session: GameSession,
    game_dir: Path | None = None,
) -> CommandResult:
    """
    Process a slash command and return content blocks.

    Args:
        command: The command string (including leading /)
        session: Current game session
        game_dir: Game directory for image paths

    Returns:
        CommandResult with blocks to display and optional action
    """
    parts = command[1:].split(maxsplit=1)
    cmd = parts[0].lower() if parts else ""
    arg = parts[1] if len(parts) > 1 else ""

    result = CommandResult()

    if cmd in ("help", "h", "?"):
        result.blocks.append(SystemMessage(text=HELP_TEXT))

    elif cmd == "save":
        slot = arg or "default"
        try:
            path = save_game(session.runtime, slot, session.turn_history, session.summaries)
            result.blocks.append(SystemMessage(text=f"Game saved to {path}"))
        except Exception as e:
            result.blocks.append(SystemMessage(text=f"Error saving: {e}", level="error"))

    elif cmd == "load":
        slot = arg or "default"
        try:
            history_data, summaries_data, warnings = load_game(session.runtime, slot)
            for w in warnings:
                result.blocks.append(SystemMessage(text=f"Warning: {w}", level="warning"))
            session.turn_history.clear()
            for turn_data in history_data:
                turn = TurnRecord(
                    room=turn_data.get("room", ""),
                    player_command=turn_data.get("command", ""),
                    actions=turn_data.get("actions", []),
                    results=turn_data.get("results", []),
                    narrative=turn_data.get("narrative", ""),
                )
                session.turn_history.append(turn)
            session.summaries = summaries_data
            result.blocks.append(SystemMessage(text=f"Game loaded ({len(session.turn_history)} turns, {len(session.summaries)} summaries)"))
            # Add room block to show current state
            state = get_game_state(session.runtime)
            room_block = build_room_block(state, session.runtime, game_dir)
            result.blocks.append(room_block)
        except FileNotFoundError:
            result.blocks.append(SystemMessage(text=f"No save found for slot '{slot}'", level="error"))
        except Exception as e:
            result.blocks.append(SystemMessage(text=f"Error loading: {e}", level="error"))

    elif cmd == "saves":
        game_name = session.runtime.world.name or "unknown"
        saves = list_saves(game_name)
        if not saves:
            result.blocks.append(SystemMessage(text="No saves found."))
        else:
            lines = ["Available saves:"]
            for slot, timestamp, _ in saves:
                lines.append(f"  {slot}: {timestamp}")
            result.blocks.append(SystemMessage(text="\n".join(lines)))

    elif cmd in ("look", "l"):
        state = get_game_state(session.runtime)
        room_block = build_room_block(state, session.runtime, game_dir)
        result.blocks.append(room_block)

    elif cmd in ("debug", "d"):
        context = session.format_debug_context()
        result.blocks.append(SystemMessage(text=f"─── Debug Context ───\n{context}\n─────────────────────"))

    elif cmd == "clear":
        result.action = "clear"

    elif cmd == "reset":
        result.action = "reset"
        result.blocks.append(SystemMessage(text="Game reset."))

    elif cmd in ("quit", "q"):
        result.action = "quit"

    else:
        result.blocks.append(SystemMessage(text=f"Unknown command: /{cmd}"))

    return result
