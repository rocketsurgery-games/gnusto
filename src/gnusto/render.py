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
class Narrate:
    """LLM-generated second-person prose."""
    text: str


@dataclass
class Speak:
    """Character dialogue."""
    speaker: str  # Entity ID, e.g. "@hacker"
    text: str
    manner: str | None = None  # e.g. "whispering", "shouting"


@dataclass
class Think:
    """Player's inner monologue / dramatic moment."""
    text: str


@dataclass
class Ambient:
    """Atmospheric detail."""
    text: str


@dataclass
class Reveal:
    """Discovery of something new."""
    text: str
    entity: str | None = None  # Entity ID for image lookup


@dataclass
class Focus:
    """Close-up on an entity."""
    text: str
    entity: str | None = None  # Entity ID for image lookup


@dataclass
class Image:
    """An image to display (system-generated, not from LLM)."""
    src: str  # Path relative to game directory
    alt: str = ""
    layout: Literal["inline", "float-left", "float-right", "background"] = "inline"
    size: Literal["small", "medium", "large", "full"] = "medium"


@dataclass
class SystemMessage:
    """System message (save/load, errors, etc.)."""
    text: str
    level: Literal["info", "warning", "error"] = "info"


@dataclass
class DebugInfo:
    """Debug information (action execution, grue I/O, etc.)."""
    label: str
    content: str


# Union type for all content blocks
ContentBlock = (
    RoomEnter | ActionResult | Narrate | Speak | Think | Ambient | Reveal | Focus
    | Image | SystemMessage | DebugInfo
)


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
    # Room images are now generated on-demand from render specs by the scene renderer.
    # The TUI and web UI handle image generation separately.
    image_url = None

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
