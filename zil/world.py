"""
ZIL World Model

A simulation of game world state that can be used by an LLM
to understand and interact with the game.
"""

from dataclasses import dataclass, field
from typing import Any

from .extractor import GameData, ZILObject


@dataclass
class ObjectState:
    """Runtime state of a game object."""

    name: str
    location: str | None = None  # Where the object currently is
    flags: set[str] = field(default_factory=set)
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldState:
    """
    Complete state of the game world.

    This captures everything needed to understand and simulate
    the current game state.
    """

    # Current location
    current_room: str = ""

    # Player inventory (objects the player is carrying)
    inventory: list[str] = field(default_factory=list)

    # State of all objects
    objects: dict[str, ObjectState] = field(default_factory=dict)

    # Global variables
    globals: dict[str, Any] = field(default_factory=dict)

    # Score and moves
    score: int = 0
    moves: int = 0

    # Whether the current room is lit
    is_lit: bool = True


class World:
    """
    Game world manager.

    Provides methods to query and modify world state,
    and to generate context for LLM interactions.
    """

    def __init__(self, game_data: GameData):
        self.data = game_data
        self.state = WorldState()
        self._initialize_state()

    def _initialize_state(self) -> None:
        """Set up initial world state from game data."""
        # Initialize objects from game data
        for name, obj in self.data.objects.items():
            state = ObjectState(name=name)

            # Set initial location
            in_prop = obj.get_property_values("IN")
            if in_prop:
                state.location = in_prop[0] if isinstance(in_prop[0], str) else None

            # Set initial flags
            flags = obj.get_property_values("FLAGS")
            state.flags = set(flags)

            self.state.objects[name] = state

        # Initialize rooms as objects too (for containment tracking)
        for name, room in self.data.rooms.items():
            state = ObjectState(name=name)
            flags = room.get_property_values("FLAGS")
            state.flags = set(flags)
            self.state.objects[name] = state

        # Set starting location (look for common starting room patterns)
        # Many games start in a room with specific names
        starting_candidates = [
            "TERMINAL-ROOM",  # Lurking Horror starts here
            "WEST-OF-HOUSE",  # Zork
            "LIVING-ROOM",
            "START",
        ]
        for candidate in starting_candidates:
            if candidate in self.data.rooms:
                self.state.current_room = candidate
                break

        # Initialize globals
        for name, glob in self.data.globals.items():
            self.state.globals[name] = glob.value

    def get_room(self, name: str) -> ZILObject | None:
        """Get a room definition."""
        return self.data.rooms.get(name)

    def get_object(self, name: str) -> ZILObject | None:
        """Get an object definition."""
        return self.data.objects.get(name)

    def get_object_state(self, name: str) -> ObjectState | None:
        """Get the current state of an object."""
        return self.state.objects.get(name)

    def get_current_room(self) -> ZILObject | None:
        """Get the current room definition."""
        return self.get_room(self.state.current_room)

    def get_objects_in_room(self, room_name: str | None = None) -> list[str]:
        """Get all objects in a room (excluding invisible/player objects)."""
        if room_name is None:
            room_name = self.state.current_room

        objects = []
        for name, state in self.state.objects.items():
            if state.location == room_name:
                # Skip the player and invisible objects
                if name == "PLAYER" or "INVISIBLE" in state.flags:
                    continue
                # Skip objects with NDESCBIT (not described)
                if "NDESCBIT" in state.flags:
                    continue
                objects.append(name)
        return objects

    def get_visible_objects(self) -> list[str]:
        """Get objects visible to the player (in room or inventory)."""
        visible = self.get_objects_in_room()
        visible.extend(self.state.inventory)
        return visible

    def get_room_exits(self, room_name: str | None = None) -> dict[str, Any]:
        """Get available exits from a room."""
        if room_name is None:
            room_name = self.state.current_room

        room = self.get_room(room_name)
        if not room:
            return {}

        exits = {}
        for direction in self.data.directions:
            exit_info = room.get_property_values(direction)
            if exit_info:
                exits[direction] = exit_info
        return exits

    def can_go(self, direction: str) -> tuple[bool, str]:
        """
        Check if player can go in a direction.

        Returns (can_go, destination_or_message)
        """
        room = self.get_current_room()
        if not room:
            return False, "You're not in a valid location."

        exit_info = room.get_property_values(direction)
        if not exit_info:
            return False, f"You can't go {direction.lower()}."

        # Parse exit info: [TO, ROOM] or [PER, ROUTINE] or [string message]
        if len(exit_info) >= 2:
            if exit_info[0] == "TO":
                return True, exit_info[1]
            elif exit_info[0] == "PER":
                # Conditional exit - would need routine evaluation
                return True, f"(conditional: {exit_info[1]})"
            elif exit_info[0] == "IF":
                # Conditional: IF DOOR IS OPEN
                return True, f"(conditional: {' '.join(str(x) for x in exit_info)})"

        # Single string is usually a blocking message
        if len(exit_info) == 1 and isinstance(exit_info[0], str):
            return False, exit_info[0]

        return False, f"Exit blocked: {exit_info}"

    def move_player(self, direction: str) -> tuple[bool, str]:
        """
        Move the player in a direction.

        Returns (success, message)
        """
        can_move, result = self.can_go(direction)
        if not can_move:
            return False, result

        # If result is a known room, move there
        if result in self.data.rooms:
            self.state.current_room = result
            self.state.moves += 1
            return True, f"You go {direction.lower()}."

        # Conditional exits need routine evaluation
        if result.startswith("(conditional:"):
            return False, f"The exit requires game logic evaluation: {result}"

        return False, result

    def take_object(self, obj_name: str) -> tuple[bool, str]:
        """
        Try to take an object.

        Returns (success, message)
        """
        obj = self.get_object(obj_name)
        obj_state = self.get_object_state(obj_name)

        if not obj or not obj_state:
            return False, f"There's no {obj_name} here."

        if obj_state.location != self.state.current_room:
            return False, f"You don't see any {obj_name} here."

        if "TAKEBIT" not in obj_state.flags:
            return False, f"You can't take the {obj_name}."

        # Move to inventory
        obj_state.location = "PLAYER"
        self.state.inventory.append(obj_name)
        return True, f"Taken."

    def drop_object(self, obj_name: str) -> tuple[bool, str]:
        """
        Try to drop an object.

        Returns (success, message)
        """
        if obj_name not in self.state.inventory:
            return False, f"You're not carrying the {obj_name}."

        obj_state = self.get_object_state(obj_name)
        if obj_state:
            obj_state.location = self.state.current_room
            self.state.inventory.remove(obj_name)
            return True, "Dropped."
        return False, "Something went wrong."

    def describe_room(self) -> str:
        """Generate a description of the current room."""
        room = self.get_current_room()
        if not room:
            return "You are nowhere."

        lines = []

        # Room name
        name = room.get_property_value("DESC", self.state.current_room)
        lines.append(f"**{name}**")

        # Room description
        ldesc = room.get_property_value("LDESC")
        if ldesc:
            lines.append(ldesc)

        # Objects in room
        objects = self.get_objects_in_room()
        if objects:
            lines.append("")
            for obj_name in objects:
                obj = self.get_object(obj_name)
                if obj:
                    obj_desc = obj.get_property_value("DESC", obj_name)
                    fdesc = obj.get_property_value("FDESC")
                    if fdesc:
                        lines.append(fdesc)
                    else:
                        lines.append(f"There is a {obj_desc} here.")

        # Exits
        exits = self.get_room_exits()
        if exits:
            exit_dirs = [d.lower() for d in exits.keys() if self.can_go(d)[0]]
            if exit_dirs:
                lines.append(f"\nExits: {', '.join(exit_dirs)}")

        return "\n".join(lines)

    def describe_inventory(self) -> str:
        """Generate inventory description."""
        if not self.state.inventory:
            return "You are empty-handed."

        lines = ["You are carrying:"]
        for obj_name in self.state.inventory:
            obj = self.get_object(obj_name)
            if obj:
                desc = obj.get_property_value("DESC", obj_name)
                lines.append(f"  - {desc}")
        return "\n".join(lines)

    def get_valid_verbs(self) -> list[str]:
        """Get list of valid verbs from syntax definitions."""
        verbs = set()
        for syn in self.data.syntax:
            if syn.verb:
                verbs.add(syn.verb)
        return sorted(verbs)

    def get_context_for_llm(self) -> dict:
        """
        Generate a context dict for LLM interaction.

        This provides all the information an LLM needs to understand
        the current game state and make decisions.
        """
        room = self.get_current_room()
        exits = self.get_room_exits()
        objects_here = self.get_objects_in_room()

        # Get object details
        object_details = []
        for obj_name in objects_here:
            obj = self.get_object(obj_name)
            state = self.get_object_state(obj_name)
            if obj and state:
                object_details.append(
                    {
                        "name": obj_name,
                        "description": obj.get_property_value("DESC", obj_name),
                        "flags": list(state.flags),
                        "takeable": "TAKEBIT" in state.flags,
                    }
                )

        return {
            "room": {
                "name": self.state.current_room,
                "description": room.get_property_value("DESC") if room else None,
                "long_description": room.get_property_value("LDESC") if room else None,
            },
            "exits": {
                dir: {"destination": self.can_go(dir)[1], "accessible": self.can_go(dir)[0]}
                for dir in exits.keys()
            },
            "objects_here": object_details,
            "inventory": self.state.inventory,
            "score": self.state.score,
            "moves": self.state.moves,
            "valid_directions": list(self.data.directions),
        }
