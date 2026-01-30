"""
Image catalog for Gnusto games.

Provides a simple structure for discovering and filtering available images
that the LLM can use when narrating. This is a chokepoint for layering in
more sophisticated image selection logic later.

Current naming convention:
- {room}.jpg - Room illustration
- {object}.jpg - Object illustration
- Future: {subject}-{state}.jpg for state-dependent variants
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import GameState


@dataclass
class ImageInfo:
    """Metadata about an available image."""

    id: str  # Unique identifier (filename without extension)
    path: str  # Web URL path (e.g., "/gfx/terminal-room.jpg")
    subject: str  # What the image depicts (room ID, object ID, or description)
    category: str  # "room", "object", or "scene"
    description: str  # Human-readable description for LLM context


def scan_images(game_dir: Path) -> list[ImageInfo]:
    """
    Scan the game's gfx/ directory for available images.

    Args:
        game_dir: Path to the game directory

    Returns:
        List of ImageInfo for all discovered images
    """
    gfx_dir = game_dir / "gfx"
    if not gfx_dir.exists():
        return []

    images = []
    extensions = {".jpg", ".jpeg", ".png", ".webp"}

    for img_path in gfx_dir.iterdir():
        if img_path.suffix.lower() not in extensions:
            continue

        stem = img_path.stem
        web_path = f"/gfx/{img_path.name}"

        # Infer category and description from filename
        # Convention: rooms use room-id names, objects use object-id names
        # For now, just use the stem as both subject and description
        # TODO: Load from metadata file if present

        # Convert filename to readable description
        description = stem.replace("-", " ").replace("_", " ").title()

        images.append(ImageInfo(
            id=stem,
            path=web_path,
            subject=f"@{stem}",  # Assume it maps to a game entity
            category="scene",  # Default; could be inferred or specified
            description=description,
        ))

    return images


def filter_images_for_state(
    images: list[ImageInfo],
    state: "GameState",
) -> list[ImageInfo]:
    """
    Filter images to those relevant to the current game state.

    Currently returns images matching:
    - Current room
    - Visible objects
    - Inventory items

    Args:
        images: Full list of available images
        state: Current game state

    Returns:
        Filtered list of relevant images
    """
    # Build set of relevant entity IDs
    relevant_ids = {state.room}
    for obj in state.visible_objects:
        relevant_ids.add(obj.id)
    for obj in state.inventory:
        relevant_ids.add(obj.id)

    # Also include IDs without @ prefix for matching
    relevant_stems = {id.lstrip("@") for id in relevant_ids}

    return [
        img for img in images
        if img.subject in relevant_ids or img.id in relevant_stems
    ]


def add_renderable_entities(
    images: list[ImageInfo],
    runtime: "GrueRuntime",
) -> list[ImageInfo]:
    """
    Add virtual image entries for entities that have render specs.

    These can be generated on-the-fly by the scene renderer.

    Args:
        images: Existing list of static images
        runtime: Game runtime to check for render specs

    Returns:
        Extended list including renderable entities
    """
    from grue.render import has_render_spec

    # Track existing image IDs to avoid duplicates
    existing_ids = {img.id for img in images}
    result = list(images)

    # Check rooms for render specs
    for room_id, room in runtime.world.rooms.items():
        stem = room_id.lstrip("@")
        if stem not in existing_ids and has_render_spec(room):
            result.append(ImageInfo(
                id=stem,
                path=f"/gfx/{stem}.png",  # Virtual path
                subject=room_id,
                category="room",
                description=f"{room.description} (can be generated)",
            ))

    # Check objects for render specs
    for obj_id, obj in runtime.world.objects.items():
        stem = obj_id.lstrip("@")
        if stem not in existing_ids and has_render_spec(obj):
            result.append(ImageInfo(
                id=stem,
                path=f"/gfx/{stem}.png",  # Virtual path
                subject=obj_id,
                category="object",
                description=f"{obj.description} (can be generated)",
            ))

    return result


if TYPE_CHECKING:
    from grue.runtime import GrueRuntime


def format_image_catalog(images: list[ImageInfo]) -> str:
    """
    Format image catalog for inclusion in LLM context.

    Args:
        images: List of images to include

    Returns:
        Markdown-formatted catalog string
    """
    if not images:
        return "**Available images:** none"

    lines = ["**Available images:**"]
    for img in images:
        lines.append(f"- `{img.path}`: {img.description}")

    return "\n".join(lines)
