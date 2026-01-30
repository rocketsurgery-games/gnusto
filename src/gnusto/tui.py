"""
Simple terminal UI for Gnusto.

Uses Rich for formatting. No scroll regions, no cursor manipulation,
just straightforward terminal output.

Scene rendering (--render flag):
    When enabled, generates and displays room illustrations using filfre.
    Requires a CUDA GPU and the filfre pipeline (~15GB VRAM).
    Images are displayed inline in supported terminals (Kitty, iTerm2, WezTerm).
"""

import re
from pathlib import Path
from typing import Optional
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
from .terminal_images import display_image, is_supported as terminal_images_supported


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

    def __init__(
        self,
        game_path: str,
        debug: bool = False,
        render: bool = False,
        render_cache_dir: str | Path | None = None,
    ):
        self.game_path = game_path
        self.game_dir = Path(game_path).resolve()
        if self.game_dir.is_file():
            self.game_dir = self.game_dir.parent
        self.debug = debug
        self.render_enabled = render
        self.session: GameSession | None = None
        self.console = Console(highlight=False)
        self._last_room: str | None = None
        self._scene_renderer: Optional["SceneRenderer"] = None
        self._render_cache_dir = render_cache_dir or self.game_dir / "cache" / "renders"
        self._can_display_images = terminal_images_supported()

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

            # Image - display if terminal supports it
            if block.image:
                # Handle paths from renderer (relative to cwd) and game def (relative to game_dir)
                image_path = Path(block.image)
                if not image_path.exists():
                    image_path = self.game_dir / block.image.lstrip("/")
                if self._can_display_images and image_path.exists():
                    # Calculate width (use ~60% of terminal width)
                    term_width, _ = self.console.size
                    img_width = min(int(term_width * 0.6), 80)
                    display_image(image_path, width=img_width)
                else:
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
            # Display image if terminal supports it
            # Handle paths like "/gfx/foo.jpg" or "gfx/foo.jpg"
            image_path = Path(block.src.lstrip("/"))
            if not image_path.is_absolute():
                image_path = self.game_dir / image_path

            # If image doesn't exist, try to generate it
            if not image_path.exists() and self._scene_renderer:
                # Extract entity ID from path (e.g., "/gfx/lantern.jpg" -> "@lantern")
                entity_id = f"@{image_path.stem}"
                # Try room first, then object
                generated = self._render_room_image(entity_id) or self._render_object_image(entity_id)
                if generated:
                    image_path = Path(generated)

            if self._can_display_images and image_path.exists():
                term_width, _ = self.console.size
                img_width = min(int(term_width * 0.6), 80)
                display_image(image_path, width=img_width)
            else:
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

        # Render all blocks, applying scene rendering to RoomEnter blocks
        for block in result.blocks:
            if isinstance(block, RoomEnter) and self._scene_renderer:
                generated_image = self._render_room_image(block.room_id)
                if generated_image:
                    block.image = generated_image
            self.render_block(block)

        # Handle special actions
        if result.action == "quit":
            return False
        elif result.action == "clear":
            self.console.clear()
        elif result.action == "reset":
            # Reload the game
            self.session = GameSession.from_game_file(self.game_path, debug=self.debug)
            # Re-init scene renderer for new session
            if self.render_enabled:
                self._init_scene_renderer()
            state = get_game_state(self.session.runtime)
            room_block = build_room_block(state, self.session.runtime, self.game_dir)
            if self._scene_renderer:
                generated_image = self._render_room_image(state.room)
                if generated_image:
                    room_block.image = generated_image
            self.render_block(room_block)

        return True

    def _init_scene_renderer(self) -> None:
        """Initialize the scene renderer if enabled."""
        if not self.render_enabled or not self.session:
            return

        try:
            from .scene_renderer import SceneRenderer
            self.render_block(SystemMessage("Loading scene renderer (this may take a moment)..."))
            self._scene_renderer = SceneRenderer(
                runtime=self.session.runtime,
                cache_dir=self._render_cache_dir,
                assets_dir=self.game_dir / "gfx",
            )
            self.render_block(SystemMessage("Scene renderer ready."))
        except Exception as e:
            self.render_block(SystemMessage(
                f"Failed to initialize scene renderer: {e}",
                level="warning"
            ))
            self.render_enabled = False

    def _render_room_image(self, room_id: str) -> str | None:
        """Generate a room image if scene rendering is enabled.

        Returns:
            Path to the generated image, or None
        """
        if not self._scene_renderer:
            return None

        try:
            image_path = self._scene_renderer.render_room(room_id)
            if image_path:
                # Return relative path for the render block
                return str(image_path)
        except Exception as e:
            if self.debug:
                self.console.print(Text(f"[Scene render failed: {e}]", style="dim red"))

        return None

    def _render_object_image(self, object_id: str) -> str | None:
        """Generate an object image if scene rendering is enabled.

        Returns:
            Path to the generated image, or None
        """
        if not self._scene_renderer:
            return None

        try:
            image_path = self._scene_renderer.render_object(object_id)
            if image_path:
                return str(image_path)
        except Exception as e:
            if self.debug:
                self.console.print(Text(f"[Object render failed: {e}]", style="dim red"))

        return None

    def run(self) -> None:
        """Run the game loop."""
        self.render_block(SystemMessage(f"Loading game: {self.game_path}"))
        if self.debug:
            self.render_block(SystemMessage("Debug mode enabled"))
        if self.render_enabled:
            self.render_block(SystemMessage("Scene rendering enabled"))

        self.session = GameSession.from_game_file(self.game_path, debug=self.debug)

        # Initialize scene renderer after session is created
        if self.render_enabled:
            self._init_scene_renderer()

        self.console.print()
        self.console.print(Rule("Game Start"))

        # Show intro
        if self.session.runtime.world.intro:
            self.render_block(Narrative(self.session.runtime.world.intro))

        # Show initial room state
        state = get_game_state(self.session.runtime)
        room_block = build_room_block(state, self.session.runtime, self.game_dir)

        # Generate scene image if renderer is enabled (prefer over static images)
        if self._scene_renderer:
            generated_image = self._render_room_image(state.room)
            if generated_image:
                room_block.image = generated_image

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

                # Generate scene image if renderer is enabled (prefer over static images)
                if self._scene_renderer:
                    generated_image = self._render_room_image(state.room)
                    if generated_image:
                        room_block.image = generated_image

                self.render_block(room_block)


def run_tui(game_path: str, debug: bool = False, render: bool = False) -> None:
    """Run the simple TUI.

    Args:
        game_path: Path to the game directory or main .grue file
        debug: Enable debug mode (show LLM tool calls)
        render: Enable scene rendering (requires CUDA GPU and filfre)
    """
    tui = SimpleTUI(game_path, debug=debug, render=render)
    tui.run()
