"""
Simple terminal UI for Gnusto.

Uses Rich for formatting and blessed for terminal control.
In interactive mode, pins the room header at the top with a
scrolling narrative area below.

Features:
- Pinned room state (interactive mode)
- Natural scrolling for narrative
- Styled dialogue and @references
- Graceful degradation for non-interactive terminals
"""

import re
import sys
from rich.console import Console
from rich.theme import Theme
from rich.text import Text
from rich.rule import Rule
from blessed import Terminal

from grue.save import save_game, load_game, list_saves

from .agent import GameSession, TurnRecord
from .state import get_game_state


# Regex to find @references like @hacker, @master-key, etc.
REF_PATTERN = re.compile(r'@[\w-]+')

# Regex to find dialogue: @speaker: "text" or @speaker: 'text' or just "quoted text"
DIALOGUE_PATTERN = re.compile(r'(@[\w-]+:\s*)?"[^"]*"')


# Custom theme for game output
THEME = Theme({
    "room.name": "bold cyan",
    "room.desc": "",
    "room.nearby": "dim",
    "room.inventory": "dim",
    "command": "bold green",
    "action": "dim",
    "narrative": "",
    "dialogue": "italic yellow",
    "thought": "dim italic",
    "system": "dim",
    "error": "bold red",
    "warning": "yellow",
    "ref": "magenta",  # @references
})


def style_text(text: str) -> str:
    """Apply Rich markup for @references and dialogue quotes."""
    # Add newlines before @speaker: patterns (but not at start of text)
    # This separates dialogue from different speakers
    text = re.sub(r'(?<=\S)(\s*)(@[\w-]+:\s*")', r'\n\n\2', text)

    # Style quoted text (dialogue) - just the quoted part
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

    # Header sizing constraints
    MAX_HEADER_LINES = 12  # Maximum header height
    MIN_SCROLL_LINES = 5   # Minimum lines reserved for scroll area

    def __init__(self, game_path: str, debug: bool = False):
        self.game_path = game_path
        self.debug = debug
        self.session: GameSession | None = None

        # Terminal detection
        self.is_tty = sys.stdout.isatty()
        self.term = Terminal() if self.is_tty else None

        # Rich console - we'll manage output positioning ourselves in TTY mode
        self.console = Console(
            theme=THEME,
            force_terminal=None,
            highlight=False,
        )

        # Cache current room state for header
        self._header_lines: list[str] = []
        self._header_height = 4  # Initial height (room name + desc + separator + buffer)

        # Scrollback buffer for the narrative area
        self._scroll_buffer: list[str] = []  # All output lines (raw, with ANSI codes)
        self._scroll_offset = 0  # 0 = viewing bottom (live), >0 = viewing history
        self._max_scrollback = 1000  # Maximum lines to keep in buffer

    def _set_scroll_region(self, top: int, bottom: int) -> None:
        """Set terminal scroll region (1-indexed)."""
        if self.term:
            # DECSTBM - Set Top and Bottom Margins
            print(f"\033[{top};{bottom}r", end="", flush=True)

    def _reset_scroll_region(self) -> None:
        """Reset scroll region to full screen."""
        if self.term:
            print("\033[r", end="", flush=True)

    def _move_cursor(self, row: int, col: int = 1) -> None:
        """Move cursor to position (1-indexed)."""
        if self.term:
            print(f"\033[{row};{col}H", end="", flush=True)

    def _save_cursor(self) -> None:
        """Save cursor position."""
        if self.term:
            print("\033[s", end="", flush=True)

    def _restore_cursor(self) -> None:
        """Restore cursor position."""
        if self.term:
            print("\033[u", end="", flush=True)

    def _clear_line(self) -> None:
        """Clear the current line."""
        if self.term:
            print("\033[2K", end="", flush=True)

    def _style_dim(self, text: str) -> str:
        """Apply dim styling using blessed."""
        if self.term:
            return self.term.dim + text + self.term.normal
        return text

    def _style_bold_cyan(self, text: str) -> str:
        """Apply bold cyan styling using blessed."""
        if self.term:
            return self.term.bold_cyan(text)
        return text

    def _style_magenta(self, text: str) -> str:
        """Apply magenta styling using blessed."""
        if self.term:
            return self.term.magenta(text)
        return text

    def _style_yellow(self, text: str) -> str:
        """Apply yellow styling using blessed."""
        if self.term:
            return self.term.yellow(text)
        return text

    def _style_green(self, text: str) -> str:
        """Apply green styling using blessed."""
        if self.term:
            return self.term.green(text)
        return text

    def _style_bright_white(self, text: str) -> str:
        """Apply bright white styling using blessed."""
        if self.term:
            return self.term.bright_white(text)
        return text

    def _style_bright_blue(self, text: str) -> str:
        """Apply bright blue styling using blessed."""
        if self.term:
            return self.term.bright_blue(text)
        return text

    def _draw_header(self) -> None:
        """Draw the pinned header area with dynamic height."""
        if not self.term or not self.session:
            return

        state = get_game_state(self.session.runtime)

        # Build all header content lines
        lines = []

        # Room name (bold cyan)
        if state.vehicle:
            header = f"{state.room_name} ({state.vehicle[1]} {state.vehicle[0]})"
        else:
            header = state.room_name
        lines.append(self._style_bold_cyan(header))

        # Room description (truncate if needed)
        if state.room_description:
            desc = state.room_description
            max_width = self.term.width - 2
            if len(desc) > max_width * 2:
                desc = desc[:max_width * 2 - 3] + "..."
            lines.append(self._style_dim(desc))

        # Blank line before exits/inventory section
        if state.nearby_rooms or state.inventory:
            lines.append("")

        # Exits (yellow)
        if state.nearby_rooms:
            nearby_str = ", ".join(r.description for r in state.nearby_rooms)
            lines.append(self._style_yellow(f"Exits: {nearby_str}"))

        # Inventory (green)
        if state.inventory:
            inv_str = ", ".join(obj.description for obj in state.inventory)
            lines.append(self._style_green(f"Carrying: {inv_str}"))

        # Objects with fdesc (bright blue with @refs in magenta)
        objects_with_fdesc = [obj for obj in state.visible_objects if obj.fdesc]
        if objects_with_fdesc:
            lines.append("")  # Blank line before objects
            for obj in objects_with_fdesc:
                fdesc_styled = REF_PATTERN.sub(lambda m: self._style_magenta(m.group(0)), obj.fdesc)
                lines.append(self._style_bright_blue(fdesc_styled))

        # Calculate dynamic header height
        # Content + 1 for separator, capped by constraints
        max_allowed = min(self.MAX_HEADER_LINES, self.term.height - self.MIN_SCROLL_LINES)
        content_height = len(lines) + 1  # +1 for separator
        new_height = min(content_height, max_allowed)

        # If header height changed, update scroll region
        if new_height != self._header_height:
            old_height = self._header_height
            self._header_height = new_height

            # Clear old header area if shrinking
            if new_height < old_height:
                for i in range(new_height, old_height):
                    self._move_cursor(i + 1)
                    self._clear_line()

            # Update scroll region
            self._set_scroll_region(self._header_height + 1, self.term.height)

        # Truncate content if needed (leaving room for separator)
        lines = lines[:self._header_height - 1]

        # Add separator as last line
        lines.append(self._style_dim("─" * self.term.width))

        # Draw header
        for i, line in enumerate(lines):
            self._move_cursor(i + 1)
            self._clear_line()
            print(line, end="", flush=True)

        self._header_lines = lines

    def _setup_screen(self) -> None:
        """Set up the screen layout for interactive mode."""
        if not self.term:
            return

        # Clear screen
        print(self.term.home + self.term.clear, end="", flush=True)

        # Draw initial header (this sets _header_height and scroll region)
        self._draw_header()

        # Move cursor to scroll region
        self._move_cursor(self._header_height + 1)

    def _scroll_height(self) -> int:
        """Get the height of the scroll region in lines."""
        if self.term:
            return self.term.height - self._header_height
        return 24  # Fallback

    def _add_to_scroll_buffer(self, text: str, style: str = "") -> str:
        """Add text to scroll buffer and return the formatted line."""
        styled_text = style_text(text) if self.is_tty else text
        if style:
            line = f"[{style}]{styled_text}[/]"
        else:
            line = styled_text

        # Split into individual lines and render each separately
        # This ensures buffer entries = screen lines for accurate scrolling
        from io import StringIO
        text_lines = text.split('\n') if text else ['']

        for text_line in text_lines:
            styled_line = style_text(text_line) if self.is_tty else text_line
            if style:
                markup = f"[{style}]{styled_line}[/]"
            else:
                markup = styled_line

            string_io = StringIO()
            temp_console = Console(file=string_io, force_terminal=True, highlight=False, theme=THEME, width=self.term.width if self.term else 80)
            temp_console.print(markup, end="")
            rendered = string_io.getvalue()
            self._scroll_buffer.append(rendered)

        # Trim buffer if too large
        if len(self._scroll_buffer) > self._max_scrollback:
            self._scroll_buffer = self._scroll_buffer[-self._max_scrollback:]

        return line

    def _render_scroll_region(self) -> None:
        """Re-render the visible portion of the scroll buffer."""
        if not self.term:
            return

        height = self._scroll_height()
        total_lines = len(self._scroll_buffer)

        # Calculate which lines to show
        if self._scroll_offset == 0:
            # At bottom - show last 'height' lines
            start = max(0, total_lines - height)
            end = total_lines
        else:
            # Scrolled up - show lines ending at offset from bottom
            end = max(0, total_lines - self._scroll_offset)
            start = max(0, end - height)

        visible_lines = self._scroll_buffer[start:end]

        # Calculate vertical offset to anchor content at bottom of scroll region
        empty_rows = max(0, height - len(visible_lines))

        # Clear and redraw the scroll area using direct cursor addressing
        # (no need to modify scroll region - cursor moves work regardless)
        for i in range(height):
            row = self._header_height + 1 + i
            # Direct cursor move and clear
            print(f"\033[{row};1H\033[2K", end="", flush=True)
            # Draw content anchored to bottom
            content_idx = i - empty_rows
            if 0 <= content_idx < len(visible_lines):
                print(visible_lines[content_idx], end="", flush=True)

        # Show scroll indicator - debug version shows all info
        total = len(self._scroll_buffer)
        max_off = max(0, total - height)
        if self._scroll_offset > 0:
            indicator = f" ↑{self._scroll_offset}/{max_off} [{total}L] "
            style = self.term.reverse
        else:
            indicator = f" [{total}L/{height}H] "
            style = self.term.dim
        row = self._header_height + 1
        col = max(1, self.term.width - len(indicator))
        print(f"\033[{row};{col}H", end="", flush=True)
        print(style + indicator + self.term.normal, end="", flush=True)

    def _scroll_up(self, lines: int = 0) -> None:
        """Scroll up (view older content). Default is half a page."""
        if not self._scroll_buffer:
            return
        if lines == 0:
            lines = max(1, self._scroll_height() // 2)
        # Max offset: can scroll until oldest content fills the screen
        max_offset = max(0, len(self._scroll_buffer) - self._scroll_height())
        if max_offset == 0:
            # All content fits on screen, nothing to scroll
            self._render_scroll_region()  # Still render to show indicator
            return
        self._scroll_offset = min(self._scroll_offset + lines, max_offset)
        self._render_scroll_region()

    def _scroll_down(self, lines: int = 0) -> None:
        """Scroll down (view newer content). Default is half a page."""
        if lines == 0:
            lines = max(1, self._scroll_height() // 2)
        self._scroll_offset = max(0, self._scroll_offset - lines)
        self._render_scroll_region()

    def _scroll_to_bottom(self) -> None:
        """Scroll to the bottom (live view)."""
        self._scroll_offset = 0
        self._render_scroll_region()

    def _print_in_scroll_region(self, text: str, style: str = "") -> None:
        """Print text in the scroll region (or normally if not TTY)."""
        if self.is_tty and self.term:
            # Add to buffer
            line = self._add_to_scroll_buffer(text, style)

            # If viewing history, don't print live - just update buffer
            # User will see it when they scroll back to bottom
            if self._scroll_offset > 0:
                return

            # Print normally (terminal auto-scrolls within region)
            self.console.print(line)
        else:
            # Non-TTY: just print
            if style:
                self.console.print(f"[{style}]{text}[/]")
            else:
                self.console.print(text)

    def _print_room_state(self) -> None:
        """Print or update room state display."""
        if self.is_tty and self.term:
            # Update pinned header (cursor will be moved temporarily)
            self._draw_header()
            # Move cursor back to bottom of scroll region for continued output
            # Position at bottom so new content appears at the end
            self._move_cursor(self.term.height, 1)
        else:
            # Non-TTY: print inline
            if not self.session:
                return
            state = get_game_state(self.session.runtime)
            if state.vehicle:
                header = f"{state.room_name} ({state.vehicle[1]} {state.vehicle[0]})"
            else:
                header = state.room_name
            self.console.print(f"\n[room.name]{header}[/]")
            if state.room_description:
                self.console.print(f"[room.desc]{state.room_description}[/]")
            # Exits and inventory before objects (consistent with TTY header)
            if state.nearby_rooms:
                nearby_str = ", ".join(r.description for r in state.nearby_rooms)
                self.console.print(f"[room.nearby]Nearby: {nearby_str}[/]")
            if state.inventory:
                inv_str = ", ".join(obj.description for obj in state.inventory)
                self.console.print(f"[room.inventory]Carrying: {inv_str}[/]")
            objects_with_fdesc = [obj for obj in state.visible_objects if obj.fdesc]
            if objects_with_fdesc:
                self.console.print()
                for obj in objects_with_fdesc:
                    self.console.print(f"[room.desc]{style_text(obj.fdesc)}[/]")
            self.console.print()

    def _print_action(self, result: str) -> None:
        """Print an action result (streaming callback)."""
        self._print_in_scroll_region(result, "action")
        self._print_in_scroll_region("")  # Blank line after each action

    def _print_narrative(self, text: str) -> None:
        """Print narrative response with dialogue styling."""
        if not text:
            return
        # Style the text - references will be styled by _print_in_scroll_region
        self._print_in_scroll_region(text, "narrative")

    def _handle_slash_command(self, command: str) -> bool:
        """Handle slash commands. Returns False to quit."""
        parts = command[1:].split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("help", "h", "?"):
            self._print_in_scroll_region("Commands: /save [slot], /load [slot], /saves, /debug, /quit", "system")
            self._print_in_scroll_region("Scrollback: PgUp/PgDn to scroll, Home/End for top/bottom, Esc to return", "system")

        elif cmd == "save":
            slot = arg or "default"
            if self.session:
                try:
                    path = save_game(self.session.runtime, slot, self.session.turn_history)
                    self._print_in_scroll_region(f"Game saved to {path}", "system")
                except Exception as e:
                    self._print_in_scroll_region(f"Error saving: {e}", "error")

        elif cmd == "load":
            slot = arg or "default"
            if self.session:
                try:
                    history_data, warnings = load_game(self.session.runtime, slot)
                    for w in warnings:
                        self._print_in_scroll_region(f"Warning: {w}", "warning")
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
                    self._print_in_scroll_region(f"Game loaded ({len(self.session.turn_history)} turns)", "system")
                    self._print_room_state()
                except FileNotFoundError:
                    self._print_in_scroll_region(f"No save found for slot '{slot}'", "error")
                except Exception as e:
                    self._print_in_scroll_region(f"Error loading: {e}", "error")

        elif cmd == "saves":
            if self.session:
                game_name = self.session.runtime.world.name or "unknown"
                saves = list_saves(game_name)
                if not saves:
                    self._print_in_scroll_region("No saves found.", "system")
                else:
                    self._print_in_scroll_region("Available saves:", "system")
                    for slot, timestamp, _ in saves:
                        self._print_in_scroll_region(f"  {slot}: {timestamp}", "system")

        elif cmd in ("debug", "d"):
            if self.session:
                context = self.session.format_debug_context()
                self._print_in_scroll_region("─── Debug Context ───", "system")
                self._print_in_scroll_region(context, "system")
                self._print_in_scroll_region("─────────────────────", "system")

        elif cmd in ("quit", "q"):
            return False

        else:
            self._print_in_scroll_region(f"Unknown command: /{cmd}", "system")

        return True

    def _read_input(self, prompt: str = "> ") -> str | None:
        """Read user input with support for Page Up/Down scrolling.

        Returns the input string, or None if EOF/interrupt.
        """
        if not self.is_tty or not self.term:
            # Fallback to regular input for non-TTY
            try:
                return input(prompt)
            except (EOFError, KeyboardInterrupt):
                return None

        # Show prompt
        print(prompt, end="", flush=True)

        input_buffer = ""
        cursor_pos = 0

        with self.term.cbreak():
            while True:
                key = self.term.inkey(timeout=None)

                if key.code == self.term.KEY_PGUP:
                    # Page Up - scroll back in history
                    self._scroll_up()
                    # Redraw header (may have been corrupted) and prompt
                    self._draw_header()
                    self._move_cursor(self.term.height)
                    self._clear_line()
                    print(prompt + input_buffer, end="", flush=True)

                elif key.code == self.term.KEY_PGDOWN:
                    # Page Down - scroll forward
                    self._scroll_down()
                    # Redraw header and prompt
                    self._draw_header()
                    self._move_cursor(self.term.height)
                    self._clear_line()
                    print(prompt + input_buffer, end="", flush=True)

                elif key.code == self.term.KEY_HOME:
                    # Home - scroll to top of buffer (show oldest content)
                    if self._scroll_buffer:
                        self._scroll_offset = max(0, len(self._scroll_buffer) - self._scroll_height())
                        self._render_scroll_region()
                    # Redraw header and prompt
                    self._draw_header()
                    self._move_cursor(self.term.height)
                    self._clear_line()
                    print(prompt + input_buffer, end="", flush=True)

                elif key.code == self.term.KEY_END:
                    # End - scroll to bottom (live)
                    self._scroll_to_bottom()
                    # Redraw header and prompt
                    self._draw_header()
                    self._move_cursor(self.term.height)
                    self._clear_line()
                    print(prompt + input_buffer, end="", flush=True)

                elif key.code == self.term.KEY_ENTER or key == "\n" or key == "\r":
                    # Enter - submit input
                    # Scroll to bottom first if viewing history
                    if self._scroll_offset > 0:
                        self._scroll_to_bottom()
                    print()  # Newline after input
                    return input_buffer

                elif key.code == self.term.KEY_BACKSPACE or key == "\x7f" or key == "\b":
                    # Backspace
                    if input_buffer:
                        input_buffer = input_buffer[:-1]
                        # Clear and redraw the line
                        print("\b \b", end="", flush=True)

                elif key.code == self.term.KEY_DELETE:
                    # Delete key - same as backspace for simplicity
                    if input_buffer:
                        input_buffer = input_buffer[:-1]
                        print("\b \b", end="", flush=True)

                elif key == "\x03":  # Ctrl+C
                    return None

                elif key == "\x04":  # Ctrl+D (EOF)
                    return None

                elif key.code == self.term.KEY_ESCAPE:
                    # Escape - clear input or scroll to bottom
                    if self._scroll_offset > 0:
                        self._scroll_to_bottom()
                        self._draw_header()
                        self._move_cursor(self.term.height)
                        self._clear_line()
                        print(prompt + input_buffer, end="", flush=True)
                    elif input_buffer:
                        input_buffer = ""
                        self._move_cursor(self.term.height)
                        self._clear_line()
                        print(prompt, end="", flush=True)

                elif not key.is_sequence and key.isprintable():
                    # Regular character
                    input_buffer += key
                    print(key, end="", flush=True)

    def run(self) -> None:
        """Run the game loop."""
        # Show loading message (will be visible in non-TTY mode)
        if not self.is_tty:
            self.console.print(f"[system]Loading game: {self.game_path}[/]")
            if self.debug:
                self.console.print("[system]Debug mode enabled[/]")

        self.session = GameSession.from_game_file(self.game_path, debug=self.debug)

        # Set up screen for interactive mode
        if self.is_tty and self.term:
            self._setup_screen()
            # Position cursor at bottom of scroll region so content starts there
            self._move_cursor(self.term.height, 1)
        else:
            self.console.print()
            self.console.print(Rule("Game Start"))

        # Show intro in the scroll region (at bottom in TTY mode)
        if self.session.runtime.world.intro:
            self._print_in_scroll_region(self.session.runtime.world.intro)
            self._print_in_scroll_region("")

        # In non-TTY mode, show room state inline
        if not self.is_tty:
            self._print_room_state()

        self._print_in_scroll_region("Type commands in natural language. /help for commands. PgUp/PgDn to scroll.", "system")
        self._print_in_scroll_region("")

        try:
            # Main loop
            while True:
                user_input = self._read_input("> ")

                if user_input is None:
                    # EOF or interrupt
                    self._print_in_scroll_region("")
                    self._print_in_scroll_region("Goodbye!", "system")
                    break

                user_input = user_input.strip()
                if not user_input:
                    continue

                # Slash commands
                if user_input.startswith("/"):
                    if not self._handle_slash_command(user_input):
                        self._print_in_scroll_region("Goodbye!", "system")
                        break
                    continue

                # Legacy quit
                if user_input.lower() in ("quit", "exit", "q"):
                    self._print_in_scroll_region("Goodbye!", "system")
                    break

                # Replace the plain input line with styled version
                if self.is_tty and self.term:
                    # Move up, clear line, print styled
                    print("\033[A\033[2K", end="", flush=True)
                self._print_in_scroll_region(f"> {user_input}", "command")
                self._print_in_scroll_region("")

                # Process command
                response_text, results = self.session.process_input(
                    user_input,
                    on_action=self._print_action
                )

                # Show narrative response
                self._print_narrative(response_text)
                self._print_in_scroll_region("")

                # Update room state display
                self._print_room_state()

        finally:
            # Cleanup: reset scroll region
            if self.is_tty and self.term:
                self._reset_scroll_region()
                self._move_cursor(self.term.height)
                print()  # Ensure we end on a new line


def run_tui(game_path: str, debug: bool = False) -> None:
    """Run the simple TUI."""
    tui = SimpleTUI(game_path, debug=debug)
    tui.run()
