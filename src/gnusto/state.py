"""
Game state serialization for the Gnusto agent.

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
    ldesc: str = ""  # Long description for room listings
    behaviors: list[str] = field(default_factory=list)  # Available verbs
    properties: dict[str, Any] = field(default_factory=dict)  # Visible properties
    contents: list["ObjectInfo"] = field(default_factory=list)  # Nested objects
    nodesc: bool = False  # :nodesc scenery - interactable but not listed in prose


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
    known_entities: list[ObjectInfo] = field(default_factory=list)  # Entities with :known true not elsewhere
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

        # Known references (abstract entities the player knows about)
        if self.known_entities:
            lines.append("")
            lines.append("**Known references:**")
            for obj in self.known_entities:
                lines.append(f"- {obj.id}: {obj.description}")

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

    # All visible objects (flat) - used for recursive content tree building
    # Use for_description=False to include nodesc objects - they're interactable
    # even if not listed in prose descriptions (e.g., call buttons mentioned in ldesc)
    visible_set = set(runtime.get_visible_objects(for_description=False))
    inventory_set = set(runtime.get_inventory())

    # Room-level visible objects (excluding inventory and nested container contents)
    room_level = runtime.get_room_level_objects(for_description=False)

    visible_objects = []
    for name in room_level:
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
            # Skip message-only blocked exits (ZIL string/SORRY exits, e.g. the
            # kitchen chimney "Only Santa Claus climbs down chimneys."): they
            # carry no destination and are refusals, not navigable ways out.
            # Listing them misleads the agent and yields a None destination name
            # (which crashes format_room_enter's join).
            if exit.to is None:
                continue

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

    # Known entities: :known true, not already in visible/inventory
    already_shown = visible_set | inventory_set
    known_entities = []
    for name, obj_state in runtime.state.objects.items():
        if name in already_shown:
            continue
        if obj_state.properties.get("known") is True:
            desc = runtime.get_object_description(name)
            if desc:
                known_entities.append(ObjectInfo(id=name, description=desc))

    return GameState(
        room=room,
        room_name=room_name,
        room_description=room_desc,
        visible_objects=visible_objects,
        inventory=inventory,
        exits=exits,
        known_entities=known_entities,
        nearby_rooms=nearby_rooms,
        vehicle=vehicle,
    )


def _format_behavior(
    verb: str, params: list[str], param_types: dict[str, str] | None = None,
) -> str:
    """Format a behavior with its parameters for agent context.

    Parameters typed as 'entity' (or untyped, which defaults to entity
    for behaviors) are prefixed with @ to signal to the agent that it
    should resolve the argument to a visible entity ID.

    Examples:
        give, [item], {}            -> "give <@item>"
        take, [], {}                -> "take"
        set-timer, [seconds], {seconds: number} -> "set-timer <seconds>"
    """
    if params:
        types = param_types or {}
        parts = []
        for p in params:
            ptype = types.get(p, "entity")  # Default to entity for behaviors
            if ptype == "entity":
                parts.append(f"<@{p}>")
            else:
                parts.append(f"<{p}>")
        param_str = " ".join(parts)
        return f"{verb} {param_str}"
    return verb


def _get_object_info_with_contents(
    runtime: "GrueRuntime", obj_name: str, visible_set: set[str]
) -> ObjectInfo:
    """Get object info including available behaviors and nested contents."""
    desc = runtime.get_object_description(obj_name)

    # Get ldesc for natural room listings (evaluates dynamic :describe behavior)
    ldesc = runtime.get_object_fdesc(obj_name)

    # Get behaviors from world definition
    # Track verb -> formatted string (with params)
    behavior_map: dict[str, str] = {}
    if obj_name in runtime.world.objects:
        obj_def = runtime.world.objects[obj_name]
        for b in obj_def.behaviors:
            # Skip internal behaviors (on-enter, describe, etc.)
            if not b.verb.startswith("on-") and b.verb not in ("describe", "through"):
                behavior_map[b.verb] = _format_behavior(
                    b.verb, b.params, b.param_types,
                )

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
        # The player rides vehicles and stands in rooms; never list them as the
        # "contents" of a container/vehicle (gnusto-f16b).
        if name == runtime.player_name:
            continue
        if obj_state.location == obj_name and runtime.is_visible(name):
            child_info = _get_object_info_with_contents(runtime, name, visible_set)
            contents.append(child_info)

    # Read :nodesc from the raw props dict (NOT get_object_property, which is
    # strict and raises on undeclared reads). Drives room-listing suppression
    # while leaving the object interactable for NL resolution.
    obj_state = runtime.state.objects.get(obj_name)
    nodesc = bool(obj_state.properties.get("nodesc", False)) if obj_state else False

    return ObjectInfo(
        id=obj_name,
        description=desc,
        ldesc=ldesc,
        behaviors=sorted(behavior_map.values()),
        contents=contents,
        nodesc=nodesc,
    )
