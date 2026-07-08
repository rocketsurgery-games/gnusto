"""
Simple terminal UI for Gnusto.

Uses Rich for formatting. No scroll regions, no cursor manipulation,
just straightforward terminal output.
"""

import re
from pathlib import Path

from rich.console import Console
from rich.rule import Rule
from rich.text import Text

from .agent import GameSession
from .commands import handle_command
from .llm import LLMConfig
from .render import (
    ActionResult,
    Ambient,
    Caption,
    ContentBlock,
    DebugInfo,
    Focus,
    Image,
    Narrate,
    Reveal,
    RoomEnter,
    Sfx,
    Speak,
    Splash,
    SystemMessage,
    Think,
    build_room_block,
)
from .state import get_game_state
from .terminal_images import display_image
from .terminal_images import is_supported as terminal_images_supported

# Regex patterns for styling
REF_PATTERN = re.compile(r"@[\w-]+")
QUOTE_PATTERN = re.compile(r'"[^"]*"')
SPEAKER_PATTERN = re.compile(r'(?<=\S)(\s*)(@[\w-]+:\s*")')


def style_narrative(text: str) -> Text:
    """Apply Rich styles to narrative text using Text object (no markup parsing).

    This approach is immune to any content in the text - no escaping needed.
    """
    # Add newlines before @speaker: patterns (but not at start of text)
    text = SPEAKER_PATTERN.sub(r"\n\n\2", text)

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

    def __init__(
        self,
        game_path: str,
        debug: bool = False,
        plain: bool = False,
        llm_config: LLMConfig | None = None,
        parsing_only: bool | None = None,
    ):
        self.game_path = game_path
        self.game_dir = Path(game_path).resolve()
        if self.game_dir.is_file():
            self.game_dir = self.game_dir.parent
        self.debug = debug
        self.plain = plain
        self.llm_config = llm_config
        self.parsing_only = parsing_only
        self.session: GameSession | None = None
        self.console = Console(
            highlight=False, force_terminal=not plain, no_color=plain
        )
        self._last_room: str | None = None
        self._can_display_images = terminal_images_supported() and not plain

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
                exits_str = ", ".join(e.direction for e in block.exits)
                self.console.print(Text(f"Exits: {exits_str}", style="dim yellow"))

            # Inventory
            if block.inventory:
                inv_str = ", ".join(o.name for o in block.inventory)
                self.console.print(Text(f"Carrying: {inv_str}", style="dim green"))

            # Objects
            if block.objects:
                obj_str = ", ".join(o.name for o in block.objects)
                self.console.print(Text(f"You see: {obj_str}", style="dim"))

            # Image - display if terminal supports it
            if block.image:
                image_path = Path(block.image)
                if not image_path.exists():
                    image_path = self.game_dir / block.image.lstrip("/")
                if self._can_display_images and image_path.exists():
                    term_width, _ = self.console.size
                    img_width = min(int(term_width * 0.6), 80)
                    display_image(image_path, width=img_width)
                else:
                    self.console.print(
                        Text(f"[Image: {Path(block.image).name}]", style="dim")
                    )

            self.console.print()
            self._last_room = block.room_id

        elif isinstance(block, ActionResult):
            self.console.print(Text(block.text, style="dim"))

        elif isinstance(block, Narrate):
            styled = style_narrative(block.text)
            self.console.print(styled)
            self.console.print()

        elif isinstance(block, Speak):
            speaker_name = block.speaker.replace("@", "").replace("-", " ").title()
            speaker_text = Text(f"{speaker_name}: ", style="bold")
            dialogue = Text(f'"{block.text}"', style="italic yellow")
            line = speaker_text + dialogue
            if block.manner:
                line.append(f" ({block.manner})", style="dim italic")
            self.console.print(line)
            self.console.print()

        elif isinstance(block, Think):
            self.console.print(Text(block.text, style="italic magenta"))
            self.console.print()

        elif isinstance(block, Ambient):
            self.console.print(Text(block.text, style="dim italic"))
            self.console.print()

        elif isinstance(block, (Reveal, Focus)):
            styled = style_narrative(block.text)
            self.console.print(styled)
            self.console.print()

        elif isinstance(block, Caption):
            # Narrator's out-of-world voice: a set-apart caption line.
            self.console.print(Text(block.text, style="dim italic cyan"))
            self.console.print()

        elif isinstance(block, Splash):
            # Full-bleed dramatic beat: rule it off and center bold text.
            self.console.rule(style="red")
            self.console.print(Text(block.text, style="bold red", justify="center"))
            self.console.rule(style="red")
            self.console.print()

        elif isinstance(block, Sfx):
            # Onomatopoeia lettering.
            self.console.print(Text(block.text.upper(), style="bold yellow"))
            self.console.print()

        elif isinstance(block, Image):
            image_path = Path(block.src.lstrip("/"))
            if not image_path.is_absolute():
                image_path = self.game_dir / image_path

            if self._can_display_images and image_path.exists():
                term_width, _ = self.console.size
                img_width = min(int(term_width * 0.6), 80)
                display_image(image_path, width=img_width)
            else:
                self.console.print(
                    Text(f"[Image: {Path(block.src).name}]", style="dim")
                )

        elif isinstance(block, SystemMessage):
            style = {
                "info": "dim",
                "warning": "yellow",
                "error": "bold red",
            }.get(block.level, "dim")
            self.console.print(Text(block.text, style=style))

        elif isinstance(block, DebugInfo):
            self.console.print(Text(block.label, style="dim cyan"))
            for line in block.content.split("\n"):
                if line:
                    self.console.print(Text(f"  {line}", style="dim"))

        else:
            # Drift guard: a block type with no renderer here. Fall back to its
            # text so nothing is silently dropped (the block-vocabulary test
            # enforces that every narrative type gets a real branch).
            text = getattr(block, "text", None)
            if text:
                self.console.print(style_narrative(str(text)))
                self.console.print()

    def _handle_slash_command(self, command: str) -> bool:
        """Handle slash commands. Returns False to quit."""
        if not self.session:
            return True

        result = handle_command(command, self.session, self.game_dir)

        for block in result.blocks:
            self.render_block(block)

        if result.action == "quit":
            return False
        elif result.action == "clear":
            self.console.clear()
        elif result.action == "reset":
            self.session = GameSession.from_game_file(
                self.game_path,
                llm_config=self.llm_config,
                debug=self.debug,
                parsing_only=self.parsing_only,
            )
            state = get_game_state(self.session.runtime)
            room_block = build_room_block(state, self.session.runtime, self.game_dir)
            self.render_block(room_block)

        return True

    def run(self) -> None:
        """Run the game loop."""
        self.render_block(SystemMessage(f"Loading game: {self.game_path}"))
        if self.debug:
            self.render_block(SystemMessage("Debug mode enabled"))

        self.session = GameSession.from_game_file(
            self.game_path,
            llm_config=self.llm_config,
            debug=self.debug,
            parsing_only=self.parsing_only,
        )

        self.console.print()
        self.console.print(Rule("Game Start"))

        # Show intro
        if self.session.runtime.world.intro:
            self.render_block(Narrate(self.session.runtime.world.intro))

        # Show initial room state
        state = get_game_state(self.session.runtime)
        room_block = build_room_block(state, self.session.runtime, self.game_dir)
        self.render_block(room_block)

        self.render_block(
            SystemMessage("Type commands in natural language. /help for commands.")
        )
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

            # Add spacing before response
            self.console.print()

            # Track previous room for change detection
            previous_room = self._last_room

            # Stream LLM outputs as they arrive
            def on_blocks(blocks: list) -> None:
                for block in blocks:
                    self.render_block(block)

            def on_debug(action_sexpr: str, result_details: str) -> None:
                self.render_block(DebugInfo(label=action_sexpr, content=result_details))

            # Process command
            self.session.process_input(
                user_input,
                on_blocks=on_blocks,
                on_debug=on_debug if self.session.debug else None,
            )

            # Check if room changed and show new room
            state = get_game_state(self.session.runtime)
            if state.room != previous_room:
                room_block = build_room_block(
                    state, self.session.runtime, self.game_dir
                )
                self.render_block(room_block)


def run_tui(
    game_path: str,
    debug: bool = False,
    plain: bool = False,
    llm_config: LLMConfig | None = None,
    parsing_only: bool | None = None,
) -> None:
    """Run the simple TUI.

    Args:
        game_path: Path to the game directory or main .grue file
        debug: Enable debug mode (show LLM tool calls)
        plain: Text-only mode (no images, no colors)
        llm_config: Optional LLM configuration override
        parsing_only: Force parse-only mode (engine emits all text); None uses
            the per-model default.
    """
    tui = SimpleTUI(
        game_path,
        debug=debug,
        plain=plain,
        llm_config=llm_config,
        parsing_only=parsing_only,
    )
    tui.run()
