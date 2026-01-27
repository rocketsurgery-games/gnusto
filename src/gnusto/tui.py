"""
Simple terminal UI for Gnusto.

Uses Rich for formatting. No scroll regions, no cursor manipulation,
just straightforward terminal output.
"""

import re
from pathlib import Path
from rich.console import Console
from rich.theme import Theme
from rich.rule import Rule

from grue.save import save_game, load_game, list_saves

from .agent import GameSession, TurnRecord
from .render import (
    ContentBlock, RoomEnter, ActionResult, Narrative, Image, SystemMessage,
    build_turn_output, build_room_block,
)
from .state import get_game_state


# Regex to find @references like @hacker, @master-key, etc.
REF_PATTERN = re.compile(r'@[\w-]+')


# Custom theme for game output
THEME = Theme({
    "room.name": "bold cyan",
    "room.desc": "",
    "room.exits": "dim yellow",
    "room.inventory": "dim green",
    "room.objects": "dim",
    "command": "bold green",
    "action": "dim",
    "narrative": "",
    "dialogue": "italic yellow",
    "system": "dim",
    "error": "bold red",
    "warning": "yellow",
    "ref": "magenta",
})


def style_text(text: str) -> str:
    """Apply Rich markup for @references and dialogue quotes."""
    # Add newlines before @speaker: patterns (but not at start of text)
    text = re.sub(r'(?<=\S)(\s*)(@[\w-]+:\s*")', r'\n\n\2', text)

    # Style quoted text (dialogue)
    def replace_quotes(match):
        return f"[dialogue]{match.group(0)}[/]"
    text = re.sub(r'"[^"]*"', replace_quotes, text)

    # Style @references in magenta
    def replace_ref(match):
        return f"[ref]{match.group(0)}[/]"
    text = REF_PATTERN.sub(replace_ref, text)

    return text


class SimpleTUI:
    """Simple terminal interface for Gnusto."""

    def __init__(self, game_path: str, debug: bool = False):
        self.game_path = game_path
        self.game_dir = Path(game_path).resolve()
        if self.game_dir.is_file():
            self.game_dir = self.game_dir.parent
        self.debug = debug
        self.session: GameSession | None = None
        self.console = Console(theme=THEME, highlight=False)
        self._last_room: str | None = None

    def render_block(self, block: ContentBlock) -> None:
        """Render a content block to the terminal."""
        if isinstance(block, RoomEnter):
            self.console.print()
            self.console.rule(style="dim")

            # Room name
            self.console.print(f"[room.name]{block.name}[/]")

            # Room description
            if block.description:
                self.console.print(f"[room.desc]{block.description}[/]")

            # Exits (just direction names)
            if block.exits:
                exits_str = ", ".join(block.exits)
                self.console.print(f"[room.exits]Exits: {exits_str}[/]")

            # Inventory
            if block.inventory:
                inv_str = ", ".join(block.inventory)
                self.console.print(f"[room.inventory]Carrying: {inv_str}[/]")

            # Objects
            if block.objects:
                obj_str = ", ".join(block.objects)
                self.console.print(f"[room.objects]You see: {obj_str}[/]")

            # Image (TUI just notes it exists)
            if block.image:
                self.console.print(f"[dim][Image: {Path(block.image).name}][/]")

            self.console.print()
            self._last_room = block.room_id

        elif isinstance(block, ActionResult):
            self.console.print(f"[action]{block.text}[/]")

        elif isinstance(block, Narrative):
            styled = style_text(block.text)
            self.console.print(f"[narrative]{styled}[/]")
            self.console.print()

        elif isinstance(block, Image):
            # TUI just notes the image
            self.console.print(f"[dim][Image: {Path(block.src).name}][/]")

        elif isinstance(block, SystemMessage):
            style = {
                "info": "system",
                "warning": "warning",
                "error": "error",
            }.get(block.level, "system")
            self.console.print(f"[{style}]{block.text}[/]")

    def _handle_slash_command(self, command: str) -> bool:
        """Handle slash commands. Returns False to quit."""
        parts = command[1:].split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("help", "h", "?"):
            self.render_block(SystemMessage("Commands: /save [slot], /load [slot], /saves, /look, /debug, /quit"))

        elif cmd == "save":
            slot = arg or "default"
            if self.session:
                try:
                    path = save_game(self.session.runtime, slot, self.session.turn_history)
                    self.render_block(SystemMessage(f"Game saved to {path}"))
                except Exception as e:
                    self.render_block(SystemMessage(f"Error saving: {e}", level="error"))

        elif cmd == "load":
            slot = arg or "default"
            if self.session:
                try:
                    history_data, warnings = load_game(self.session.runtime, slot)
                    for w in warnings:
                        self.render_block(SystemMessage(f"Warning: {w}", level="warning"))
                    self.session.turn_history.clear()
                    for turn_data in history_data:
                        turn = TurnRecord(
                            room=turn_data.get("room", ""),
                            player_command=turn_data.get("command", ""),
                            actions=turn_data.get("actions", []),
                            results=turn_data.get("results", []),
                            narrative=turn_data.get("narrative", ""),
                        )
                        self.session.turn_history.append(turn)
                    self.render_block(SystemMessage(f"Game loaded ({len(self.session.turn_history)} turns)"))
                    # Show current room state
                    state = get_game_state(self.session.runtime)
                    room_block = build_room_block(state, self.session.runtime, self.game_dir)
                    self.render_block(room_block)
                except FileNotFoundError:
                    self.render_block(SystemMessage(f"No save found for slot '{slot}'", level="error"))
                except Exception as e:
                    self.render_block(SystemMessage(f"Error loading: {e}", level="error"))

        elif cmd == "saves":
            if self.session:
                game_name = self.session.runtime.world.name or "unknown"
                saves = list_saves(game_name)
                if not saves:
                    self.render_block(SystemMessage("No saves found."))
                else:
                    self.render_block(SystemMessage("Available saves:"))
                    for slot, timestamp, _ in saves:
                        self.render_block(SystemMessage(f"  {slot}: {timestamp}"))

        elif cmd in ("look", "l"):
            if self.session:
                state = get_game_state(self.session.runtime)
                room_block = build_room_block(state, self.session.runtime, self.game_dir)
                self.render_block(room_block)

        elif cmd in ("debug", "d"):
            if self.session:
                context = self.session.format_debug_context()
                self.render_block(SystemMessage("─── Debug Context ───"))
                self.render_block(SystemMessage(context))
                self.render_block(SystemMessage("─────────────────────"))

        elif cmd in ("quit", "q"):
            return False

        else:
            self.render_block(SystemMessage(f"Unknown command: /{cmd}"))

        return True

    def run(self) -> None:
        """Run the game loop."""
        self.render_block(SystemMessage(f"Loading game: {self.game_path}"))
        if self.debug:
            self.render_block(SystemMessage("Debug mode enabled"))

        self.session = GameSession.from_game_file(self.game_path, debug=self.debug)

        self.console.print()
        self.console.print(Rule("Game Start"))

        # Show intro
        if self.session.runtime.world.intro:
            self.render_block(Narrative(self.session.runtime.world.intro))

        # Show initial room state
        state = get_game_state(self.session.runtime)
        room_block = build_room_block(state, self.session.runtime, self.game_dir)
        self.render_block(room_block)

        self.render_block(SystemMessage("Type commands in natural language. /help for commands."))
        self.console.print()

        # Main loop
        while True:
            try:
                user_input = input("> ")
            except (EOFError, KeyboardInterrupt):
                self.console.print()
                self.render_block(SystemMessage("Goodbye!"))
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            # Slash commands
            if user_input.startswith("/"):
                if not self._handle_slash_command(user_input):
                    self.render_block(SystemMessage("Goodbye!"))
                    break
                continue

            # Legacy quit
            if user_input.lower() in ("quit", "exit", "q"):
                self.render_block(SystemMessage("Goodbye!"))
                break

            # Echo command
            self.console.print(f"[command]> {user_input}[/]")
            self.console.print()

            # Track previous room for change detection
            previous_room = self._last_room

            # Collect action results for building blocks
            action_results: list[str] = []

            def on_action(result: str) -> None:
                action_results.append(result)
                # Stream action results as they happen
                if result and result != "Done.":
                    self.render_block(ActionResult(text=result))

            # Process command
            response_text, _ = self.session.process_input(user_input, on_action=on_action)

            # Build and render content blocks for the turn
            state = get_game_state(self.session.runtime)
            blocks = build_turn_output(
                action_results=action_results,
                narrative=response_text,
                state=state,
                runtime=self.session.runtime,
                previous_room=previous_room,
                game_dir=self.game_dir,
            )

            # Render blocks (skip ActionResults - already streamed)
            for block in blocks:
                if not isinstance(block, ActionResult):
                    self.render_block(block)


def run_tui(game_path: str, debug: bool = False) -> None:
    """Run the simple TUI."""
    tui = SimpleTUI(game_path, debug=debug)
    tui.run()
