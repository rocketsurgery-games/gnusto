"""
ZIL-to-DSL Converter

Converts parsed ZIL game data (ZILObject, Syntax, etc.) into DSL format
(WorldDefinition with Room, Object, Action, etc.).
"""

from dataclasses import dataclass, field
from typing import Any

from ..extractor import GameData, ZILObject, Syntax
from .world import (
    WorldDefinition,
    GameMeta,
    Room,
    Object,
    Action,
    ActionMessages,
    Exit,
)


# Direction property names in ZIL that map to exits
DIRECTION_PROPERTIES = {
    "NORTH", "SOUTH", "EAST", "WEST",
    "NE", "NW", "SE", "SW",
    "UP", "DOWN", "IN", "OUT",
    "LAND",  # For vehicles/flying
}

# Properties to skip when extracting room/object properties
SKIP_PROPERTIES = {
    "IN",  # Container/location
    "DESC",  # Description
    "LDESC",  # Long description
    "FDESC",  # First description
    "FLAGS",  # Flags
    "SYNONYM",  # Synonyms
    "ADJECTIVE",  # Adjectives
    "ACTION",  # Action routine
    "GLOBAL",  # Global objects
    "THINGS",  # Pseudo objects
    "FLOOR",  # Building floor (specific to location)
    "GENERIC",  # Generic handler
    # Direction properties
    "NORTH", "SOUTH", "EAST", "WEST",
    "NE", "NW", "SE", "SW",
    "UP", "DOWN", "IN", "OUT", "LAND",
}


@dataclass
class ConversionResult:
    """Result of converting ZIL to DSL."""
    world: WorldDefinition
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ZILtoDSLConverter:
    """Converts ZIL GameData to DSL WorldDefinition."""

    def __init__(self, game_data: GameData):
        self.data = game_data
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def convert(
        self,
        name: str = "Converted Game",
        author: str = "Unknown",
        starting_room: str | None = None,
    ) -> ConversionResult:
        """
        Convert GameData to WorldDefinition.

        Args:
            name: Game name for meta
            author: Author name for meta
            starting_room: Override starting room (auto-detected if None)
        """
        # Build world definition
        world = WorldDefinition(
            meta=GameMeta(
                name=name,
                author=author,
                starting_room=starting_room or self._detect_starting_room(),
            ),
            rooms=self._convert_rooms(),
            objects=self._convert_objects(),
            actions=self._convert_actions(),
            globals=self._convert_globals(),
        )

        return ConversionResult(
            world=world,
            warnings=self.warnings,
            errors=self.errors,
        )

    def _detect_starting_room(self) -> str:
        """Try to detect starting room from game data."""
        # Common starting room names
        for name in ["WEST-OF-HOUSE", "LIVING-ROOM", "START", "TERMINAL-ROOM"]:
            if name in self.data.rooms:
                return name

        # Return first room if any exist
        if self.data.rooms:
            return next(iter(self.data.rooms.keys()))

        return "START"

    def _convert_rooms(self) -> dict[str, Room]:
        """Convert ZIL rooms to DSL rooms."""
        rooms: dict[str, Room] = {}

        for name, zil_room in self.data.rooms.items():
            room = self._convert_room(zil_room)
            rooms[name] = room

        return rooms

    def _convert_room(self, zil_room: ZILObject) -> Room:
        """Convert a single ZIL room to DSL room."""
        room = Room(name=zil_room.name)

        # Description
        desc = zil_room.get_property_value("DESC")
        if desc:
            room.description = str(desc)

        # Long description (LDESC or FDESC)
        ldesc = zil_room.get_property_value("LDESC") or zil_room.get_property_value("FDESC")
        if ldesc:
            room.long_description = str(ldesc)

        # Flags
        flags = zil_room.get_property_values("FLAGS")
        room.flags = [str(f) for f in flags]

        # Exits
        room.exits = self._extract_exits(zil_room)

        # Additional properties
        for prop_name, prop in zil_room.properties.items():
            if prop_name not in SKIP_PROPERTIES:
                if len(prop.values) == 1:
                    room.properties[prop_name] = prop.values[0]
                elif prop.values:
                    room.properties[prop_name] = prop.values

        return room

    def _extract_exits(self, zil_room: ZILObject) -> dict[str, Exit]:
        """Extract exits from ZIL room properties."""
        exits: dict[str, Exit] = {}

        for direction in DIRECTION_PROPERTIES:
            prop = zil_room.get_property(direction)
            if not prop or not prop.values:
                continue

            # Skip IN if it's the container property (IN ROOMS)
            if direction == "IN":
                first_val = prop.values[0]
                if first_val == "ROOMS" or first_val == "LOCAL-GLOBALS":
                    continue  # This is the container, not an exit

            direction_lower = direction.lower()
            first_val = prop.values[0]

            # Simple exit: (NORTH TO ROOM-NAME)
            if first_val == "TO" and len(prop.values) >= 2:
                dest = prop.values[1]
                exits[direction_lower] = Exit(to=str(dest))

            # Exit with condition: (NORTH PER ROUTINE)
            elif first_val == "PER":
                # This is a conditional exit handled by a routine
                # We skip these - they need manual analysis of the routine
                if len(prop.values) >= 2:
                    routine_name = prop.values[1]
                    self.warnings.append(
                        f"Room {zil_room.name}: {direction} exit uses PER {routine_name}, "
                        "requires manual conversion (skipped)"
                    )
                    # Don't create exit - destination unknown

            # Blocked exit with message: (NORTH "You can't go that way.")
            elif isinstance(first_val, str) and first_val.startswith('"'):
                # This is a blocked direction with a message
                # In DSL, this would be a transition that blocks with message
                self.warnings.append(
                    f"Room {zil_room.name}: {direction} is blocked with message, "
                    "needs transition in DSL"
                )

            # Direct room reference (rare): (NORTH ROOM-NAME)
            elif isinstance(first_val, str) and not first_val.startswith('"'):
                # Check if it's a known room
                if first_val in self.data.rooms:
                    exits[direction_lower] = Exit(to=first_val)
                else:
                    # Might be a message or other construct
                    self.warnings.append(
                        f"Room {zil_room.name}: {direction} has unclear value {first_val}"
                    )

        return exits

    def _convert_objects(self) -> dict[str, Object]:
        """Convert ZIL objects to DSL objects."""
        objects: dict[str, Object] = {}

        for name, zil_obj in self.data.objects.items():
            obj = self._convert_object(zil_obj)
            objects[name] = obj

        return objects

    def _convert_object(self, zil_obj: ZILObject) -> Object:
        """Convert a single ZIL object to DSL object."""
        obj = Object(name=zil_obj.name)

        # Description
        desc = zil_obj.get_property_value("DESC")
        if desc:
            obj.description = str(desc)

        # Long description
        ldesc = zil_obj.get_property_value("LDESC") or zil_obj.get_property_value("FDESC")
        if ldesc:
            obj.long_description = str(ldesc)

        # Initial location
        loc = zil_obj.get_property_value("IN")
        if loc:
            obj.initial_location = str(loc)

        # Flags
        flags = zil_obj.get_property_values("FLAGS")
        obj.flags = [str(f) for f in flags]

        # Synonyms
        synonyms = zil_obj.get_property_values("SYNONYM")
        obj.synonyms = [str(s) for s in synonyms]

        # Adjectives
        adjectives = zil_obj.get_property_values("ADJECTIVE")
        obj.adjectives = [str(a) for a in adjectives]

        # Additional properties
        for prop_name, prop in zil_obj.properties.items():
            if prop_name not in SKIP_PROPERTIES:
                if len(prop.values) == 1:
                    obj.properties[prop_name] = prop.values[0]
                elif prop.values:
                    obj.properties[prop_name] = prop.values

        return obj

    def _convert_actions(self) -> dict[str, Action]:
        """
        Convert ZIL SYNTAX definitions to DSL actions.

        Groups syntax entries by action routine and builds Action objects.
        """
        # Group syntaxes by action routine
        action_syntaxes: dict[str, list[Syntax]] = {}
        for syntax in self.data.syntax:
            if syntax.action:
                action_name = self._normalize_action_name(syntax.action)
                if action_name not in action_syntaxes:
                    action_syntaxes[action_name] = []
                action_syntaxes[action_name].append(syntax)

        # Build actions
        actions: dict[str, Action] = {}
        for action_name, syntaxes in action_syntaxes.items():
            action = self._build_action(action_name, syntaxes)
            actions[action_name] = action

        return actions

    def _normalize_action_name(self, routine_name: str) -> str:
        """Normalize action routine name to action name."""
        # Remove V- prefix common in Infocom games
        if routine_name.startswith("V-"):
            return routine_name[2:]
        return routine_name

    def _build_action(self, name: str, syntaxes: list[Syntax]) -> Action:
        """Build an Action from a list of syntax definitions."""
        action = Action(name=name)

        # Build syntax patterns
        for syntax in syntaxes:
            pattern = self._syntax_to_pattern(syntax)
            if pattern and pattern not in action.syntax:
                action.syntax.append(pattern)

        # Note: Preconditions and effects would need routine analysis
        # For now, we leave them empty and add a warning
        if name not in self._standard_actions():
            self.warnings.append(
                f"Action {name}: preconditions/effects need manual definition"
            )

        return action

    def _syntax_to_pattern(self, syntax: Syntax) -> str:
        """Convert ZIL syntax to DSL pattern string."""
        parts = [syntax.verb.lower()]

        for elem in syntax.pattern:
            if elem == "OBJECT":
                parts.append("[object]")
            elif elem in ("TO", "IN", "ON", "WITH", "AT", "FOR", "FROM", "ABOUT"):
                parts.append(elem.lower())
            else:
                # Other words in the pattern
                parts.append(elem.lower())

        return " ".join(parts)

    def _standard_actions(self) -> set[str]:
        """Return set of standard actions that have well-known semantics."""
        return {
            "TAKE", "DROP", "EXAMINE", "LOOK", "INVENTORY",
            "OPEN", "CLOSE", "READ", "TURN-ON", "TURN-OFF",
            "GO", "ENTER", "EXIT", "WAIT", "ATTACK",
        }

    def _convert_globals(self) -> dict[str, Any]:
        """Convert ZIL globals to DSL globals."""
        result: dict[str, Any] = {}

        for name, glob in self.data.globals.items():
            value = glob.value

            # Skip globals that are tables or complex structures
            if isinstance(value, dict) and "_form" in value:
                continue

            # Convert ZIL empty list (<>) to false
            if value == []:
                value = False

            # Skip None values
            if value is None:
                continue

            result[name] = value

        return result


def convert_zil_to_dsl(
    game_data: GameData,
    name: str = "Converted Game",
    author: str = "Unknown",
    starting_room: str | None = None,
) -> ConversionResult:
    """
    Convenience function to convert ZIL GameData to DSL.

    Args:
        game_data: Extracted ZIL game data
        name: Game name
        author: Author name
        starting_room: Starting room (auto-detected if None)

    Returns:
        ConversionResult with world definition and any warnings/errors
    """
    converter = ZILtoDSLConverter(game_data)
    return converter.convert(name, author, starting_room)
