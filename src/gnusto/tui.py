"""
Simple terminal UI for Gnusto.

Uses Rich for formatting. No scroll regions, no cursor manipulation,
just straightforward terminal output.
"""

import re
from pathlib import Path
from rich.console import Console
from rich.text import Text
from rich.rule import Rule

from .agent import GameSession
from .commands import handle_command
from .llm import ImageRequest
from .render import (
    ContentBlock, RoomEnter, ActionResult, Narrative, Image, SystemMessage,
    build_room_block,
)
from .state import get_game_state


# Regex patterns for styling
REF_PATTERN = re.compile(r'@[\w-]+')
QUOTE_PATTERN = re.compile(r'"[^"]*"')
SPEAKER_PATTERN = re.compile(r'(?<=\S)(\s*)(@[\w-]+:\s*")')


def style_narrative(text: str) -> Text:
    """Apply Rich styles to narrative text using Text object (no markup parsing).

    This approach is immune to any content in the text - no escaping needed.
    """
    # Add newlines before @speaker: patterns (but not at start of text)
    text = SPEAKER_PATTERN.sub(r'\n\n\2', text)

    # Create a Text object with base italic style
    styled = Text(text, style="italic")

    # Apply dialogue style to quoted text
    for match in QUOTE_PATTERN.finditer(text):
        styled.stylize("italic yellow", match.start(), match.end())

    # Apply ref style to @references
    for match in REF_PATTERN.finditer(text):
        styled.stylize("magenta", match.start(), match.end())

    return styled


class SimpleTUI:
    """Simple terminal interface for Gnusto."""

    def __init__(self, game_path: str, debug: bool = False):
        self.game_path = game_path
        self.game_dir = Path(game_path).resolve()
        if self.game_dir.is_file():
            self.game_dir = self.game_dir.parent
        self.debug = debug
        self.session: GameSession | None = None
        self.console = Console(highlight=False)
        self._last_room: str | None = None

    def render_block(self, block: ContentBlock) -> None:
        """Render a content block to the terminal.

        Uses Rich Text objects instead of markup strings to avoid parsing issues
        with LLM-generated content that may contain bracket characters.
        """
        if isinstance(block, RoomEnter):
            self.console.print()
            self.console.rule(style="dim")

            # Room name
            self.console.print(Text(block.name, style="bold cyan"))

            # Room description
            if block.description:
                self.console.print(Text(block.description))

            # Exits (just direction names)
            if block.exits:
                exits_str = ", ".join(block.exits)
                self.console.print(Text(f"Exits: {exits_str}", style="dim yellow"))

            # Inventory
            if block.inventory:
                inv_str = ", ".join(block.inventory)
                self.console.print(Text(f"Carrying: {inv_str}", style="dim green"))

            # Objects
            if block.objects:
                obj_str = ", ".join(block.objects)
                self.console.print(Text(f"You see: {obj_str}", style="dim"))

            # Image (TUI just notes it exists)
            if block.image:
                self.console.print(Text(f"[Image: {Path(block.image).name}]", style="dim"))

            self.console.print()
            self._last_room = block.room_id

        elif isinstance(block, ActionResult):
            self.console.print(Text(block.text, style="dim"))

        elif isinstance(block, Narrative):
            styled = style_narrative(block.text)
            self.console.print(styled)
            self.console.print()

        elif isinstance(block, Image):
            # TUI just notes the image
            self.console.print(Text(f"[Image: {Path(block.src).name}]", style="dim"))

        elif isinstance(block, SystemMessage):
            style = {
                "info": "dim",
                "warning": "yellow",
                "error": "bold red",
            }.get(block.level, "dim")
            self.console.print(Text(block.text, style=style))

    def _handle_slash_command(self, command: str) -> bool:
        """Handle slash commands. Returns False to quit."""
        if not self.session:
            return True

        result = handle_command(command, self.session, self.game_dir)

        # Render all blocks
        for block in result.blocks:
            self.render_block(block)

        # Handle special actions
        if result.action == "quit":
            return False
        elif result.action == "clear":
            self.console.clear()
        elif result.action == "reset":
            # Reload the game
            self.session = GameSession.from_game_file(self.game_path, debug=self.debug)
            state = get_game_state(self.session.runtime)
            room_block = build_room_block(state, self.session.runtime, self.game_dir)
            self.render_block(room_block)

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

            # Add spacing before response (command already visible from input)
            self.console.print()

            # Track previous room for change detection
            previous_room = self._last_room

            # Stream LLM outputs as they arrive
            def on_narrative(text: str) -> None:
                if text:
                    self.render_block(Narrative(text=text))

            def on_image(image: ImageRequest) -> None:
                # TUI can't display images, just note they exist
                self.render_block(Image(src=image.path, alt=image.alt))

            # Process command - outputs are streamed via callbacks
            self.session.process_input(
                user_input,
                on_narrative=on_narrative,
                on_image=on_image,
            )

            # Check if room changed and show new room
            state = get_game_state(self.session.runtime)
            if state.room != previous_room:
                room_block = build_room_block(state, self.session.runtime, self.game_dir)
                self.render_block(room_block)


def run_tui(game_path: str, debug: bool = False) -> None:
    """Run the simple TUI."""
    tui = SimpleTUI(game_path, debug=debug)
    tui.run()
