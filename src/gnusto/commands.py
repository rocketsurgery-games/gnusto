"""
Shared slash command handling for TUI and web UI.

Provides a unified command processor that returns content blocks,
allowing both interfaces to handle commands identically.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TYPE_CHECKING

from grue.save import save_game, load_game, list_saves
from grue.sexpr import parse

from .render import ContentBlock, SystemMessage, RoomEnter, DebugInfo, build_room_block

if TYPE_CHECKING:
    from .agent import GameSession
from .state import get_game_state


# Special actions that the UI must handle
CommandAction = Literal["quit", "clear", "reset"] | None


@dataclass
class CommandResult:
    """Result of processing a slash command."""
    blocks: list[ContentBlock] = field(default_factory=list)
    action: CommandAction = None


def render_block_to_text(block: ContentBlock) -> str:
    """Render a content block to plain text for CLI output."""
    if isinstance(block, SystemMessage):
        prefix = ""
        if block.level == "warning":
            prefix = "Warning: "
        elif block.level == "error":
            prefix = "Error: "
        return f"{prefix}{block.text}"
    elif isinstance(block, RoomEnter):
        lines = [f"\n=== {block.name} ===\n", block.description]
        if block.objects:
            lines.append("")
            for obj in block.objects:
                lines.append(obj)
        if block.exits:
            lines.append(f"\nNearby: {', '.join(block.exits)}")
        if block.inventory:
            lines.append(f"Carrying: {', '.join(block.inventory)}")
        return "\n".join(lines)
    elif isinstance(block, DebugInfo):
        return f"  [{block.label}] {block.content}"
    else:
        # ActionResult, Narrate, Speak, etc. - just return text if available
        return getattr(block, "text", str(block))


def render_blocks_to_text(blocks: list[ContentBlock]) -> str:
    """Render a list of content blocks to plain text."""
    return "\n".join(render_block_to_text(b) for b in blocks)


HINT_PROMPT = """\
You are a helpful hint system for an interactive fiction game. \
The player is stuck and wants suggestions for what to try next.

Based on the current game state and recent history, suggest 2-4 concrete, \
actionable next steps. Each suggestion should be something the player could \
actually type as a command.

Rules:
- Be specific: reference actual objects, characters, and locations from the game state
- Suggest actions using the available behaviors shown on objects
- Don't give away puzzle solutions outright — nudge toward discovery
- Frame suggestions as natural language commands (e.g., "Try examining the desk" or "Ask the hacker about the key")
- Keep it brief — one line per suggestion
"""

HELP_TEXT = """Available commands:
  /help, /h, /?     Show this help
  /hint             Get suggestions for what to try next
  /look, /l         Show current room
  /save [slot]      Save game (default slot: "default")
  /load [slot]      Load game
  /saves            List saved games
  /debug [on|off]   Toggle debug mode, or show context
  /state, /s        Show current game state
  /history          Show turn history
  /kg [entity|map]  Query knowledge graph
  /eval <expr>      Evaluate a Grue expression
  /clear            Clear screen
  /reset            Restart game
  /quit, /q         Quit game"""


def handle_command(
    command: str,
    session: "GameSession",
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
            from .agent import TurnRecord  # Local import to avoid circular dependency
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
        if arg.lower() == "on":
            session.debug = True
            result.blocks.append(SystemMessage(text="Debug mode: on"))
        elif arg.lower() == "off":
            session.debug = False
            result.blocks.append(SystemMessage(text="Debug mode: off"))
        elif arg == "":
            # No arg: toggle
            session.debug = not session.debug
            result.blocks.append(SystemMessage(text=f"Debug mode: {'on' if session.debug else 'off'}"))
        else:
            result.blocks.append(SystemMessage(text="Usage: /debug [on|off]"))

    elif cmd in ("state", "s"):
        context = session.format_debug_context()
        result.blocks.append(SystemMessage(text=context))

    elif cmd == "history":
        if not session.turn_history:
            result.blocks.append(SystemMessage(text="No turns yet."))
        else:
            lines = []
            for i, turn in enumerate(session.turn_history, 1):
                lines.append(f"{i}. [{turn.room}] {turn.player_command}")
                if turn.actions:
                    lines.append(f"   Actions: {', '.join(turn.actions)}")
            result.blocks.append(SystemMessage(text="\n".join(lines)))

    elif cmd == "hint":
        from .llm import LLMClient, LLMConfig

        state = get_game_state(session.runtime)
        state_context = state.to_context_string()

        history_lines = []
        if session.summaries:
            history_lines.append(f"Earlier: {session.summaries[-1]}")
        for turn in session.turn_history[-5:]:
            history_lines.append(turn.to_summary())
        history_text = "\n".join(history_lines) if history_lines else "(no history yet)"

        hint_model = os.getenv("GRUE_HINT_MODEL", "anthropic/claude-haiku-4-5-20251001")
        hint_llm = LLMClient(LLMConfig(
            model=hint_model,
            temperature=0.8,
            max_tokens=512,
        ))
        try:
            response = hint_llm.chat([
                {"role": "system", "content": HINT_PROMPT},
                {"role": "user", "content": f"{state_context}\n\n## Recent history\n{history_text}"},
            ])
            result.blocks.append(SystemMessage(text=response.content or "No hints available."))
        except Exception as e:
            result.blocks.append(SystemMessage(text=f"Error getting hints: {e}", level="error"))

    elif cmd == "kg":
        if not arg:
            # Default: show map + entities + recent history
            sections = [
                session.knowledge.map_summary(),
                session.knowledge.entities_summary(),
                session.knowledge.history(last_n=10),
            ]
            result.blocks.append(SystemMessage(text="\n\n".join(sections)))
        elif arg.lower() == "map":
            result.blocks.append(SystemMessage(text=session.knowledge.map_summary()))
        elif arg.startswith("@"):
            result.blocks.append(SystemMessage(text=session.knowledge.recall(arg)))
        else:
            result.blocks.append(SystemMessage(text=session.knowledge.search(arg)))

    elif cmd == "eval":
        if not arg:
            result.blocks.append(SystemMessage(text="Usage: /eval <grue-expression>"))
        else:
            try:
                expr = parse(arg)
                eval_result = session.evaluator.eval(expr)
                result.blocks.append(SystemMessage(text=f"=> {eval_result}"))
            except Exception as e:
                result.blocks.append(SystemMessage(text=f"Error: {e}", level="error"))

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
