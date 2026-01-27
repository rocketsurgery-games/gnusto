"""
Structured content blocks for rendering game output.

Provides a unified representation of game output that can be rendered
differently by TUI (colored text) and web UI (HTML with images).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from .state import GameState
    from grue.runtime import GrueRuntime


@dataclass
class RoomEnter:
    """Player has entered a room."""
    room_id: str
    name: str
    description: str
    exits: list[str] = field(default_factory=list)  # Destination room names
    objects: list[str] = field(default_factory=list)  # Just object descriptions
    inventory: list[str] = field(default_factory=list)  # Just item descriptions
    image: str | None = None  # Path to room image, if any


@dataclass
class ActionResult:
    """Result of a game action (from effects)."""
    text: str


@dataclass
class Narrative:
    """LLM-generated prose."""
    text: str


@dataclass
class Image:
    """An image to display."""
    src: str  # Path relative to game directory
    alt: str = ""


@dataclass
class SystemMessage:
    """System message (save/load, errors, etc.)."""
    text: str
    level: Literal["info", "warning", "error"] = "info"


# Union type for all content blocks
ContentBlock = RoomEnter | ActionResult | Narrative | Image | SystemMessage


def build_room_block(
    state: "GameState",
    runtime: "GrueRuntime",
    game_dir: Path | None = None,
) -> RoomEnter:
    """
    Build a RoomEnter block from current game state.

    Args:
        state: Current game state
        runtime: Game runtime (for looking up room images)
        game_dir: Game directory for resolving image paths

    Returns:
        RoomEnter block with room info
    """
    # Get room image - check :image property first, then look for gfx/{room_id}.jpg/png
    image_url = None
    if game_dir:
        room_state = runtime.state.objects.get(state.room)
        if room_state:
            img = room_state.properties.get("image")
            if img:
                full_path = game_dir / img
                if full_path.exists():
                    # Return web URL path
                    image_url = f"/gfx/{Path(img).name}"

        # If no explicit image, look for one matching room ID
        if not image_url:
            # Strip @ prefix from room ID to get base name
            room_base = state.room.lstrip("@")
            gfx_dir = game_dir / "gfx"
            if gfx_dir.exists():
                for ext in (".jpg", ".png", ".jpeg", ".webp"):
                    img_path = gfx_dir / f"{room_base}{ext}"
                    if img_path.exists():
                        image_url = f"/gfx/{room_base}{ext}"
                        break

    # De-duplicate exits (multiple directions may lead to same room)
    seen_exits: set[str] = set()
    unique_exits: list[str] = []
    for e in state.exits:
        if e.destination_name not in seen_exits:
            seen_exits.add(e.destination_name)
            unique_exits.append(e.destination_name)

    return RoomEnter(
        room_id=state.room,
        name=state.room_name,
        description=state.room_description,
        exits=unique_exits,
        objects=[obj.description for obj in state.visible_objects],
        inventory=[obj.description for obj in state.inventory],
        image=image_url,
    )


def build_turn_output(
    action_results: list[str],
    narrative: str,
    state: "GameState",
    runtime: "GrueRuntime",
    previous_room: str | None = None,
    game_dir: Path | None = None,
) -> list[ContentBlock]:
    """
    Build content blocks for a completed turn.

    Args:
        action_results: List of action result strings (from effects)
        narrative: LLM-generated narrative text
        state: Current game state after the turn
        runtime: Game runtime
        previous_room: Room ID before the turn (to detect room changes)
        game_dir: Game directory for resolving image paths

    Returns:
        List of ContentBlock objects to render
    """
    blocks: list[ContentBlock] = []

    # Add action results (skip empty or "Done.")
    for result in action_results:
        if result and result != "Done.":
            blocks.append(ActionResult(text=result))

    # Add narrative if present
    if narrative:
        blocks.append(Narrative(text=narrative))

    # Add room block if room changed (or if no previous room - initial state)
    room_changed = previous_room is None or state.room != previous_room
    if room_changed:
        room_block = build_room_block(state, runtime, game_dir)
        blocks.append(room_block)

    return blocks


def format_room_enter(room: RoomEnter) -> str:
    """Format a RoomEnter block as plain text (for TUI)."""
    lines = []
    lines.append(room.name)
    if room.description:
        lines.append(room.description)
    if room.exits:
        lines.append(f"Exits: {', '.join(room.exits)}")
    if room.inventory:
        lines.append(f"Carrying: {', '.join(room.inventory)}")
    if room.objects:
        lines.append(f"You see: {', '.join(room.objects)}")
    return "\n".join(lines)
