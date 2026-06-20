"""
Structured content blocks for rendering game output.

Provides a unified representation of game output that can be rendered
differently by TUI (colored text) and web UI (HTML with images).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from grue.render import is_renderable, resolve_asset_key

# Image formats tried (in order) when resolving an extension-less asset key.
SUPPORTED_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")

if TYPE_CHECKING:
    from grue.runtime import GrueRuntime

    from .state import GameState


@dataclass
class EntityInfo:
    """Structured entity reference (id + display name)."""

    id: str
    name: str
    behaviors: list[str] = field(default_factory=list)


@dataclass
class ExitDetail:
    """Structured exit (direction + destination display name)."""

    direction: str
    destination: str


@dataclass
class RoomEnter:
    """Player has entered a room."""

    room_id: str
    name: str
    description: str
    exits: list[ExitDetail] = field(default_factory=list)
    objects: list[EntityInfo] = field(default_factory=list)
    inventory: list[EntityInfo] = field(default_factory=list)
    image: str | None = None  # Path to room image, if any


@dataclass
class ActionResult:
    """Result of a game action (from effects)."""

    text: str


# Beat / emphasis: the LLM's pacing intent for a block. The ENGINE maps these to
# presentation (size, spacing, weight) — the LLM never specifies pixels.
Beat = Literal["aside", "normal", "emphasis"]


@dataclass
class Narrate:
    """LLM-generated second-person prose."""

    text: str
    beat: Beat | None = None


@dataclass
class Speak:
    """Character dialogue."""

    speaker: str  # Entity ID, e.g. "@hacker"
    text: str
    manner: str | None = None  # e.g. "whispering", "shouting"
    beat: Beat | None = None


@dataclass
class Think:
    """Player's inner monologue / dramatic moment."""

    text: str
    beat: Beat | None = None


@dataclass
class Ambient:
    """Atmospheric detail."""

    text: str
    beat: Beat | None = None


@dataclass
class Reveal:
    """Discovery of something new."""

    text: str
    entity: str | None = None  # Entity ID for image lookup
    beat: Beat | None = None


@dataclass
class Focus:
    """Close-up on an entity."""

    text: str
    entity: str | None = None  # Entity ID for image lookup
    beat: Beat | None = None


@dataclass
class Sfx:
    """Onomatopoeia lettering (a comic sound-effect panel)."""

    text: str
    beat: Beat | None = None


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
    RoomEnter
    | ActionResult
    | Narrate
    | Speak
    | Think
    | Ambient
    | Reveal
    | Focus
    | Sfx
    | Image
    | SystemMessage
    | DebugInfo
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
    # Resolve the room's current asset key to an image URL
    image_url = None
    room = runtime.world.rooms.get(state.room)
    if room and is_renderable(room):
        image_url = _resolve_image_url(room.render, state.room, runtime, game_dir)

    # De-duplicate exits: keep first direction per destination
    seen_dests: set[str] = set()
    exits: list[ExitDetail] = []
    for e in state.exits:
        if e.destination_name not in seen_dests:
            seen_dests.add(e.destination_name)
            exits.append(
                ExitDetail(direction=e.direction, destination=e.destination_name)
            )

    def _flatten_objects(obj_list: list) -> list[EntityInfo]:
        result: list[EntityInfo] = []
        for obj in obj_list:
            result.append(
                EntityInfo(
                    id=obj.id, name=obj.description or obj.id, behaviors=obj.behaviors
                )
            )
            if obj.contents:
                result.extend(_flatten_objects(obj.contents))
        return result

    return RoomEnter(
        room_id=state.room,
        name=state.room_name,
        description=state.room_description,
        exits=exits,
        objects=_flatten_objects(state.visible_objects),
        inventory=_flatten_objects(state.inventory),
        image=image_url,
    )


def _resolve_image_url(
    spec: Any,
    entity_name: str,
    runtime: "GrueRuntime",
    game_dir: Path | None,
) -> str | None:
    """Resolve an entity's :render selector to a /assets/ URL, or None.

    Keys are extension-less; the file is located on disk by trying the
    supported image formats in order.
    """
    try:
        key = resolve_asset_key(entity_name, spec, runtime)
        if not key:
            return None
        if not game_dir:
            return f"/assets/{key}"
        assets = game_dir / "assets"
        # Literal key that already carries an extension.
        if (assets / key).is_file():
            return f"/assets/{key}"
        # Extension-less key: find the file across supported formats.
        for ext in SUPPORTED_IMAGE_EXTS:
            if (assets / f"{key}{ext}").is_file():
                return f"/assets/{key}{ext}"
        return None
    except Exception:
        return None


def build_scene_context(
    state: "GameState",
    runtime: "GrueRuntime",
    game_dir: Path | None = None,
) -> dict[str, dict[str, str | None]]:
    """Build entity-to-image map for the current scene.

    Iterates visible objects, inventory, and the current room, evaluating
    render specs to produce image URLs for the web UI's scene_context.

    Returns:
        Dict mapping entity IDs to {"name": ..., "image": ...}
    """
    entities: dict[str, dict[str, str | None]] = {}

    # Current room
    room_def = runtime.world.rooms.get(state.room)
    if room_def and is_renderable(room_def):
        image_url = _resolve_image_url(room_def.render, state.room, runtime, game_dir)
        entities[state.room] = {
            "name": str(room_def.description or ""),
            "image": image_url,
        }

    # Visible objects + inventory (recursing into containers)
    def _add_objects(obj_list: list) -> None:
        for obj_info in obj_list:
            obj_def = runtime.world.objects.get(obj_info.id)
            if obj_def and is_renderable(obj_def):
                url = _resolve_image_url(obj_def.render, obj_info.id, runtime, game_dir)
                entities[obj_info.id] = {
                    "name": str(obj_def.description or ""),
                    "image": url,
                }
            if obj_info.contents:
                _add_objects(obj_info.contents)

    _add_objects(list(state.visible_objects) + list(state.inventory))

    return entities


def format_room_enter(room: RoomEnter) -> str:
    """Format a RoomEnter block as plain text (for TUI)."""
    lines = []
    lines.append(room.name)
    if room.description:
        lines.append(room.description)
    if room.exits:
        lines.append(f"Exits: {', '.join(e.destination for e in room.exits)}")
    if room.inventory:
        lines.append(f"Carrying: {', '.join(item.name for item in room.inventory)}")
    if room.objects:
        lines.append(f"You see: {', '.join(obj.name for obj in room.objects)}")
    return "\n".join(lines)
