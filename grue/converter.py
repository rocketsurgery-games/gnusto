"""
ZIL-to-GRUE Converter

Converts parsed ZIL game data into GRUE format for manual refinement.

The converter extracts:
- Room definitions with exits
- Object definitions with flags, locations, properties
- ZIL source as comments for objects with ACTION routines

The output is designed to be refined by an LLM to add behavioral logic.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO
import io

from zil.ast import ASTNode, Atom, Number, String, Form, List
from zil.extractor import GameData, ZILObject, Routine


# Direction properties that map to exits
DIRECTION_PROPERTIES = {
    "NORTH", "SOUTH", "EAST", "WEST",
    "NE", "NW", "SE", "SW",
    "UP", "DOWN", "IN", "OUT",
}

# Properties to skip when extracting (handled specially or not needed)
SKIP_PROPERTIES = {
    "IN",  # Container/location - handled separately
    "DESC",  # Description - handled separately
    "LDESC", "FDESC",  # Long/first descriptions
    "FLAGS",  # Flags - handled separately
    "SYNONYM", "ADJECTIVE",  # Word lists - handled separately
    "ACTION", "GENERIC",  # Action routines - handled via ZIL source
    "GLOBAL", "THINGS",  # Meta properties
    # Direction properties
    "NORTH", "SOUTH", "EAST", "WEST",
    "NE", "NW", "SE", "SW",
    "UP", "DOWN", "IN", "OUT", "LAND",
}


def ast_to_zil(node: ASTNode, indent: int = 0) -> str:
    """Convert ZIL AST node back to readable ZIL source."""
    if isinstance(node, Atom):
        return node.name
    elif isinstance(node, Number):
        return str(node.value)
    elif isinstance(node, String):
        # Escape quotes in string
        escaped = node.value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    elif isinstance(node, Form):
        if not node.elements:
            return "<>"
        parts = [ast_to_zil(e, indent) for e in node.elements]
        content = " ".join(parts)
        # Format nicely for complex forms
        if len(content) > 60 or any(isinstance(e, (Form, List)) and len(e.elements) > 2 for e in node.elements):
            inner_indent = "  " * (indent + 1)
            formatted_parts = [ast_to_zil(e, indent + 1) for e in node.elements]
            if len(node.elements) > 1:
                first = formatted_parts[0]
                rest = [f"\n{inner_indent}{p}" for p in formatted_parts[1:]]
                return "<" + first + "".join(rest) + ">"
        return "<" + content + ">"
    elif isinstance(node, List):
        if not node.elements:
            return "()"
        parts = [ast_to_zil(e, indent) for e in node.elements]
        return "(" + " ".join(parts) + ")"
    else:
        return str(node)


def routine_to_zil(routine: Routine) -> str:
    """Convert a Routine back to ZIL source."""
    lines = []

    # Build argument spec
    arg_parts = []
    if routine.args:
        arg_parts.extend(routine.args)
    if routine.aux_vars:
        arg_parts.append('"AUX"')
        arg_parts.extend(routine.aux_vars)
    if routine.optional_args:
        arg_parts.append('"OPT"')
        arg_parts.extend(routine.optional_args)

    arg_spec = " ".join(arg_parts) if arg_parts else ""
    lines.append(f"<ROUTINE {routine.name} ({arg_spec})")

    # Format body
    for form in routine.body:
        body_zil = ast_to_zil(form, indent=1)
        # Indent each line
        for line in body_zil.split("\n"):
            lines.append("  " + line)

    lines.append(">")
    return "\n".join(lines)


@dataclass
class ConversionResult:
    """Result of ZIL to GRUE conversion."""
    grue_source: str
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)


class ZILtoGRUEConverter:
    """Convert ZIL GameData to GRUE format."""

    def __init__(self, game_data: GameData):
        self.data = game_data
        self.warnings: list[str] = []
        self.out: TextIO = io.StringIO()

    def convert(
        self,
        name: str = "Converted Game",
        description: str = "",
        starting_room: str | None = None,
    ) -> ConversionResult:
        """
        Convert GameData to GRUE source.

        Args:
            name: Game name
            description: Game description
            starting_room: Starting room (auto-detected if None)
        """
        self.out = io.StringIO()
        self.warnings = []

        # Header
        self._write_header(name, description)

        # World form
        self._emit("(world")
        self._emit(f'  :name "{name}"')
        if description:
            self._emit(f'  :description "{description}")')
        else:
            self._emit(")")
        self._emit("")

        # Player
        start = starting_room or self._detect_starting_room()
        self._emit("; === PLAYER ===")
        self._emit("")
        self._emit("(object PLAYER")
        self._emit(f"  :location {start}")
        self._emit("  :flags (PERSON))")
        self._emit("")

        # Rooms
        self._emit("; === ROOMS ===")
        self._emit("")
        rooms_count = 0
        for name, room in sorted(self.data.rooms.items()):
            self._convert_room(room)
            rooms_count += 1

        # Objects
        self._emit("; === OBJECTS ===")
        self._emit("")
        objects_count = 0
        objects_with_actions = 0
        for name, obj in sorted(self.data.objects.items()):
            has_action = self._convert_object(obj)
            objects_count += 1
            if has_action:
                objects_with_actions += 1

        # Collect stats
        stats = {
            "rooms": rooms_count,
            "objects": objects_count,
            "objects_with_actions": objects_with_actions,
        }

        return ConversionResult(
            grue_source=self.out.getvalue(),
            warnings=self.warnings,
            stats=stats,
        )

    def _emit(self, line: str) -> None:
        """Emit a line to the output."""
        self.out.write(line + "\n")

    def _write_header(self, name: str, description: str) -> None:
        """Write file header comment."""
        self._emit(f"; {name}")
        self._emit("; Converted from ZIL source")
        if description:
            self._emit(f"; {description}")
        self._emit(";")
        self._emit("; Objects marked [NEEDS-TRANSLATION] have ZIL source that needs")
        self._emit("; to be converted to GRUE behaviors by an LLM or human.")
        self._emit("")

    def _detect_starting_room(self) -> str:
        """Detect the starting room."""
        for name in ["WEST-OF-HOUSE", "LIVING-ROOM", "START", "TERMINAL-ROOM"]:
            if name in self.data.rooms:
                return name
        if self.data.rooms:
            return next(iter(self.data.rooms.keys()))
        return "START"

    def _convert_room(self, room: ZILObject) -> None:
        """Convert a room to GRUE."""
        self._emit(f"(room {room.name}")

        # Description
        desc = room.get_property_value("DESC")
        if desc:
            self._emit(f'  :description "{self._escape_string(str(desc))}"')

        # Flags
        flags = room.get_property_values("FLAGS")
        if flags:
            flag_str = " ".join(str(f) for f in flags)
            self._emit(f"  :flags ({flag_str})")

        # Exits
        exits = self._extract_exits(room)
        if exits:
            self._emit("  :exits")
            self._emit("    (")
            for direction, dest in exits:
                self._emit(f"      ({direction} :to {dest})")
            self._emit("    )")

        self._emit(")")
        self._emit("")

    def _extract_exits(self, room: ZILObject) -> list[tuple[str, str]]:
        """Extract simple exits from a room."""
        exits = []

        for direction in DIRECTION_PROPERTIES:
            prop = room.get_property(direction)
            if not prop or not prop.values:
                continue

            first_val = prop.values[0]

            # Skip IN if it's the container property
            if direction == "IN":
                if first_val in ("ROOMS", "LOCAL-GLOBALS"):
                    continue

            direction_lower = direction.lower()

            # Simple exit: (NORTH TO ROOM-NAME)
            if first_val == "TO" and len(prop.values) >= 2:
                dest = str(prop.values[1])
                exits.append((direction_lower, dest))
            # Direct room reference
            elif isinstance(first_val, str) and first_val in self.data.rooms:
                exits.append((direction_lower, first_val))
            # PER routine - add warning
            elif first_val == "PER":
                routine = prop.values[1] if len(prop.values) > 1 else "?"
                self.warnings.append(
                    f"Room {room.name}: {direction} uses PER {routine} (needs manual handling)"
                )

        return exits

    def _convert_object(self, obj: ZILObject) -> bool:
        """Convert an object to GRUE. Returns True if it has an ACTION routine."""
        action_routine = obj.get_property_value("ACTION")
        has_action = action_routine is not None

        if has_action:
            self._emit(f"; [NEEDS-TRANSLATION] {obj.name}")

        self._emit(f"(object {obj.name}")

        # Description
        desc = obj.get_property_value("DESC")
        if desc:
            self._emit(f'  :description "{self._escape_string(str(desc))}"')

        # Location
        loc = obj.get_property_value("IN")
        if loc and loc not in ("ROOMS", "LOCAL-GLOBALS", "GLOBAL-OBJECTS"):
            self._emit(f"  :location {loc}")

        # Flags
        flags = obj.get_property_values("FLAGS")
        if flags:
            flag_str = " ".join(str(f) for f in flags)
            self._emit(f"  :flags ({flag_str})")

        # Properties (non-standard ones)
        extra_props = []
        for prop_name, prop in obj.properties.items():
            if prop_name not in SKIP_PROPERTIES:
                if prop.values:
                    val = prop.values[0] if len(prop.values) == 1 else prop.values
                    extra_props.append((prop_name.lower(), val))

        if extra_props:
            self._emit("  :properties")
            self._emit("    (")
            for prop_name, val in extra_props:
                if isinstance(val, str):
                    self._emit(f'      ({prop_name} "{self._escape_string(val)}")')
                elif isinstance(val, list):
                    val_str = " ".join(str(v) for v in val)
                    self._emit(f"      ({prop_name} {val_str})")
                else:
                    self._emit(f"      ({prop_name} {val})")
            self._emit("    )")

        # If has action routine, include ZIL source as comment
        if has_action and action_routine in self.data.routines:
            routine = self.data.routines[action_routine]
            zil_source = routine_to_zil(routine)

            self._emit("")
            self._emit("  ; --- ZIL Source ---")
            for line in zil_source.split("\n"):
                self._emit(f"  ; {line}")
            self._emit("  ; --- End ZIL Source ---")
            self._emit("")
            self._emit("  :behaviors")
            self._emit("    (; TODO: Translate from ZIL source above")
            self._emit("    )")

        self._emit(")")
        self._emit("")

        return has_action

    def _escape_string(self, s: str) -> str:
        """Escape a string for GRUE output."""
        return s.replace("\\", "\\\\").replace('"', '\\"')


def convert_zil_to_grue(
    game_data: GameData,
    name: str = "Converted Game",
    description: str = "",
    starting_room: str | None = None,
) -> ConversionResult:
    """
    Convert ZIL GameData to GRUE source.

    Args:
        game_data: Extracted ZIL game data
        name: Game name
        description: Game description
        starting_room: Starting room (auto-detected if None)

    Returns:
        ConversionResult with GRUE source and warnings
    """
    converter = ZILtoGRUEConverter(game_data)
    return converter.convert(name, description, starting_room)
