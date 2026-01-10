"""
GRUE World Parser - Parse .grue files into WorldDefinition structures.

This parser reads GRUE S-expression world files and converts them into
the WorldDefinition dataclasses used by the runtime.

Grammar for top-level forms:
    (world :name "..." :description "...")
    (room NAME :description "..." :flags (...) :exits (...))
    (object NAME :description "..." :location LOC :flags (...) :behaviors (...))
    (victory :when EXPR :context (...))
    (defeat NAME :when EXPR :context (...))
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .sexpr import parse_all, SExpr, Symbol, Keyword, SList


class GrueParseError(Exception):
    """Error during GRUE parsing."""
    pass


@dataclass
class GrueExit:
    """An exit from a room."""
    direction: str
    to: str
    via: str | None = None  # Door/boundary object
    when: SExpr | None = None  # Optional condition


@dataclass
class GrueCase:
    """A single case in a behavior."""
    when: SExpr
    outcome: str  # "success", "blocked", "redirect"
    effects: list[SExpr] = field(default_factory=list)
    reason: str | None = None
    context: list[tuple[str, Any]] = field(default_factory=list)
    action: SExpr | None = None  # For redirects


@dataclass
class GrueBehavior:
    """A behavior definition for a specific verb."""
    verb: str
    cases: list[GrueCase] = field(default_factory=list)


@dataclass
class GrueRoom:
    """A room definition."""
    name: str
    description: str = ""
    ldesc: str = ""  # Long description
    flags: list[str] = field(default_factory=list)
    exits: list[GrueExit] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GrueObject:
    """An object definition."""
    name: str
    description: str = ""
    fdesc: str = ""  # First description (before object is moved)
    ldesc: str = ""  # Long description
    location: str | None = None
    flags: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    behaviors: list[GrueBehavior] = field(default_factory=list)


@dataclass
class GrueVictory:
    """Victory condition."""
    when: SExpr
    context: list[tuple[str, Any]] = field(default_factory=list)


@dataclass
class GrueDefeat:
    """Defeat condition."""
    name: str
    when: SExpr
    context: list[tuple[str, Any]] = field(default_factory=list)


@dataclass
class GrueWorld:
    """
    Complete GRUE world definition.
    """
    name: str = ""
    description: str = ""
    rooms: dict[str, GrueRoom] = field(default_factory=dict)
    objects: dict[str, GrueObject] = field(default_factory=dict)
    victory: GrueVictory | None = None
    defeat: dict[str, GrueDefeat] = field(default_factory=dict)


class GrueParser:
    """Parse GRUE S-expression world files."""

    def parse(self, source: str) -> GrueWorld:
        """Parse GRUE source into a GrueWorld."""
        exprs = parse_all(source)
        world = GrueWorld()

        for expr in exprs:
            self._parse_top_level(expr, world)

        return world

    def parse_file(self, path: str | Path) -> GrueWorld:
        """Parse a .grue file."""
        with open(path, "r") as f:
            return self.parse(f.read())

    def _parse_top_level(self, expr: SExpr, world: GrueWorld) -> None:
        """Parse a top-level form."""
        if not isinstance(expr, SList) or len(expr) == 0:
            raise GrueParseError(f"Expected top-level form, got {expr}")

        form = expr[0]
        if not isinstance(form, Symbol):
            raise GrueParseError(f"Expected form name, got {form}")

        name = form.name.lower()

        if name == "world":
            self._parse_world_meta(expr, world)
        elif name == "room":
            room = self._parse_room(expr)
            world.rooms[room.name] = room
        elif name == "object":
            obj = self._parse_object(expr)
            world.objects[obj.name] = obj
        elif name == "victory":
            world.victory = self._parse_victory(expr)
        elif name == "defeat":
            defeat = self._parse_defeat(expr)
            world.defeat[defeat.name] = defeat
        else:
            raise GrueParseError(f"Unknown top-level form: {name}")

    def _parse_kwargs(self, items: list[SExpr]) -> dict[str, SExpr]:
        """Parse Clojure-style keyword arguments."""
        kwargs: dict[str, SExpr] = {}
        i = 0
        while i < len(items):
            if isinstance(items[i], Keyword):
                key = items[i].name
                if i + 1 >= len(items):
                    raise GrueParseError(f"Missing value for keyword :{key}")
                kwargs[key] = items[i + 1]
                i += 2
            else:
                # Positional argument encountered - stop parsing kwargs
                break
        return kwargs

    def _parse_world_meta(self, expr: SList, world: GrueWorld) -> None:
        """Parse (world :name "..." :description "...")."""
        kwargs = self._parse_kwargs(list(expr.items[1:]))

        if "name" in kwargs:
            world.name = self._expect_string(kwargs["name"], "world name")
        if "description" in kwargs:
            world.description = self._expect_string(kwargs["description"], "world description")

    def _parse_room(self, expr: SList) -> GrueRoom:
        """Parse (room NAME :description "..." :flags (...) :exits (...))."""
        if len(expr) < 2:
            raise GrueParseError("room requires a name")

        name = self._expect_symbol(expr[1], "room name")
        room = GrueRoom(name=name)

        kwargs = self._parse_kwargs(list(expr.items[2:]))

        if "description" in kwargs:
            room.description = self._expect_string(kwargs["description"], "room description")
        if "ldesc" in kwargs:
            room.ldesc = self._expect_string(kwargs["ldesc"], "room ldesc")
        if "flags" in kwargs:
            room.flags = self._parse_flags(kwargs["flags"])
        if "exits" in kwargs:
            room.exits = self._parse_exits(kwargs["exits"])
        if "properties" in kwargs:
            room.properties = self._parse_properties(kwargs["properties"])

        return room

    def _parse_object(self, expr: SList) -> GrueObject:
        """Parse (object NAME :description "..." :location LOC :flags (...) :behaviors (...))."""
        if len(expr) < 2:
            raise GrueParseError("object requires a name")

        name = self._expect_symbol(expr[1], "object name")
        obj = GrueObject(name=name)

        kwargs = self._parse_kwargs(list(expr.items[2:]))

        if "description" in kwargs:
            obj.description = self._expect_string(kwargs["description"], "object description")
        if "fdesc" in kwargs:
            obj.fdesc = self._expect_string(kwargs["fdesc"], "object fdesc")
        if "ldesc" in kwargs:
            obj.ldesc = self._expect_string(kwargs["ldesc"], "object ldesc")
        if "location" in kwargs:
            obj.location = self._expect_symbol(kwargs["location"], "object location")
        if "flags" in kwargs:
            obj.flags = self._parse_flags(kwargs["flags"])
        if "properties" in kwargs:
            obj.properties = self._parse_properties(kwargs["properties"])
        if "behaviors" in kwargs:
            obj.behaviors = self._parse_behaviors(kwargs["behaviors"])

        return obj

    def _parse_flags(self, expr: SExpr) -> list[str]:
        """Parse a flags list like (DOOR LOCKED OPENABLE)."""
        if not isinstance(expr, SList):
            raise GrueParseError(f"Expected flags list, got {expr}")

        flags = []
        for item in expr:
            if isinstance(item, Symbol):
                flags.append(item.name)
            else:
                raise GrueParseError(f"Expected flag symbol, got {item}")
        return flags

    def _parse_exits(self, expr: SExpr) -> list[GrueExit]:
        """Parse exits like ((in :to LOBBY :via DOOR) (north :to HALLWAY))."""
        if not isinstance(expr, SList):
            raise GrueParseError(f"Expected exits list, got {expr}")

        exits = []
        for item in expr:
            if not isinstance(item, SList) or len(item) < 1:
                raise GrueParseError(f"Expected exit form, got {item}")

            direction = self._expect_symbol(item[0], "exit direction")
            kwargs = self._parse_kwargs(list(item.items[1:]))

            if "to" not in kwargs:
                raise GrueParseError(f"Exit {direction} missing :to destination")

            exit = GrueExit(
                direction=direction,
                to=self._expect_symbol(kwargs["to"], "exit destination"),
                via=self._expect_symbol(kwargs["via"], "exit via") if "via" in kwargs else None,
                when=kwargs.get("when"),
            )
            exits.append(exit)

        return exits

    def _parse_properties(self, expr: SExpr) -> dict[str, Any]:
        """Parse properties like ((key-type electronic) (locked true))."""
        if not isinstance(expr, SList):
            raise GrueParseError(f"Expected properties list, got {expr}")

        props = {}
        for item in expr:
            if not isinstance(item, SList) or len(item) < 2:
                raise GrueParseError(f"Expected (key value) property, got {item}")

            key = self._expect_symbol(item[0], "property key")
            value = self._sexpr_to_value(item[1])
            props[key] = value

        return props

    def _parse_behaviors(self, expr: SExpr) -> list[GrueBehavior]:
        """Parse behaviors list."""
        if not isinstance(expr, SList):
            raise GrueParseError(f"Expected behaviors list, got {expr}")

        behaviors = []
        for item in expr:
            if not isinstance(item, SList) or len(item) < 2:
                raise GrueParseError(f"Expected behavior form, got {item}")

            verb = self._expect_symbol(item[0], "behavior verb")
            behavior = GrueBehavior(verb=verb)

            # Rest of items are case forms
            for case_expr in item.items[1:]:
                case = self._parse_case(case_expr)
                behavior.cases.append(case)

            behaviors.append(behavior)

        return behaviors

    def _parse_case(self, expr: SExpr) -> GrueCase:
        """Parse (case CONDITION :outcome ... :effects ... :reason ... :context ...)."""
        if not isinstance(expr, SList) or len(expr) < 2:
            raise GrueParseError(f"Expected case form, got {expr}")

        if not isinstance(expr[0], Symbol) or expr[0].name != "case":
            raise GrueParseError(f"Expected 'case', got {expr[0]}")

        condition = expr[1]
        kwargs = self._parse_kwargs(list(expr.items[2:]))

        outcome = "success"  # default
        if "outcome" in kwargs:
            outcome = self._expect_symbol(kwargs["outcome"], "case outcome")

        effects: list[SExpr] = []
        if "effects" in kwargs:
            effects_expr = kwargs["effects"]
            if isinstance(effects_expr, SList):
                effects = list(effects_expr.items)

        reason = None
        if "reason" in kwargs:
            reason = self._expect_symbol(kwargs["reason"], "case reason")

        context: list[tuple[str, Any]] = []
        if "context" in kwargs:
            context = self._parse_context(kwargs["context"])

        action = kwargs.get("action")

        return GrueCase(
            when=condition,
            outcome=outcome,
            effects=effects,
            reason=reason,
            context=context,
            action=action,
        )

    def _parse_context(self, expr: SExpr) -> list[tuple[str, Any]]:
        """Parse context like ((mechanism push-bar) (note auto-closing))."""
        if not isinstance(expr, SList):
            raise GrueParseError(f"Expected context list, got {expr}")

        context = []
        for item in expr:
            if not isinstance(item, SList) or len(item) < 2:
                raise GrueParseError(f"Expected (key value) context, got {item}")

            key = self._expect_symbol(item[0], "context key")
            # Keep the raw value - might be symbol, list, etc.
            value = self._sexpr_to_value(item[1]) if len(item) == 2 else [self._sexpr_to_value(v) for v in item.items[1:]]
            context.append((key, value))

        return context

    def _parse_victory(self, expr: SList) -> GrueVictory:
        """Parse (victory :when EXPR :context (...))."""
        kwargs = self._parse_kwargs(list(expr.items[1:]))

        if "when" not in kwargs:
            raise GrueParseError("victory requires :when condition")

        context: list[tuple[str, Any]] = []
        if "context" in kwargs:
            context = self._parse_context(kwargs["context"])

        return GrueVictory(when=kwargs["when"], context=context)

    def _parse_defeat(self, expr: SList) -> GrueDefeat:
        """Parse (defeat NAME :when EXPR :context (...))."""
        if len(expr) < 2:
            raise GrueParseError("defeat requires a name")

        name = self._expect_symbol(expr[1], "defeat name")
        kwargs = self._parse_kwargs(list(expr.items[2:]))

        if "when" not in kwargs:
            raise GrueParseError("defeat requires :when condition")

        context: list[tuple[str, Any]] = []
        if "context" in kwargs:
            context = self._parse_context(kwargs["context"])

        return GrueDefeat(name=name, when=kwargs["when"], context=context)

    # Helper methods

    def _expect_symbol(self, expr: SExpr, what: str) -> str:
        """Expect a symbol and return its name."""
        if isinstance(expr, Symbol):
            return expr.name
        raise GrueParseError(f"Expected {what} (symbol), got {expr}")

    def _expect_string(self, expr: SExpr, what: str) -> str:
        """Expect a string literal."""
        if isinstance(expr, str):
            return expr
        raise GrueParseError(f"Expected {what} (string), got {expr}")

    def _sexpr_to_value(self, expr: SExpr) -> Any:
        """Convert an S-expression to a Python value."""
        if isinstance(expr, Symbol):
            return expr.name
        elif isinstance(expr, (str, int, bool)):
            return expr
        elif isinstance(expr, SList):
            return [self._sexpr_to_value(item) for item in expr]
        elif isinstance(expr, Keyword):
            return f":{expr.name}"
        else:
            return expr


def load_grue(path: str | Path) -> GrueWorld:
    """Load a GRUE world definition from a file or directory.
    
    If path is a file, parse it as a single GRUE source.
    If path is a directory, load and combine all .grue files (excluding reference/).
    """
    path = Path(path)
    
    if path.is_file():
        parser = GrueParser()
        return parser.parse_file(path)
    
    if path.is_dir():
        # Load main files in order, skip reference/ directory
        main_files = ["world.grue", "rooms.grue", "objects.grue", "barriers.grue"]
        combined_source = []
        
        for filename in main_files:
            file_path = path / filename
            if file_path.exists():
                combined_source.append(file_path.read_text())
        
        # Also load any other .grue files in the root (for custom additions)
        for file_path in sorted(path.glob("*.grue")):
            if file_path.name not in main_files:
                combined_source.append(file_path.read_text())
        
        return parse_grue("\n".join(combined_source))
    
    raise FileNotFoundError(f"Path not found: {path}")


def parse_grue(source: str) -> GrueWorld:
    """Parse GRUE source text into a GrueWorld."""
    parser = GrueParser()
    return parser.parse(source)
