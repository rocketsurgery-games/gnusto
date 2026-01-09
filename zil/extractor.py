"""
ZIL Extractor

Extracts game data from parsed ZIL AST into structured Python objects.
Handles ROOM, OBJECT, ROUTINE, SYNTAX, and other game definitions.
"""

from dataclasses import dataclass, field
from typing import Any

from .ast import ASTNode, Atom, Form, List, Number, String


@dataclass
class Property:
    """A property on a room or object."""

    name: str
    values: list[Any] = field(default_factory=list)


@dataclass
class ZILObject:
    """
    An OBJECT or ROOM definition from ZIL.

    Objects have properties defined as lists:
        (IN LOCATION)
        (DESC "description")
        (FLAGS FLAG1 FLAG2)
        (NORTH TO ROOM-NAME)
    """

    name: str
    kind: str  # "OBJECT" or "ROOM"
    properties: dict[str, Property] = field(default_factory=dict)
    line: int = 0

    def get_property(self, name: str) -> Property | None:
        """Get a property by name."""
        return self.properties.get(name)

    def get_property_value(self, name: str, default: Any = None) -> Any:
        """Get the first value of a property."""
        prop = self.properties.get(name)
        if prop and prop.values:
            return prop.values[0]
        return default

    def get_property_values(self, name: str) -> list[Any]:
        """Get all values of a property."""
        prop = self.properties.get(name)
        return prop.values if prop else []


@dataclass
class Routine:
    """
    A ROUTINE definition from ZIL.

    Routines are functions with optional arguments and a body.
    """

    name: str
    args: list[str] = field(default_factory=list)
    optional_args: list[str] = field(default_factory=list)
    aux_vars: list[str] = field(default_factory=list)
    body: list[ASTNode] = field(default_factory=list)
    line: int = 0


@dataclass
class Syntax:
    """
    A SYNTAX definition (verb pattern).

    Example:
        <SYNTAX TAKE OBJECT (HELD MANY HAVE) = V-TAKE PRE-TAKE>
    """

    verb: str = ""
    pattern: list[str] = field(default_factory=list)  # words/objects in pattern
    filters: list[str] = field(default_factory=list)  # HELD, FIND, etc.
    action: str = ""
    pre_action: str = ""
    line: int = 0


@dataclass
class Constant:
    """A CONSTANT definition."""

    name: str
    value: Any
    line: int = 0


@dataclass
class Global:
    """A GLOBAL variable definition."""

    name: str
    value: Any
    line: int = 0


@dataclass
class GameData:
    """All extracted game data from ZIL source."""

    objects: dict[str, ZILObject] = field(default_factory=dict)
    rooms: dict[str, ZILObject] = field(default_factory=dict)
    routines: dict[str, Routine] = field(default_factory=dict)
    syntax: list[Syntax] = field(default_factory=list)
    constants: dict[str, Constant] = field(default_factory=dict)
    globals: dict[str, Global] = field(default_factory=dict)
    synonyms: dict[str, list[str]] = field(default_factory=dict)
    directions: list[str] = field(default_factory=list)


def extract_value(node: ASTNode) -> Any:
    """Extract a Python value from an AST node."""
    if isinstance(node, Atom):
        return node.name
    if isinstance(node, Number):
        return node.value
    if isinstance(node, String):
        return node.value
    if isinstance(node, List):
        return [extract_value(e) for e in node.elements]
    if isinstance(node, Form):
        # Return form as a dict-like structure for complex values
        if node.operator:
            return {
                "_form": node.operator.name,
                "_args": [extract_value(a) for a in node.args],
            }
        return [extract_value(e) for e in node.elements]
    return None


def extract_property(lst: List) -> Property | None:
    """Extract a property from a list like (IN ROOMS) or (DESC "text")."""
    if not lst.elements:
        return None

    first = lst.elements[0]
    if not isinstance(first, Atom):
        return None

    name = first.name
    values = [extract_value(e) for e in lst.elements[1:]]
    return Property(name=name, values=values)


def extract_object(form: Form) -> ZILObject | None:
    """
    Extract an OBJECT or ROOM from a form.

    Format: <OBJECT NAME (PROP1 val) (PROP2 val) ...>
    """
    if not form.operator or form.operator.name not in ("OBJECT", "ROOM"):
        return None

    kind = form.operator.name
    args = form.args

    if not args or not isinstance(args[0], Atom):
        return None

    name = args[0].name
    obj = ZILObject(name=name, kind=kind, line=form.line)

    # Extract properties from remaining args
    for arg in args[1:]:
        if isinstance(arg, List):
            prop = extract_property(arg)
            if prop:
                obj.properties[prop.name] = prop

    return obj


def extract_routine(form: Form) -> Routine | None:
    """
    Extract a ROUTINE definition.

    Format: <ROUTINE NAME (args "AUX" aux-vars "OPT" opt-vars) body...>
    or: <ROUTINE NAME ("AUX" aux-vars) body...>
    """
    if not form.operator or form.operator.name not in ("ROUTINE", "DEFINE"):
        return None

    args = form.args
    if not args or not isinstance(args[0], Atom):
        return None

    name = args[0].name
    routine = Routine(name=name, line=form.line)

    # Parse argument list if present
    if len(args) > 1 and isinstance(args[1], List):
        arg_list = args[1].elements
        mode = "args"  # args, aux, or opt

        for elem in arg_list:
            if isinstance(elem, String):
                mode_str = elem.value.upper()
                if mode_str == "AUX":
                    mode = "aux"
                elif mode_str == "OPT" or mode_str == "OPTIONAL":
                    mode = "opt"
            elif isinstance(elem, Atom):
                if mode == "args":
                    routine.args.append(elem.name)
                elif mode == "aux":
                    routine.aux_vars.append(elem.name)
                elif mode == "opt":
                    routine.optional_args.append(elem.name)
            elif isinstance(elem, List):
                # Argument with default value: (VAR DEFAULT)
                if elem.elements and isinstance(elem.elements[0], Atom):
                    var_name = elem.elements[0].name
                    if mode == "args":
                        routine.args.append(var_name)
                    elif mode == "aux":
                        routine.aux_vars.append(var_name)
                    elif mode == "opt":
                        routine.optional_args.append(var_name)

        # Body is everything after the arg list
        routine.body = args[2:]
    else:
        # No arg list, body starts at index 1
        routine.body = args[1:]

    return routine


def extract_syntax(form: Form) -> Syntax | None:
    """
    Extract a SYNTAX definition.

    Format: <SYNTAX VERB [PREP] OBJECT [(filters)] [= ACTION [PRE-ACTION]]>
    """
    if not form.operator or form.operator.name != "SYNTAX":
        return None

    args = form.args
    if not args:
        return None

    syntax = Syntax(line=form.line)

    # First element is the verb
    if isinstance(args[0], Atom):
        syntax.verb = args[0].name

    # Parse remaining elements
    i = 1
    while i < len(args):
        elem = args[i]

        if isinstance(elem, Atom):
            if elem.name == "=":
                # Everything after = is action and pre-action
                i += 1
                if i < len(args) and isinstance(args[i], Atom):
                    syntax.action = args[i].name
                    i += 1
                if i < len(args) and isinstance(args[i], Atom):
                    syntax.pre_action = args[i].name
                break
            else:
                syntax.pattern.append(elem.name)

        elif isinstance(elem, List):
            # Filter list like (HELD MANY HAVE) or (FIND CONTBIT)
            for filter_elem in elem.elements:
                if isinstance(filter_elem, Atom):
                    syntax.filters.append(filter_elem.name)

        i += 1

    return syntax


def extract_constant(form: Form) -> Constant | None:
    """Extract a CONSTANT definition."""
    if not form.operator or form.operator.name != "CONSTANT":
        return None

    args = form.args
    if len(args) < 2 or not isinstance(args[0], Atom):
        return None

    name = args[0].name
    value = extract_value(args[1])
    return Constant(name=name, value=value, line=form.line)


def extract_global(form: Form) -> Global | None:
    """Extract a GLOBAL definition."""
    if not form.operator or form.operator.name != "GLOBAL":
        return None

    args = form.args
    if not args or not isinstance(args[0], Atom):
        return None

    name = args[0].name
    value = extract_value(args[1]) if len(args) > 1 else None
    return Global(name=name, value=value, line=form.line)


def extract_synonym(form: Form) -> tuple[str, list[str]] | None:
    """
    Extract a SYNONYM or VERB-SYNONYM definition.

    Format: <SYNONYM WORD ALIAS1 ALIAS2 ...>
    """
    if not form.operator or form.operator.name not in (
        "SYNONYM",
        "VERB-SYNONYM",
        "PREP-SYNONYM",
    ):
        return None

    args = form.args
    if len(args) < 2:
        return None

    words = []
    for arg in args:
        if isinstance(arg, Atom):
            words.append(arg.name)

    if len(words) >= 2:
        return words[0], words[1:]
    return None


def extract_directions(form: Form) -> list[str] | None:
    """Extract DIRECTIONS definition."""
    if not form.operator or form.operator.name != "DIRECTIONS":
        return None

    directions = []
    for arg in form.args:
        if isinstance(arg, Atom):
            directions.append(arg.name)
    return directions


def extract_game_data(ast: list[ASTNode]) -> GameData:
    """
    Extract all game data from a parsed ZIL AST.

    Args:
        ast: List of top-level AST nodes

    Returns:
        GameData containing all extracted definitions
    """
    data = GameData()

    for node in ast:
        if not isinstance(node, Form) or not node.operator:
            continue

        op = node.operator.name

        if op in ("OBJECT", "ROOM"):
            obj = extract_object(node)
            if obj:
                if obj.kind == "ROOM":
                    data.rooms[obj.name] = obj
                else:
                    data.objects[obj.name] = obj

        elif op in ("ROUTINE", "DEFINE"):
            routine = extract_routine(node)
            if routine:
                data.routines[routine.name] = routine

        elif op == "SYNTAX":
            syntax = extract_syntax(node)
            if syntax:
                data.syntax.append(syntax)

        elif op == "CONSTANT":
            const = extract_constant(node)
            if const:
                data.constants[const.name] = const

        elif op == "GLOBAL":
            glob = extract_global(node)
            if glob:
                data.globals[glob.name] = glob

        elif op in ("SYNONYM", "VERB-SYNONYM", "PREP-SYNONYM"):
            syn = extract_synonym(node)
            if syn:
                word, aliases = syn
                if word not in data.synonyms:
                    data.synonyms[word] = []
                data.synonyms[word].extend(aliases)

        elif op == "DIRECTIONS":
            dirs = extract_directions(node)
            if dirs:
                data.directions = dirs

    return data
