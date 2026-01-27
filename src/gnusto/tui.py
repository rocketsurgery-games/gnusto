"""
Simple terminal UI for Gnusto.

Uses Rich for formatting. No scroll regions, no cursor manipulation,
just straightforward terminal output.
"""

import re
from rich.console import Console
from rich.theme import Theme
from rich.rule import Rule

from grue.save import save_game, load_game, list_saves

from .agent import GameSession, TurnRecord
from .state import get_game_state


# Regex to find @references like @hacker, @master-key, etc.
REF_PATTERN = re.compile(r'@[\w-]+')


# Custom theme for game output
THEME = Theme({
    "room.name": "bold cyan",
    "room.desc": "",
    "room.nearby": "dim",
    "room.inventory": "dim green",
    "command": "bold green",
    "action": "dim",
    "narrative": "",
    "dialogue": "italic yellow",
    "system": "dim",
    "error": "bold red",
    "warning": "yellow",
    "ref": "magenta",
    "object": "bright_blue",
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
        self.debug = debug
        self.session: GameSession | None = None
        self.console = Console(theme=THEME, highlight=False)
        self._last_room: str | None = None

    def _print_room_state(self, force: bool = False) -> None:
        """Print room state. Only prints if room changed or forced."""
        if not self.session:
            return

        state = get_game_state(self.session.runtime)

        # Skip if room hasn't changed (unless forced)
        if not force and state.room == self._last_room:
            return
        self._last_room = state.room

        self.console.print()
        self.console.rule(style="dim")

        # Room name
        if state.vehicle:
            header = f"{state.room_name} ({state.vehicle[1]} {state.vehicle[0]})"
        else:
            header = state.room_name
        self.console.print(f"[room.name]{header}[/]")

        # Room description
        if state.room_description:
            self.console.print(f"[room.desc]{state.room_description}[/]")

        # Exits
        if state.nearby_rooms:
            nearby_str = ", ".join(r.description for r in state.nearby_rooms)
            self.console.print(f"[room.nearby]Exits: {nearby_str}[/]")

        # Inventory
        if state.inventory:
            inv_str = ", ".join(obj.description for obj in state.inventory)
            self.console.print(f"[room.inventory]Carrying: {inv_str}[/]")

        # Objects with fdesc
        objects_with_fdesc = [obj for obj in state.visible_objects if obj.fdesc]
        if objects_with_fdesc:
            self.console.print()
            for obj in objects_with_fdesc:
                styled = style_text(obj.fdesc)
                self.console.print(f"[object]{styled}[/]")

        self.console.print()

    def _print_action(self, result: str) -> None:
        """Print an action result (streaming callback)."""
        self.console.print(f"[action]{result}[/]")

    def _print_narrative(self, text: str) -> None:
        """Print narrative response with dialogue styling."""
        if not text:
            return
        styled = style_text(text)
        self.console.print(f"[narrative]{styled}[/]")

    def _handle_slash_command(self, command: str) -> bool:
        """Handle slash commands. Returns False to quit."""
        parts = command[1:].split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("help", "h", "?"):
            self.console.print("[system]Commands: /save [slot], /load [slot], /saves, /look, /debug, /quit[/]")

        elif cmd == "save":
            slot = arg or "default"
            if self.session:
                try:
                    path = save_game(self.session.runtime, slot, self.session.turn_history)
                    self.console.print(f"[system]Game saved to {path}[/]")
                except Exception as e:
                    self.console.print(f"[error]Error saving: {e}[/]")

        elif cmd == "load":
            slot = arg or "default"
            if self.session:
                try:
                    history_data, warnings = load_game(self.session.runtime, slot)
                    for w in warnings:
                        self.console.print(f"[warning]Warning: {w}[/]")
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
                    self.console.print(f"[system]Game loaded ({len(self.session.turn_history)} turns)[/]")
                    self._last_room = None  # Force room display
                    self._print_room_state(force=True)
                except FileNotFoundError:
                    self.console.print(f"[error]No save found for slot '{slot}'[/]")
                except Exception as e:
                    self.console.print(f"[error]Error loading: {e}[/]")

        elif cmd == "saves":
            if self.session:
                game_name = self.session.runtime.world.name or "unknown"
                saves = list_saves(game_name)
                if not saves:
                    self.console.print("[system]No saves found.[/]")
                else:
                    self.console.print("[system]Available saves:[/]")
                    for slot, timestamp, _ in saves:
                        self.console.print(f"[system]  {slot}: {timestamp}[/]")

        elif cmd in ("look", "l"):
            self._print_room_state(force=True)

        elif cmd in ("debug", "d"):
            if self.session:
                context = self.session.format_debug_context()
                self.console.print("[system]─── Debug Context ───[/]")
                self.console.print(f"[system]{context}[/]")
                self.console.print("[system]─────────────────────[/]")

        elif cmd in ("quit", "q"):
            return False

        else:
            self.console.print(f"[system]Unknown command: /{cmd}[/]")

        return True

    def run(self) -> None:
        """Run the game loop."""
        self.console.print(f"[system]Loading game: {self.game_path}[/]")
        if self.debug:
            self.console.print("[system]Debug mode enabled[/]")

        self.session = GameSession.from_game_file(self.game_path, debug=self.debug)

        self.console.print()
        self.console.print(Rule("Game Start"))

        # Show intro
        if self.session.runtime.world.intro:
            self.console.print(self.session.runtime.world.intro)

        # Show initial room state
        self._print_room_state(force=True)

        self.console.print("[system]Type commands in natural language. /help for commands.[/]")
        self.console.print()

        # Main loop
        while True:
            try:
                user_input = input("> ")
            except (EOFError, KeyboardInterrupt):
                self.console.print()
                self.console.print("[system]Goodbye![/]")
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            # Slash commands
            if user_input.startswith("/"):
                if not self._handle_slash_command(user_input):
                    self.console.print("[system]Goodbye![/]")
                    break
                continue

            # Legacy quit
            if user_input.lower() in ("quit", "exit", "q"):
                self.console.print("[system]Goodbye![/]")
                break

            # Echo command
            self.console.print(f"[command]> {user_input}[/]")
            self.console.print()

            # Process command
            response_text, results = self.session.process_input(
                user_input,
                on_action=self._print_action
            )

            # Show narrative response
            self._print_narrative(response_text)
            self.console.print()

            # Update room state if we moved
            self._print_room_state()


def run_tui(game_path: str, debug: bool = False) -> None:
    """Run the simple TUI."""
    tui = SimpleTUI(game_path, debug=debug)
    tui.run()
