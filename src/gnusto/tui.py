"""
Textual-based TUI for Gnusto.

A fullscreen terminal interface with:
- Room panel: current location, room image, and visible objects
- Narrative panel: scrollable conversation history
- Input: natural language command entry (always focused)
- Debug screen: LLM context (F3 to toggle)

Keyboard shortcuts:
- F3: Toggle debug screen
- Up/Down, Ctrl+U/D: Scroll line by line
- PgUp/PgDn, Ctrl+B/F: Scroll by page

Designed to work well at any terminal size (80x24 and up).
"""

from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Static, RichLog

from grue.save import save_game, load_game, list_saves

from .agent import GameSession, TurnRecord
from .state import get_game_state

# Import textual-image for terminal image display (Kitty protocol)
# Detection must happen before Textual starts, so we check env vars
import os

HAS_IMAGE_SUPPORT = False
ImageWidget = None

try:
    # Check for Kitty terminal via environment variable
    if os.environ.get("KITTY_WINDOW_ID"):
        # Force TGP (Kitty graphics protocol) for Kitty terminal
        from textual_image.widget import TGPImage as ImageWidget
        HAS_IMAGE_SUPPORT = True
    else:
        # Use auto-detection for other terminals
        from textual_image.widget import Image as ImageWidget
        HAS_IMAGE_SUPPORT = True
except ImportError:
    pass


class DebugScreen(ModalScreen):
    """Full-screen debug view showing LLM context."""

    BINDINGS = [
        Binding("escape", "dismiss", "Back"),
        Binding("f3", "dismiss", "Back"),
        Binding("q", "quit_app", "Quit"),
    ]

    CSS = """
    DebugScreen {
        align: center middle;
    }

    #debug-container {
        width: 100%;
        height: 100%;
        padding: 1;
        scrollbar-size-vertical: 1;
        scrollbar-color: #333333;
        scrollbar-background: transparent;
    }

    #debug-header {
        text-style: bold;
        color: grey;
        border-bottom: solid grey;
        padding-bottom: 1;
        margin-bottom: 1;
    }

    #debug-content {
        color: grey;
    }
    """

    def __init__(self, context: str):
        super().__init__()
        self.context = context

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="debug-container"):
            yield Static("LLM Context (ESC to return)", id="debug-header")
            yield Static(self.context, id="debug-content")

    def action_quit_app(self) -> None:
        """Quit the application."""
        self.app.exit()


class GnustoApp(App):
    """Gnusto TUI application."""

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

    /* Horizontal layout for room content (image + description) */
    #room-content {
        height: auto;
    }

    #room-image {
        width: 24;
        height: 12;
        margin-right: 1;
    }

    /* Hide image container when no image */
    #room-image.hidden {
        display: none;
    }

    #room-text {
        width: 1fr;
    }

    #room-description {
        text-overflow: fold;
    }

    /* Narrative panel: fills remaining space, bottom border only */
    #narrative {
        height: 1fr;
        width: 100%;
        border-bottom: solid grey;
        padding: 0 1;
        overflow-x: hidden;
        scrollbar-visibility: hidden;
        text-overflow: fold;
    }

    /* Input at bottom - minimal styling, no border */
    Input {
        dock: bottom;
        margin: 0;
        border: none;
        padding: 0 1;
    }

    /* Remove focus highlight from input */
    Input:focus {
        border: none;
    }
    """

    # Bindings with priority=True to work even when input is focused
    BINDINGS = [
        Binding("f3", "show_debug", "Debug", show=False, priority=True),
        # Arrow keys and page keys for scrolling
        Binding("up", "scroll_up", "Scroll Up", show=False, priority=True),
        Binding("down", "scroll_down", "Scroll Down", show=False, priority=True),
        Binding("pageup", "page_up", "Page Up", show=False, priority=True),
        Binding("pagedown", "page_down", "Page Down", show=False, priority=True),
        # Emacs-style alternatives
        Binding("ctrl+u", "scroll_up", "Scroll Up", show=False, priority=True),
        Binding("ctrl+d", "scroll_down", "Scroll Down", show=False, priority=True),
        Binding("ctrl+b", "page_up", "Page Up", show=False, priority=True),
        Binding("ctrl+f", "page_down", "Page Down", show=False, priority=True),
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
            # Horizontal layout for image (optional) + description
            with Horizontal(id="room-content"):
                if HAS_IMAGE_SUPPORT:
                    yield ImageWidget(id="room-image", classes="hidden")
                yield Vertical(
                    Static(id="room-description"),
                    id="room-text",
                )
        # Narrative panel - RichLog handles its own scrolling
        yield RichLog(id="narrative", wrap=True, highlight=False, markup=True)
        yield Input(placeholder="What do you do?")

    def on_mount(self) -> None:
        """Initialize game session on mount."""
        self.session = GameSession.from_game_file(self.game_path, debug=self.start_debug)
        self.title = f"Gnusto - {self.game_path}"

        # Disable focus on narrative panel (input always gets focus)
        self.query_one("#narrative", RichLog).can_focus = False

        # Show intro text if available
        if self.session.runtime.world.intro:
            narrative = self.query_one("#narrative", RichLog)
            narrative.write(self.session.runtime.world.intro)
            narrative.write("")

        self._update_display()
        self.query_one(Input).focus()

    def _get_room_image_path(self, room_id: str) -> Path | None:
        """Find image for a room if one exists.

        Looks for images in: <game_path>/images/<room_id>.png
        Room IDs like @terminal-room become terminal-room.png
        """
        # Strip leading @ from room ID
        room_name = room_id.lstrip("@")
        image_path = Path(self.game_path) / "gfx" / f"{room_name}.png"
        if image_path.exists():
            return image_path
        # Also try .jpg
        image_path = image_path.with_suffix(".jpg")
        if image_path.exists():
            return image_path
        return None

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

        # Update room image if supported
        if HAS_IMAGE_SUPPORT:
            image_widget = self.query_one("#room-image", ImageWidget)
            image_path = self._get_room_image_path(state.room)
            if image_path:
                image_widget.image = str(image_path)
                image_widget.remove_class("hidden")
            else:
                image_widget.add_class("hidden")

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
        # Don't stack debug screens
        if isinstance(self.screen, DebugScreen):
            return
        if self.session:
            context = self.session.format_debug_context()
            self.push_screen(DebugScreen(context))

    def action_scroll_up(self) -> None:
        """Scroll narrative up a few lines."""
        self.query_one("#narrative", RichLog).scroll_up(animate=False)

    def action_scroll_down(self) -> None:
        """Scroll narrative down a few lines."""
        self.query_one("#narrative", RichLog).scroll_down(animate=False)

    def action_page_up(self) -> None:
        """Scroll narrative up a page."""
        self.query_one("#narrative", RichLog).scroll_page_up(animate=False)

    def action_page_down(self) -> None:
        """Scroll narrative down a page."""
        self.query_one("#narrative", RichLog).scroll_page_down(animate=False)

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
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("help", "h", "?"):
            narrative.write("[dim]Commands: /save, /load, /saves, /debug (F3), /quit | Scroll: Up/Down, PgUp/PgDn[/]")
        elif cmd == "save":
            slot = arg or "default"
            if self.session:
                try:
                    path = save_game(self.session.runtime, slot, self.session.turn_history)
                    narrative.write(f"[dim]Game saved to {path}[/]")
                except Exception as e:
                    narrative.write(f"[red]Error saving: {e}[/]")
        elif cmd == "load":
            slot = arg or "default"
            if self.session:
                try:
                    history_data, warnings = load_game(self.session.runtime, slot)
                    for w in warnings:
                        narrative.write(f"[yellow]Warning: {w}[/]")
                    # Restore turn history
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
                    narrative.write(f"[dim]Game loaded ({len(self.session.turn_history)} turns of history)[/]")
                    self._update_display()
                except FileNotFoundError:
                    narrative.write(f"[red]No save found for slot '{slot}'[/]")
                except Exception as e:
                    narrative.write(f"[red]Error loading: {e}[/]")
        elif cmd == "saves":
            if self.session:
                game_name = self.session.runtime.world.name or "unknown"
                saves = list_saves(game_name)
                if not saves:
                    narrative.write("[dim]No saves found.[/]")
                else:
                    narrative.write("[dim]Available saves:[/]")
                    for slot, timestamp, _ in saves:
                        narrative.write(f"[dim]  {slot}: {timestamp}[/]")
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
    app = GnustoApp(game_path, debug=debug)
    app.run()
