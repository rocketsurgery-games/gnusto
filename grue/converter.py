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
class ExitInfo:
    """Information about a room exit."""
    direction: str
    to: str
    via: str | None = None  # Door object for IF X IS OPEN
    per: str | None = None  # PER routine name


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
        self.referenced_routines: set[str] = set()  # Track routines we've emitted

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

        # Unreferenced routines
        unreferenced_count = self._emit_unreferenced_routines()

        # Reference sections (syntax, globals, constants)
        self._emit_syntax_reference()
        self._emit_globals_reference()
        self._emit_constants_reference()

        # Collect stats
        stats = {
            "rooms": rooms_count,
            "objects": objects_count,
            "objects_with_actions": objects_with_actions,
            "unreferenced_routines": unreferenced_count,
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
        exits = self._extract_exits(room)
        per_routines = [e.per for e in exits if e.per]
        action_routine = room.get_property_value("ACTION")

        # Add [NEEDS-TRANSLATION] marker if room has ACTION or PER exits
        needs_translation = []
        if action_routine:
            needs_translation.append(f"ACTION {action_routine}")
        if per_routines:
            needs_translation.append("PER exits")
        if needs_translation:
            self._emit(f"; [NEEDS-TRANSLATION] Room {room.name}: {', '.join(needs_translation)}")

        self._emit(f"(room {room.name}")

        # Description
        desc = room.get_property_value("DESC")
        if desc:
            self._emit(f'  :description "{self._escape_string(str(desc))}"')

        # Long description
        ldesc = room.get_property_value("LDESC")
        if ldesc:
            self._emit(f'  :ldesc "{self._escape_string(str(ldesc))}"')

        # Flags
        flags = room.get_property_values("FLAGS")
        if flags:
            flag_str = " ".join(str(f) for f in flags)
            self._emit(f"  :flags ({flag_str})")

        # Exits
        if exits:
            self._emit("  :exits")
            self._emit("    (")
            for exit_info in exits:
                exit_parts = [f"{exit_info.direction} :to {exit_info.to}"]
                if exit_info.via:
                    exit_parts.append(f":via {exit_info.via}")
                if exit_info.per:
                    exit_parts.append(f":per {exit_info.per}")
                self._emit(f"      ({' '.join(exit_parts)})")
            self._emit("    )")

        # Include PER routine sources as comments (deduplicated)
        if per_routines:
            unique_routines = list(dict.fromkeys(per_routines))  # Preserve order, dedupe
            self._emit("")
            self._emit("  ; --- PER Exit Routines ---")
            for routine_name in unique_routines:
                self.referenced_routines.add(routine_name)
                routine = self.data.routines.get(routine_name)
                if routine:
                    zil_source = routine_to_zil(routine)
                    for line in zil_source.split("\n"):
                        self._emit(f"  ; {line}")
                    self._emit("  ;")
            self._emit("  ; --- End PER Exit Routines ---")

        # Include room ACTION routine source as comment
        if action_routine and action_routine in self.data.routines:
            self.referenced_routines.add(action_routine)
            routine = self.data.routines[action_routine]
            zil_source = routine_to_zil(routine)
            self._emit("")
            self._emit("  ; --- Room ACTION Routine ---")
            for line in zil_source.split("\n"):
                self._emit(f"  ; {line}")
            self._emit("  ; --- End Room ACTION Routine ---")

        self._emit(")")
        self._emit("")

    def _extract_exits(self, room: ZILObject) -> list[ExitInfo]:
        """Extract exits from a room, including conditional and PER exits."""
        exits = []

        for direction in DIRECTION_PROPERTIES:
            prop = room.get_property(direction)
            if not prop or not prop.values:
                continue

            values = prop.values
            first_val = values[0]

            # Skip IN if it's the container property
            if direction == "IN":
                if first_val in ("ROOMS", "LOCAL-GLOBALS"):
                    continue

            direction_lower = direction.lower()

            # Pattern: (DIRECTION TO ROOM-NAME)
            if first_val == "TO" and len(values) >= 2:
                dest = str(values[1])
                via = None

                # Check for conditional: (DIRECTION TO ROOM IF DOOR IS OPEN)
                # values = ['TO', 'ROOM', 'IF', 'DOOR', 'IS', 'OPEN']
                if len(values) >= 6 and values[2] == "IF" and values[4] == "IS":
                    door = str(values[3])
                    state = str(values[5])
                    if state == "OPEN":
                        via = door
                    else:
                        self.warnings.append(
                            f"Room {room.name}: {direction} has condition '{door} IS {state}' (non-OPEN not supported)"
                        )

                exits.append(ExitInfo(direction=direction_lower, to=dest, via=via))

            # Pattern: (DIRECTION ROOM-NAME) - direct reference
            elif isinstance(first_val, str) and first_val in self.data.rooms:
                exits.append(ExitInfo(direction=direction_lower, to=first_val))

            # Pattern: (DIRECTION PER ROUTINE)
            elif first_val == "PER" and len(values) >= 2:
                routine_name = str(values[1])
                # Try to find destination from routine if it's simple
                dest = self._infer_per_destination(routine_name)
                exits.append(ExitInfo(direction=direction_lower, to=dest, per=routine_name))

            # Pattern: (DIRECTION NEXIT) - blocked exit
            elif first_val == "NEXIT":
                # NEXIT means "no exit in this direction" - skip it
                pass

            # Pattern: (DIRECTION SORRY ...) - blocked with message
            elif first_val == "SORRY":
                # SORRY is a blocked exit with a message - skip for now
                pass

            # Pattern: (DIRECTION "message") - blocked with message string
            # Strings with spaces are messages, not room names
            elif isinstance(first_val, str) and " " in first_val:
                # This is a blocked exit with a message - skip for now
                pass
            elif len(values) == 1 and first_val not in self.data.rooms:
                # Single value that's not a room - likely a blocked message or constant
                pass

            else:
                self.warnings.append(
                    f"Room {room.name}: {direction} has unrecognized pattern: {values[:3]}..."
                )

        return exits

    def _infer_per_destination(self, routine_name: str) -> str:
        """Try to infer destination from a PER routine. Returns '?' if unknown."""
        routine = self.data.routines.get(routine_name)
        if not routine:
            return "?"

        # Look for simple patterns like <ELSE ,ROOM-NAME> at end of routine
        # This is a heuristic - complex routines may have multiple destinations
        for form in reversed(routine.body):
            dest = self._find_room_in_form(form)
            if dest:
                return dest

        return "?"

    def _find_room_in_form(self, node: ASTNode) -> str | None:
        """Recursively search for a room reference in a form."""
        if isinstance(node, Atom):
            # Check if this atom is a room reference (with or without comma prefix)
            name = node.name
            if name.startswith(","):
                name = name[1:]
            if name in self.data.rooms:
                return name
        elif isinstance(node, (Form, List)):
            # Search through Form and List elements
            for elem in node.elements:
                result = self._find_room_in_form(elem)
                if result:
                    return result
        return None

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

        # First description (shown before object is moved/taken)
        fdesc = obj.get_property_value("FDESC")
        if fdesc:
            self._emit(f'  :fdesc "{self._escape_string(str(fdesc))}"')

        # Long description
        ldesc = obj.get_property_value("LDESC")
        if ldesc:
            self._emit(f'  :ldesc "{self._escape_string(str(ldesc))}"')

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
            self.referenced_routines.add(action_routine)
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

    def _emit_unreferenced_routines(self) -> int:
        """Emit unreferenced routines as comments. Returns count."""
        unreferenced = [
            name for name in self.data.routines.keys()
            if name not in self.referenced_routines
        ]

        if not unreferenced:
            return 0

        self._emit("; === UNREFERENCED ROUTINES ===")
        self._emit("; These routines are not directly tied to rooms or objects.")
        self._emit("; They may be utility functions, event handlers, or game logic.")
        self._emit("")

        for routine_name in sorted(unreferenced):
            routine = self.data.routines[routine_name]
            zil_source = routine_to_zil(routine)
            self._emit(f"; --- {routine_name} ---")
            for line in zil_source.split("\n"):
                self._emit(f"; {line}")
            self._emit("")

        return len(unreferenced)

    def _emit_syntax_reference(self) -> None:
        """Emit syntax definitions as reference comments."""
        if not self.data.syntax:
            return

        self._emit("; === SYNTAX REFERENCE ===")
        self._emit("; Verb patterns defining valid command structures.")
        self._emit("")

        for syn in self.data.syntax:
            # Format: VERB pattern -> ACTION
            pattern_str = " ".join(str(p) for p in syn.pattern) if syn.pattern else "(no args)"
            filters_str = f" [{', '.join(str(f) for f in syn.filters)}]" if syn.filters else ""
            pre_str = f" PRE={syn.pre_action}" if syn.pre_action else ""
            self._emit(f"; {syn.verb} {pattern_str}{filters_str} -> {syn.action}{pre_str}")

        self._emit("")

    def _emit_globals_reference(self) -> None:
        """Emit global variables as reference comments."""
        if not self.data.globals:
            return

        self._emit("; === GLOBALS REFERENCE ===")
        self._emit("; Game state variables.")
        self._emit("")

        for name, glob in sorted(self.data.globals.items()):
            if glob.value is None:
                value_str = "(uninitialized)"
            elif isinstance(glob.value, list):
                value_str = " ".join(str(v) for v in glob.value) if glob.value else "(empty)"
            else:
                value_str = str(glob.value)
            # Handle multi-line values by commenting each line
            lines = value_str.split("\n")
            if len(lines) == 1:
                self._emit(f"; {name} = {value_str}")
            else:
                self._emit(f"; {name} = {lines[0]}")
                for line in lines[1:]:
                    self._emit(f";   {line}")

        self._emit("")

    def _emit_constants_reference(self) -> None:
        """Emit constants as reference comments."""
        if not self.data.constants:
            return

        self._emit("; === CONSTANTS REFERENCE ===")
        self._emit("; Named constant values.")
        self._emit("")

        for name, const in sorted(self.data.constants.items()):
            self._emit(f"; {name} = {const.value}")

        self._emit("")

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
