"""
Textual-based TUI for Frotz LM.

A fullscreen terminal interface with:
- Single main game view (room description, narrative log)
- Input: natural language command entry
- Debug screen: LLM context (press 'd' to view, escape to return)
- Keyboard shortcuts for common actions

Designed to work well at any terminal size (80x24 and up).
"""

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Static, RichLog

from .agent import GameSession
from .state import get_game_state


class DebugScreen(ModalScreen):
    """Full-screen debug view showing LLM context."""

    BINDINGS = [
        Binding("escape", "dismiss", "Back"),
        Binding("ctrl+d", "dismiss", "Back"),
        Binding("q", "quit_app", "Quit"),
    ]

    CSS = """
    DebugScreen {
        align: center middle;
    }

    #debug-container {
        width: 100%;
        height: 100%;
        border: solid yellow;
        padding: 1;
    }

    #debug-header {
        text-style: bold;
        color: yellow;
        margin-bottom: 1;
    }

    #debug-content {
        color: grey;  /* Explicit color, not Textual design token */
    }
    """

    def __init__(self, context: str):
        super().__init__()
        self.context = context

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="debug-container"):
            yield Static("LLM Context (press d or escape to return)", id="debug-header")
            yield Static(self.context, id="debug-content")

    def action_quit_app(self) -> None:
        """Quit the application."""
        self.app.exit()


class FrotzApp(App):
    """Frotz LM TUI application."""

    # Disable default Textual chrome
    ENABLE_COMMAND_PALETTE = False

    CSS = """
    /* Room panel: fixed height, bottom border only */
    #room-panel {
        height: auto;
        border-bottom: solid grey;
        padding: 0 1;
    }

    #room-header {
        text-style: bold;
        color: cyan;
        margin-bottom: 1;
    }

    #room-description {
    }

    /* Narrative panel: fills remaining space, bottom border only */
    #narrative {
        height: 1fr;
        border-bottom: solid grey;
        padding: 0 1;
        overflow-x: hidden;
    }

    /* Input at bottom, no extra margins */
    Input {
        dock: bottom;
        margin: 0;
    }
    """

    # Bindings hidden from display (no footer)
    BINDINGS = [
        Binding("ctrl+d", "show_debug", "Debug", show=False),
        Binding("q", "quit", "Quit", show=False),
        Binding("escape", "focus_input", "Input", show=False),
    ]

    def __init__(self, game_path: str, debug: bool = False):
        super().__init__()
        self.game_path = game_path
        self.start_debug = debug
        self.session: GameSession | None = None

    def compose(self) -> ComposeResult:
        # Room panel - auto-height, non-scrolling
        with Vertical(id="room-panel"):
            yield Static(id="room-header")
            yield Static(id="room-description")
        # Narrative panel - RichLog handles its own scrolling
        yield RichLog(id="narrative", wrap=True, highlight=False, markup=True)
        yield Input(placeholder="What do you do?")

    def on_mount(self) -> None:
        """Initialize game session on mount."""
        self.session = GameSession.from_game_file(self.game_path, debug=self.start_debug)
        self.title = f"Frotz LM - {self.game_path}"

        self._update_display()
        self.query_one(Input).focus()

    def _update_display(self) -> None:
        """Update game display with current state."""
        if not self.session:
            return

        state = get_game_state(self.session.runtime)

        # Update room header
        header = self.query_one("#room-header", Static)
        if state.vehicle:
            header.update(f"{state.room_name} ({state.vehicle[1]} {state.vehicle[0]})")
        else:
            header.update(state.room_name)

        # Update room description
        desc_lines = [state.room_description]

        # Object listings (visually separated)
        objects_with_fdesc = [obj for obj in state.visible_objects if obj.fdesc]
        if objects_with_fdesc:
            desc_lines.append("")  # Blank line separator
            for obj in objects_with_fdesc:
                desc_lines.append(obj.fdesc)

        # Nearby rooms (player-friendly, deduplicated)
        if state.nearby_rooms:
            nearby_str = ", ".join(r.description for r in state.nearby_rooms)
            desc_lines.append(f"\n[dim]Nearby: {nearby_str}[/]")

        # Inventory
        if state.inventory:
            inv_str = ", ".join(obj.description for obj in state.inventory)
            desc_lines.append(f"[dim]Carrying: {inv_str}[/]")

        self.query_one("#room-description", Static).update("\n".join(desc_lines))

    def action_show_debug(self) -> None:
        """Show debug screen with full LLM context (history + state)."""
        if self.session:
            context = self.session.format_debug_context()
            self.push_screen(DebugScreen(context))

    def action_focus_input(self) -> None:
        """Focus the input field."""
        self.query_one(Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle player command submission."""
        command = event.value.strip()
        if not command:
            return

        # Clear input
        event.input.value = ""

        if command.lower() in ("quit", "exit", "q"):
            self.exit()
            return

        # Handle slash commands
        if command.startswith("/"):
            self._handle_slash_command(command)
            return

        # Add command to narrative
        narrative = self.query_one("#narrative", RichLog)
        narrative.write(f"[bold green]> {command}[/]")

        # Process in background to keep UI responsive
        self._process_command(command)

    def _handle_slash_command(self, command: str) -> None:
        """Handle slash commands in TUI."""
        narrative = self.query_one("#narrative", RichLog)
        parts = command[1:].split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""

        if cmd in ("help", "h", "?"):
            narrative.write("[dim]Commands: /help, /debug (or press d), /quit[/]")
        elif cmd in ("debug", "d"):
            self.action_show_debug()
        elif cmd in ("quit", "q"):
            self.exit()
        else:
            narrative.write(f"[dim]Unknown command: /{cmd}[/]")

    @work(thread=True)
    def _process_command(self, command: str) -> None:
        """Process command in background thread."""
        if not self.session:
            return

        # Stream action results as they happen
        def on_action(result: str) -> None:
            self.call_from_thread(self._stream_action, result)

        response_text, results = self.session.process_input(command, on_action=on_action)

        # Show final response (results already streamed)
        self.call_from_thread(self._show_response, response_text)

    def _stream_action(self, result: str) -> None:
        """Stream an action result to the narrative panel."""
        narrative = self.query_one("#narrative", RichLog)
        narrative.write(f"[dim]{result}[/]")

    def _show_response(self, response_text: str) -> None:
        """Show final response in narrative panel (action results already streamed)."""
        narrative = self.query_one("#narrative", RichLog)

        # Show narrative response
        if response_text:
            narrative.write(response_text)

        narrative.write("")  # Blank line

        # Update state display
        self._update_display()


def run_tui(game_path: str, debug: bool = False) -> None:
    """Run the Textual TUI."""
    app = FrotzApp(game_path, debug=debug)
    app.run()
