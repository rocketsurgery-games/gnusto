"""
Textual-based TUI for Frotz LM.

A fullscreen terminal interface with:
- Game panel: room description, object listings, narrative
- Input: natural language command entry
- Debug panel: LLM context (toggle-able)
- Keyboard shortcuts for common actions
"""

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Static, RichLog

from .agent import GameSession
from .state import get_game_state


class GamePanel(VerticalScroll):
    """Main game display panel - room description and narrative."""

    def compose(self) -> ComposeResult:
        yield Static(id="room-header")
        yield Static(id="room-description")
        yield RichLog(id="narrative", wrap=True, highlight=True, markup=True)


class DebugPanel(VerticalScroll):
    """Debug panel showing LLM context."""

    def compose(self) -> ComposeResult:
        yield Static("[bold]LLM Context[/]", id="debug-header")
        yield Static(id="debug-content")


class FrotzApp(App):
    """Frotz LM TUI application."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 1;
        grid-columns: 2fr 1fr;
    }

    Screen.hide-debug {
        grid-size: 1 1;
    }

    GamePanel {
        border: solid cyan;
        padding: 1;
    }

    DebugPanel {
        border: solid yellow;
        padding: 1;
    }

    .hide-debug DebugPanel {
        display: none;
    }

    #room-header {
        text-style: bold;
        color: cyan;
        margin-bottom: 1;
    }

    #room-description {
        margin-bottom: 1;
    }

    #narrative {
        border-top: solid dim;
        padding-top: 1;
        height: auto;
        max-height: 100%;
    }

    #debug-header {
        text-style: bold;
        color: yellow;
        margin-bottom: 1;
    }

    #debug-content {
        color: $text-muted;
    }

    Input {
        dock: bottom;
        margin: 1;
    }

    Footer {
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("d", "toggle_debug", "Debug"),
        Binding("q", "quit", "Quit"),
        Binding("escape", "focus_input", "Input", show=False),
    ]

    def __init__(self, game_path: str, debug: bool = False):
        super().__init__()
        self.game_path = game_path
        self.show_debug = debug
        self.session: GameSession | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield GamePanel()
            yield DebugPanel()
        yield Input(placeholder="What do you do?")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize game session on mount."""
        self.session = GameSession.from_game_file(self.game_path, debug=self.show_debug)
        self.title = f"Frotz LM - {self.game_path}"

        if not self.show_debug:
            self.add_class("hide-debug")

        self._update_display()
        self.query_one(Input).focus()

    def _update_display(self) -> None:
        """Update game and debug panels with current state."""
        if not self.session:
            return

        state = get_game_state(self.session.runtime)

        # Update room header
        header = self.query_one("#room-header", Static)
        if state.vehicle:
            header.update(f"{state.room} ({state.vehicle[1]} {state.vehicle[0]})")
        else:
            header.update(state.room)

        # Update room description with objects
        desc_lines = [state.room_description]
        for obj in state.visible_objects:
            if obj.fdesc:
                desc_lines.append(obj.fdesc)

        # Add exits
        if state.exits:
            exits_str = ", ".join(f"{d} → {dest}" for d, dest in state.exits.items())
            desc_lines.append(f"\n[dim]Exits: {exits_str}[/]")

        # Add inventory
        if state.inventory:
            inv_str = ", ".join(obj.description for obj in state.inventory)
            desc_lines.append(f"[dim]Carrying: {inv_str}[/]")

        self.query_one("#room-description", Static).update("\n".join(desc_lines))

        # Update debug panel
        if self.show_debug:
            context = state.to_context_string()
            self.query_one("#debug-content", Static).update(context)

    def action_toggle_debug(self) -> None:
        """Toggle debug panel visibility."""
        self.show_debug = not self.show_debug
        self.toggle_class("hide-debug")
        if self.show_debug:
            self._update_display()

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

        # Add command to narrative
        narrative = self.query_one("#narrative", RichLog)
        narrative.write(f"[bold green]> {command}[/]")

        # Process in background to keep UI responsive
        self._process_command(command)

    @work(thread=True)
    def _process_command(self, command: str) -> None:
        """Process command in background thread."""
        if not self.session:
            return

        response_text, results = self.session.process_input(command)

        # Update UI from main thread
        self.call_from_thread(self._show_response, response_text, results)

    def _show_response(self, response_text: str, results: list[str]) -> None:
        """Show response in narrative panel."""
        narrative = self.query_one("#narrative", RichLog)

        # Show action results
        for result in results:
            if result and result != "Done.":
                narrative.write(f"[dim]{result}[/]")

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
