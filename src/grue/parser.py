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
    outcome: str  # "success", "blocked", "default"
    effects: list[SExpr] = field(default_factory=list)
    reason: str | None = None
    context: list[tuple[str, Any]] = field(default_factory=list)
    action: SExpr | None = None  # For default with explicit action


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
    defaults: dict[str, GrueBehavior] = field(default_factory=dict)  # verb -> default behavior


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
        elif name == "default":
            behavior = self._parse_default(expr)
            world.defaults[behavior.verb] = behavior
        elif name in ("test", "test-sequence", "defn"):
            # Skip test-related forms (handled by test_dsl module)
            pass
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
        """Parse properties.

        Supports two formats:
        - New (Clojure-style): (:capacity 20 :strength 10)
        - Legacy: ((capacity 20) (strength 10))
        """
        if not isinstance(expr, SList):
            raise GrueParseError(f"Expected properties list, got {expr}")

        props = {}
        items = list(expr.items)

        # Detect format: if first item is a Keyword, use new format
        if items and isinstance(items[0], Keyword):
            # New format: keyword-value pairs
            i = 0
            while i < len(items):
                if isinstance(items[i], Keyword):
                    key = items[i].name
                    if i + 1 >= len(items):
                        raise GrueParseError(f"Missing value for property :{key}")
                    value = self._sexpr_to_value(items[i + 1])
                    props[key] = value
                    i += 2
                else:
                    i += 1
        else:
            # Legacy format: (key value) pairs
            for item in expr:
                if not isinstance(item, SList) or len(item) < 2:
                    raise GrueParseError(f"Expected (key value) property, got {item}")

                key = self._expect_symbol(item[0], "property key")
                value = self._sexpr_to_value(item[1])
                props[key] = value

        return props

    def _parse_default(self, expr: SExpr) -> GrueBehavior:
        """Parse (default VERB (cond ...)).

        Defines a default behavior for a verb that applies when an object
        doesn't define its own behavior for that verb.

        Example:
            (default take (cond
              ((not (has-flag self TAKEBIT)) (blocked :reason not-takeable))
              (true (success :effects ((move! self ?actor))))))
        """
        if not isinstance(expr, SList) or len(expr) < 3:
            raise GrueParseError(f"Expected (default VERB (cond ...)), got {expr}")

        verb = self._expect_symbol(expr[1], "default verb")
        behavior = GrueBehavior(verb=verb)

        cond_expr = expr[2]
        if not isinstance(cond_expr, SList) or len(cond_expr) < 1:
            raise GrueParseError(f"Expected (cond ...) in default, got {cond_expr}")

        first = cond_expr[0]
        if not isinstance(first, Symbol) or first.name != "cond":
            raise GrueParseError(f"Expected 'cond' in default, got {first}")

        behavior.cases = self._parse_cond(cond_expr)

        if not behavior.cases:
            raise GrueParseError(f"Default behavior for '{verb}' has no cases")

        return behavior

    def _parse_behaviors(self, expr: SExpr) -> list[GrueBehavior]:
        """Parse behaviors list: (:verb (cond ...) :verb2 (cond ...) ...)

        Example:
            :behaviors (
              :open (cond
                ((has-flag self LOCKED) (blocked :reason locked))
                (true (success :effects ((set-flag! self OPENBIT)))))
              :close (cond
                (true (success))))
        """
        if not isinstance(expr, SList):
            raise GrueParseError(f"Expected behaviors list, got {expr}")

        behaviors = []
        items = list(expr.items)
        i = 0

        while i < len(items):
            item = items[i]

            if isinstance(item, Keyword):
                verb = item.name
                i += 1

                if i >= len(items):
                    raise GrueParseError(f"Missing (cond ...) after :{verb}")

                cond_expr = items[i]
                if not isinstance(cond_expr, SList) or len(cond_expr) < 1:
                    raise GrueParseError(f"Expected (cond ...) after :{verb}, got {cond_expr}")

                first = cond_expr[0]
                if not isinstance(first, Symbol) or first.name != "cond":
                    raise GrueParseError(f"Expected 'cond' after :{verb}, got {first}")

                behavior = GrueBehavior(verb=verb)
                behavior.cases = self._parse_cond(cond_expr)
                behaviors.append(behavior)
                i += 1
            else:
                i += 1  # Skip unknown items (e.g., comments)

        return behaviors

    def _parse_cond(self, expr: SExpr) -> list[GrueCase]:
        """Parse (cond (CONDITION (outcome ...)) (CONDITION (outcome ...)) ...).

        New syntax using standard Lisp cond form. Each clause is:
            (CONDITION (success :effects ... :message ...))
            (CONDITION (blocked :reason ... :message ...))
            (CONDITION (default :action ...))
        """
        if not isinstance(expr, SList) or len(expr) < 2:
            raise GrueParseError(f"Expected (cond ...), got {expr}")

        if not isinstance(expr[0], Symbol) or expr[0].name != "cond":
            raise GrueParseError(f"Expected 'cond', got {expr[0]}")

        cases = []
        for clause in expr.items[1:]:
            case = self._parse_cond_clause(clause)
            cases.append(case)

        return cases

    def _parse_cond_clause(self, expr: SExpr) -> GrueCase:
        """Parse a cond clause: (CONDITION (outcome :key val ...)).

        Examples:
            ((not (has-flag self TAKEBIT)) (blocked :reason not-takeable))
            (true (success :effects ((move! self ?actor))))
        """
        if not isinstance(expr, SList) or len(expr) < 2:
            raise GrueParseError(f"Expected (CONDITION (outcome ...)), got {expr}")

        condition = expr[0]
        outcome_form = expr[1]

        if not isinstance(outcome_form, SList) or len(outcome_form) < 1:
            raise GrueParseError(f"Expected outcome form like (success ...), got {outcome_form}")

        outcome_type = outcome_form[0]
        if not isinstance(outcome_type, Symbol):
            raise GrueParseError(f"Expected outcome type (success/blocked/default), got {outcome_type}")

        outcome = outcome_type.name
        if outcome not in ("success", "blocked", "default"):
            raise GrueParseError(f"Unknown outcome type: {outcome}")

        # Parse the outcome form's keyword arguments
        kwargs = self._parse_kwargs(list(outcome_form.items[1:]))

        effects: list[SExpr] = []
        if "effects" in kwargs:
            effects_expr = kwargs["effects"]
            if isinstance(effects_expr, SList):
                effects = list(effects_expr.items)

        reason = None
        if "reason" in kwargs:
            reason = self._expect_symbol(kwargs["reason"], "clause reason")

        # Build context from various keyword args
        context: list[tuple[str, Any]] = []
        if "context" in kwargs:
            context = self._parse_context(kwargs["context"])
        # Also support :message as shorthand for context
        if "message" in kwargs:
            msg = kwargs["message"]
            if isinstance(msg, str):
                context.append(("message", msg))
            else:
                context.append(("message", str(msg)))

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


def _load_defaults() -> GrueWorld:
    """Load the built-in builtins.grue file."""
    defaults_path = Path(__file__).parent / "builtins.grue"
    if defaults_path.exists():
        parser = GrueParser()
        return parser.parse_file(defaults_path)
    return GrueWorld()


def _merge_defaults(world: GrueWorld, defaults: GrueWorld) -> None:
    """Merge default behaviors into a world (in place).

    Only adds defaults for verbs not already defined in world.defaults.
    """
    for verb, behavior in defaults.defaults.items():
        if verb not in world.defaults:
            world.defaults[verb] = behavior


def load_grue(path: str | Path, include_defaults: bool = True) -> GrueWorld:
    """Load a GRUE world definition from a file or directory.

    If path is a file, parse it as a single GRUE source.
    If path is a directory, load and combine all .grue files (excluding reference/).

    Args:
        path: File or directory to load
        include_defaults: If True, merge built-in builtins.grue (default: True)
    """
    path = Path(path)

    if path.is_file():
        parser = GrueParser()
        world = parser.parse_file(path)
    elif path.is_dir():
        # Load main files in order, skip reference/ directory
        main_files = ["world.grue", "rooms.grue", "objects.grue", "barriers.grue"]
        combined_source = []

        for filename in main_files:
            file_path = path / filename
            if file_path.exists():
                combined_source.append(file_path.read_text())

        # Also load any other .grue files in the root (for custom additions)
        # Skip test files (*.test.grue)
        for file_path in sorted(path.glob("*.grue")):
            if file_path.name not in main_files and not file_path.name.endswith(".test.grue"):
                combined_source.append(file_path.read_text())

        world = parse_grue("\n".join(combined_source))
    else:
        raise FileNotFoundError(f"Path not found: {path}")

    if include_defaults:
        _merge_defaults(world, _load_defaults())

    return world


def parse_grue(source: str) -> GrueWorld:
    """Parse GRUE source text into a GrueWorld."""
    parser = GrueParser()
    return parser.parse(source)
