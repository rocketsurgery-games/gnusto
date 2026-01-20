"""
Game state serialization for the Frotz agent.

Provides structured representations of game state that can be serialized
for agent context. The agent uses this to understand the current game
situation and make decisions about actions.
"""

from dataclasses import dataclass, field
from typing import Any

# Import runtime type for type hints only
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from grue.runtime import GrueRuntime


@dataclass
class ObjectInfo:
    """Information about a game object for agent context."""

    id: str
    description: str  # Short name like "pc", "chair"
    fdesc: str = ""  # First/look description for room listings
    behaviors: list[str] = field(default_factory=list)  # Available verbs
    properties: dict[str, Any] = field(default_factory=dict)  # Visible properties
    contents: list["ObjectInfo"] = field(default_factory=list)  # Nested objects


@dataclass
class RoomInfo:
    """Information about a room for display."""

    id: str
    description: str  # Short description/name


@dataclass
class ExitInfo:
    """Information about an exit for agent context."""

    direction: str
    destination_id: str  # Room ID like @smith-st
    destination_name: str  # Human-readable like "Smith Street"
    via: str | None = None  # Description of door/barrier, e.g., "elevator doors"


@dataclass
class GameState:
    """Current game state for agent context."""

    room: str  # Room ID like @terminal-room
    room_name: str  # Human-readable name like "Terminal Room"
    room_description: str
    visible_objects: list[ObjectInfo]
    inventory: list[ObjectInfo]
    exits: list[ExitInfo]  # Rich exit information for agent
    nearby_rooms: list[RoomInfo] = field(default_factory=list)  # Unique adjacent rooms (for player)
    vehicle: tuple[str, str] | None = None  # (vehicle_name, preposition) if in vehicle

    def to_context_string(self) -> str:
        """Format game state as a string for agent context."""
        lines = []

        # Location
        lines.append(f"## Current Location: {self.room}")
        if self.vehicle:
            lines.append(f"(You are {self.vehicle[1]} the {self.vehicle[0]})")
        lines.append("")
        lines.append(self.room_description)
        lines.append("")

        # Exits
        if self.exits:
            exit_parts = []
            for exit in self.exits:
                if exit.via:
                    exit_parts.append(f"{exit.direction} -> {exit.destination_name} (via {exit.via})")
                else:
                    exit_parts.append(f"{exit.direction} -> {exit.destination_name}")
            lines.append(f"**Exits:** {', '.join(exit_parts)}")
        else:
            lines.append("**Exits:** none")
        lines.append("")

        # Visible objects
        if self.visible_objects:
            lines.append("**Visible objects:**")
            self._render_objects(self.visible_objects, lines, indent=0)
        else:
            lines.append("**Visible objects:** none")
        lines.append("")

        # Inventory
        if self.inventory:
            lines.append("**Inventory:**")
            self._render_objects(self.inventory, lines, indent=0)
        else:
            lines.append("**Inventory:** empty")

        return "\n".join(lines)

    def _render_objects(
        self, objects: list["ObjectInfo"], lines: list[str], indent: int
    ) -> None:
        """Render objects with nested contents."""
        prefix = "  " * indent
        for obj in objects:
            behaviors_str = ", ".join(obj.behaviors) if obj.behaviors else "none"
            lines.append(f"{prefix}- {obj.id}: {obj.description} [actions: {behaviors_str}]")
            if obj.contents:
                self._render_objects(obj.contents, lines, indent + 1)


def get_game_state(runtime: "GrueRuntime") -> GameState:
    """
    Extract current game state from runtime for agent context.

    Args:
        runtime: GrueRuntime instance

    Returns:
        GameState with current room, objects, inventory, exits
    """
    room = runtime.get_player_room()
    room_def = runtime.world.rooms.get(room)
    room_name = room_def.description if room_def else room
    room_desc = runtime.get_room_description()
    vehicle = runtime.get_player_vehicle()
    player = runtime.get_player_name()
    player_loc = runtime.get_player_location()

    # Get all visible object names as a set for efficient lookup
    # Use for_description=False to include nodesc objects - they're interactable
    # even if not listed in prose descriptions (e.g., call buttons mentioned in ldesc)
    visible_set = set(runtime.get_visible_objects(for_description=False))
    inventory_set = set(runtime.get_inventory())

    # Build tree of visible objects (excluding inventory)
    # Top-level: objects directly in room, player's vehicle, or room's :visible list
    top_level_locs = {room}
    if player_loc and player_loc != room:
        top_level_locs.add(player_loc)  # Player's vehicle

    # Get room's :visible list (objects explicitly made visible, e.g., call buttons)
    room_def = runtime.world.rooms.get(room)
    room_visible = set(room_def.visible) if room_def else set()

    visible_objects = []
    for name in visible_set:
        if name in inventory_set:
            continue
        obj_state = runtime.state.objects.get(name)
        if not obj_state:
            continue
        # Include if: in room/vehicle, OR explicitly in room's :visible list
        if obj_state.location in top_level_locs or name in room_visible:
            obj_info = _get_object_info_with_contents(runtime, name, visible_set)
            visible_objects.append(obj_info)

    # Build tree of inventory items
    inventory = []
    for name in inventory_set:
        obj_info = _get_object_info_with_contents(runtime, name, visible_set)
        inventory.append(obj_info)

    # Build rich exit information
    exits = []
    nearby_rooms = []
    seen_rooms: set[str] = set()

    if room_def:
        for exit in room_def.exits:
            # Get destination room info
            dest_room_def = runtime.world.rooms.get(exit.to)
            dest_name = dest_room_def.description if dest_room_def else exit.to

            # Get via object description if present
            via_desc = None
            if exit.via:
                via_obj = runtime.world.objects.get(exit.via)
                if via_obj:
                    via_desc = via_obj.description

            exits.append(ExitInfo(
                direction=exit.direction,
                destination_id=exit.to,
                destination_name=dest_name,
                via=via_desc,
            ))

            # Build unique nearby rooms list for player display
            if exit.to not in seen_rooms:
                seen_rooms.add(exit.to)
                if dest_room_def:
                    nearby_rooms.append(RoomInfo(id=exit.to, description=dest_room_def.description))

    return GameState(
        room=room,
        room_name=room_name,
        room_description=room_desc,
        visible_objects=visible_objects,
        inventory=inventory,
        exits=exits,
        nearby_rooms=nearby_rooms,
        vehicle=vehicle,
    )


def _format_behavior(verb: str, params: list[str]) -> str:
    """Format a behavior with its parameters for agent context.

    Examples:
        give, [item] -> "give <item>"
        take, [] -> "take"
        unlock, [key] -> "unlock <key>"
    """
    if params:
        param_str = " ".join(f"<{p}>" for p in params)
        return f"{verb} {param_str}"
    return verb


def _get_object_info_with_contents(
    runtime: "GrueRuntime", obj_name: str, visible_set: set[str]
) -> ObjectInfo:
    """Get object info including available behaviors and nested contents."""
    desc = runtime.get_object_description(obj_name)

    # Get fdesc for natural room listings (evaluates dynamic :describe behavior)
    fdesc = runtime.get_object_fdesc(obj_name)

    # Get behaviors from world definition
    # Track verb -> formatted string (with params)
    behavior_map: dict[str, str] = {}
    if obj_name in runtime.world.objects:
        obj_def = runtime.world.objects[obj_name]
        for b in obj_def.behaviors:
            # Skip internal behaviors (on-enter, describe, etc.)
            if not b.verb.startswith("on-") and b.verb not in ("describe", "through"):
                behavior_map[b.verb] = _format_behavior(b.verb, b.params)

    # Also check defaults for common behaviors
    # Objects can respond to default behaviors even without explicit definition
    for verb in runtime.world.defaults:
        if verb not in behavior_map:
            # Defaults have no params (they operate on just the object)
            behavior_map[verb] = verb

    # Recursively get visible contents (including nodesc objects in containers)
    # Container contents should be shown even if they have nodesc - that flag
    # is about room listings, not about whether the agent can see/interact with them
    contents = []
    for name, obj_state in runtime.state.objects.items():
        if obj_state.location == obj_name and runtime.is_visible(name):
            child_info = _get_object_info_with_contents(runtime, name, visible_set)
            contents.append(child_info)

    return ObjectInfo(
        id=obj_name,
        description=desc,
        fdesc=fdesc,
        behaviors=sorted(behavior_map.values()),
        contents=contents,
    )
