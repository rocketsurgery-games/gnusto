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
    description: str
    behaviors: list[str] = field(default_factory=list)  # Available verbs
    properties: dict[str, Any] = field(default_factory=dict)  # Visible properties


@dataclass
class GameState:
    """Current game state for agent context."""

    room: str
    room_description: str
    visible_objects: list[ObjectInfo]
    inventory: list[ObjectInfo]
    exits: dict[str, str]
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
            exits_str = ", ".join(f"{d} -> {dest}" for d, dest in self.exits.items())
            lines.append(f"**Exits:** {exits_str}")
        else:
            lines.append("**Exits:** none")
        lines.append("")

        # Visible objects
        if self.visible_objects:
            lines.append("**Visible objects:**")
            for obj in self.visible_objects:
                behaviors_str = ", ".join(obj.behaviors) if obj.behaviors else "none"
                lines.append(f"- {obj.id}: {obj.description} [actions: {behaviors_str}]")
        else:
            lines.append("**Visible objects:** none")
        lines.append("")

        # Inventory
        if self.inventory:
            lines.append("**Inventory:**")
            for obj in self.inventory:
                lines.append(f"- {obj.id}: {obj.description}")
        else:
            lines.append("**Inventory:** empty")

        return "\n".join(lines)


def get_game_state(runtime: "GrueRuntime") -> GameState:
    """
    Extract current game state from runtime for agent context.

    Args:
        runtime: GrueRuntime instance

    Returns:
        GameState with current room, objects, inventory, exits
    """
    room = runtime.get_player_room()
    room_desc = runtime.get_room_description()
    exits = runtime.get_exits()
    vehicle = runtime.get_player_vehicle()

    # Get visible objects with their behaviors
    visible_names = runtime.get_visible_objects()
    visible_objects = []
    for name in visible_names:
        if name not in runtime.get_inventory():
            obj_info = _get_object_info(runtime, name)
            visible_objects.append(obj_info)

    # Get inventory items
    inv_names = runtime.get_inventory()
    inventory = [_get_object_info(runtime, name) for name in inv_names]

    return GameState(
        room=room,
        room_description=room_desc,
        visible_objects=visible_objects,
        inventory=inventory,
        exits=exits,
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


def _get_object_info(runtime: "GrueRuntime", obj_name: str) -> ObjectInfo:
    """Get object info including available behaviors."""
    desc = runtime.get_object_description(obj_name)

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

    return ObjectInfo(
        id=obj_name,
        description=desc,
        behaviors=sorted(behavior_map.values()),
    )
