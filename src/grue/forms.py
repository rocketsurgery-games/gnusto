"""
GRUE Form Handlers - Interpret top-level S-expression forms into GrueWorld.

Each form handler is a function that processes a specific top-level form
(world, room, object, etc.) and updates the GrueWorld datastructure.

Form handlers are registered via the @form decorator and dispatched by
FormDispatcher.dispatch().
"""

from typing import Any, Callable, Protocol
from dataclasses import dataclass, field

from .sexpr import SExpr, Symbol, Keyword, SList


class FormParseError(Exception):
    """Error during form interpretation."""
    pass


# Type aliases for form handlers
class FormHandler(Protocol):
    """Protocol for form handler functions."""
    def __call__(self, expr: SList, world: "GrueWorld") -> None: ...


# Form handler registry
_form_handlers: dict[str, FormHandler] = {}


def form(name: str) -> Callable[[FormHandler], FormHandler]:
    """Decorator to register a form handler.

    Usage:
        @form("room")
        def parse_room(expr: SList, world: GrueWorld) -> None:
            ...
    """
    def decorator(fn: FormHandler) -> FormHandler:
        _form_handlers[name.lower()] = fn
        return fn
    return decorator


def get_form_handler(name: str) -> FormHandler | None:
    """Get a registered form handler by name."""
    return _form_handlers.get(name.lower())


def list_form_handlers() -> list[str]:
    """List all registered form handler names."""
    return sorted(_form_handlers.keys())


# === Dataclasses (moved from parser.py for shared access) ===

@dataclass
class GrueExit:
    """An exit from a room."""
    direction: str
    to: str
    via: str | None = None  # Door/boundary object
    when: SExpr | None = None  # Optional condition


@dataclass
class GrueBehavior:
    """A behavior definition for a specific verb.

    Behaviors are functions with explicit parameters:
        :give (fn (?item) (if (held? ?item) (success) (blocked :reason not-held)))
        :take (fn () (success))

    The body can be any expression - not limited to (cond ...).
    Common patterns:
        - (cond ...) for multiple branches
        - (if ...) for simple conditionals
        - (success) / (blocked ...) for direct results

    Auto-bound symbols (not in params):
        ?self  - The object whose behavior is invoked
        ?actor - Who is performing the action (usually @player)
    """
    verb: str
    params: list[str] = field(default_factory=list)  # Parameter names (without ?)
    body: SExpr | None = None  # The function body expression


@dataclass
class GrueRoom:
    """A room definition.

    Rooms can have behaviors just like objects. The most common is :before-action,
    which runs before any action in the room and can block or redirect it.

    Nested forms (def, defn) can be placed inside the room to define scoped
    bindings that are only visible within this room's behaviors.
    """
    name: str
    description: str = ""
    ldesc: str = ""  # Long description
    flags: list[str] = field(default_factory=list)
    exits: list[GrueExit] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    behaviors: list["GrueBehavior"] = field(default_factory=list)
    nested_forms: list[SExpr] = field(default_factory=list)  # (def ...), (defn ...) etc.


@dataclass
class GrueObject:
    """An object definition.

    Nested forms (def, defn) can be placed inside the object to define scoped
    bindings that are only visible within this object's behaviors.

    Example:
        (object @door
          (def closed-desc "The door is closed.")
          (defn check-locked () (has-flag? ?self LOCKED))

          :description closed-desc
          :behaviors (
            :open (fn () (if (check-locked) (blocked) (success)))))
    """
    name: str
    description: str = ""
    fdesc: str = ""  # First description (before object is moved)
    ldesc: str = ""  # Long description
    location: str | None = None
    flags: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    behaviors: list[GrueBehavior] = field(default_factory=list)
    nested_forms: list[SExpr] = field(default_factory=list)  # (def ...), (defn ...) etc.


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
class GrueEvent:
    """Turn-based event handler (like ZIL interrupts).

    Events run once per turn when queued. The body is evaluated like
    a behavior - typically a (cond ...) that returns success/blocked.

    Example:
        (event hacker-helps
          :location @terminal-room   ; Only fires when player is here
          :on-turn (cond
            ((= hacker-help 1) (success :effects (...) :context (...)))
            ((= hacker-help 2) ...)
            (true (success :effects ((dequeue! hacker-helps)) ...))))
    """
    name: str
    location: str | None  # If set, event only fires when player is here
    body: SExpr | None = None  # The :on-turn handler expression
    nested_forms: list[SExpr] = field(default_factory=list)  # (def ...), (defn ...) etc.


@dataclass
class GrueFunction:
    """A named function defined with (defn name (params) body)."""
    name: str
    params: list[str]
    body: SExpr


@dataclass
class GrueWorld:
    """
    Complete GRUE world definition.
    """
    name: str = ""
    description: str = ""
    player: str = ""  # Entity name of the player (e.g., "@player")
    rooms: dict[str, GrueRoom] = field(default_factory=dict)
    objects: dict[str, GrueObject] = field(default_factory=dict)
    victory: GrueVictory | None = None
    defeat: dict[str, GrueDefeat] = field(default_factory=dict)
    defaults: dict[str, GrueBehavior] = field(default_factory=dict)  # verb -> default behavior
    globals: dict[str, Any] = field(default_factory=dict)  # global variables
    constants: dict[str, Any] = field(default_factory=dict)  # immutable constants from (def name value)
    events: dict[str, GrueEvent] = field(default_factory=dict)  # name -> turn-based event handler
    functions: dict[str, GrueFunction] = field(default_factory=dict)  # name -> function definition


# === Helper functions for form handlers ===

def parse_entity_body(items: list[SExpr], entity_type: str) -> tuple[list[SExpr], dict[str, SExpr]]:
    """Parse entity body into nested forms and keyword arguments.

    Handles interleaved nested forms (def, defn) and keyword arguments.
    Raises errors for unexpected items or misplaced forms.

    Args:
        items: List of items after entity name
        entity_type: Name of entity type for error messages (e.g., "object", "room")

    Returns:
        (nested_forms, kwargs)
    """
    nested_forms: list[SExpr] = []
    kwargs: dict[str, SExpr] = {}

    # Known nested form types
    nested_form_types = {"def", "defn"}

    i = 0
    while i < len(items):
        item = items[i]

        if isinstance(item, Keyword):
            # Keyword argument - consume key and value
            key = item.name
            if i + 1 >= len(items):
                raise FormParseError(f"Missing value for keyword :{key} in {entity_type}")
            kwargs[key] = items[i + 1]
            i += 2

        elif isinstance(item, SList) and len(item) > 0 and isinstance(item[0], Symbol):
            form_name = item[0].name
            if form_name in nested_form_types:
                # It's a nested form like (def ...) or (defn ...)
                nested_forms.append(item)
                i += 1
            else:
                raise FormParseError(
                    f"Unexpected form ({form_name} ...) in {entity_type} body. "
                    f"Only {nested_form_types} forms are allowed. "
                    f"Did you mean to use a keyword like :{form_name}?"
                )
        else:
            raise FormParseError(
                f"Unexpected item in {entity_type} body: {item}. "
                f"Expected keyword argument (like :description) or nested form (like (def ...))."
            )

    return nested_forms, kwargs


def separate_nested_forms(items: list[SExpr]) -> tuple[list[SExpr], list[SExpr]]:
    """Separate nested forms from keyword arguments.

    DEPRECATED: Use parse_entity_body() instead for better error handling.

    Items before the first keyword are treated as nested forms (e.g., (def ...), (defn ...)).
    Items starting from the first keyword are kwargs.

    Returns:
        (nested_forms, remaining_items)
    """
    nested_forms = []
    for i, item in enumerate(items):
        if isinstance(item, Keyword):
            # Found first keyword - rest are kwargs
            return nested_forms, items[i:]
        elif isinstance(item, SList) and len(item) > 0 and isinstance(item[0], Symbol):
            # It's a nested form like (def ...) or (defn ...)
            nested_forms.append(item)
        else:
            # Something else - stop collecting nested forms
            return nested_forms, items[i:]
    # All items were nested forms
    return nested_forms, []


def parse_kwargs(items: list[SExpr]) -> dict[str, SExpr]:
    """Parse Clojure-style keyword arguments from a list."""
    kwargs: dict[str, SExpr] = {}
    i = 0
    while i < len(items):
        if isinstance(items[i], Keyword):
            key = items[i].name
            if i + 1 >= len(items):
                raise FormParseError(f"Missing value for keyword :{key}")
            kwargs[key] = items[i + 1]
            i += 2
        else:
            # Positional argument encountered - stop parsing kwargs
            break
    return kwargs


def expect_symbol(expr: SExpr, what: str) -> str:
    """Expect a symbol and return its name."""
    if isinstance(expr, Symbol):
        return expr.name
    raise FormParseError(f"Expected {what} (symbol), got {expr}")


def expect_string(expr: SExpr, what: str) -> str:
    """Expect a string literal."""
    if isinstance(expr, str):
        return expr
    raise FormParseError(f"Expected {what} (string), got {expr}")


def sexpr_to_value(expr: SExpr) -> Any:
    """Convert an S-expression to a Python value."""
    if isinstance(expr, Symbol):
        return expr.name
    elif isinstance(expr, (str, int, bool)):
        return expr
    elif isinstance(expr, SList):
        return [sexpr_to_value(item) for item in expr]
    elif isinstance(expr, Keyword):
        return f":{expr.name}"
    else:
        return expr


def parse_flags(expr: SExpr) -> list[str]:
    """Parse a flags list like (DOOR LOCKED OPENABLE)."""
    if not isinstance(expr, SList):
        raise FormParseError(f"Expected flags list, got {expr}")

    flags = []
    for item in expr:
        if isinstance(item, Symbol):
            flags.append(item.name)
        else:
            raise FormParseError(f"Expected flag symbol, got {item}")
    return flags


def parse_properties(expr: SExpr) -> dict[str, Any]:
    """Parse properties.

    Supports two formats:
    - New (Clojure-style): (:capacity 20 :strength 10)
    - Legacy: ((capacity 20) (strength 10))
    """
    if not isinstance(expr, SList):
        raise FormParseError(f"Expected properties list, got {expr}")

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
                    raise FormParseError(f"Missing value for property :{key}")
                value = sexpr_to_value(items[i + 1])
                props[key] = value
                i += 2
            else:
                i += 1
    else:
        # Legacy format: (key value) pairs
        for item in expr:
            if not isinstance(item, SList) or len(item) < 2:
                raise FormParseError(f"Expected (key value) property, got {item}")

            key = expect_symbol(item[0], "property key")
            value = sexpr_to_value(item[1])
            props[key] = value

    return props


def parse_context(expr: SExpr) -> list[tuple[str, Any]]:
    """Parse context like ((mechanism push-bar) (note auto-closing))."""
    if not isinstance(expr, SList):
        raise FormParseError(f"Expected context list, got {expr}")

    context = []
    for item in expr:
        if not isinstance(item, SList) or len(item) < 2:
            raise FormParseError(f"Expected (key value) context, got {item}")

        key = expect_symbol(item[0], "context key")
        # Keep the raw value - might be symbol, list, etc.
        value = sexpr_to_value(item[1]) if len(item) == 2 else [sexpr_to_value(v) for v in item.items[1:]]
        context.append((key, value))

    return context


def parse_exits(expr: SExpr) -> list[GrueExit]:
    """Parse exits like ((in :to LOBBY :via DOOR) (north :to HALLWAY))."""
    if not isinstance(expr, SList):
        raise FormParseError(f"Expected exits list, got {expr}")

    exits = []
    for item in expr:
        if not isinstance(item, SList) or len(item) < 1:
            raise FormParseError(f"Expected exit form, got {item}")

        direction = expect_symbol(item[0], "exit direction")
        kwargs = parse_kwargs(list(item.items[1:]))

        if "to" not in kwargs:
            raise FormParseError(f"Exit {direction} missing :to destination")

        exit = GrueExit(
            direction=direction,
            to=expect_symbol(kwargs["to"], "exit destination"),
            via=expect_symbol(kwargs["via"], "exit via") if "via" in kwargs else None,
            when=kwargs.get("when"),
        )
        exits.append(exit)

    return exits


def parse_behaviors(expr: SExpr) -> list[GrueBehavior]:
    """Parse behaviors list: (:verb (fn (?params) body) ...) or (:verb fn-reference ...)

    The body can be any expression - not limited to (cond ...).
    Alternatively, a bare symbol can reference a function defined elsewhere.

    Example:
        :behaviors (
          :give (fn (?item)
            (if (held-by? ?item ?actor)
                (success)
                (blocked :reason not-held)))
          :take (fn () (success))
          :examine shared-examine)  ; reference to defn or entity-scoped function

    Auto-bound symbols (not specified in params):
        ?self  - The object whose behavior is invoked
        ?actor - Who is performing the action
    """
    if not isinstance(expr, SList):
        raise FormParseError(f"Expected behaviors list, got {expr}")

    behaviors = []
    items = list(expr.items)
    i = 0

    while i < len(items):
        item = items[i]

        if isinstance(item, Keyword):
            verb = item.name
            i += 1

            if i >= len(items):
                raise FormParseError(f"Missing function or (fn ...) after :{verb}")

            fn_expr = items[i]

            # Case 1: Bare symbol - reference to a function
            if isinstance(fn_expr, Symbol):
                # Store as a call to the referenced function with no args
                # The body is (fn-name) which will be resolved at runtime
                body_expr = SList([fn_expr])
                behavior = GrueBehavior(verb=verb, params=[], body=body_expr)
                behaviors.append(behavior)
                i += 1
                continue

            # Case 2: (fn ...) inline definition
            if not isinstance(fn_expr, SList) or len(fn_expr) < 1:
                raise FormParseError(f"Expected (fn ...) or symbol after :{verb}, got {fn_expr}")

            first = fn_expr[0]
            if not isinstance(first, Symbol) or first.name != "fn":
                raise FormParseError(f"Expected 'fn' or symbol after :{verb}, got {first}")

            # Parse (fn (?param1 ?param2) body)
            if len(fn_expr) < 3:
                raise FormParseError(f"Expected (fn (params) body) for :{verb}")

            params_expr = fn_expr[1]
            body_expr = fn_expr[2]

            # Parse parameter list
            params = []
            if isinstance(params_expr, SList):
                for p in params_expr.items:
                    if isinstance(p, Symbol) and p.name.startswith("?"):
                        params.append(p.name[1:])  # Strip leading ?
                    else:
                        raise FormParseError(f"Expected ?param in params list, got {p}")

            # Store the body expression directly
            behavior = GrueBehavior(verb=verb, params=params, body=body_expr)
            behaviors.append(behavior)
            i += 1
        else:
            i += 1  # Skip unknown items (e.g., comments)

    return behaviors


# === Form Handlers ===

@form("world")
def _parse_world(expr: SList, world: GrueWorld) -> None:
    """Parse (world :name "..." :description "..." :player @entity)."""
    kwargs = parse_kwargs(list(expr.items[1:]))

    if "name" in kwargs:
        world.name = expect_string(kwargs["name"], "world name")
    if "description" in kwargs:
        world.description = expect_string(kwargs["description"], "world description")
    if "player" in kwargs:
        world.player = expect_symbol(kwargs["player"], "world player")


@form("globals")
def _parse_globals(expr: SList, world: GrueWorld) -> None:
    """Parse (globals :name value :name2 value2 ...).

    Example:
        (globals
          :lair-cnt 0
          :hacker-help 0
          :hacker-trade false)
    """
    kwargs = parse_kwargs(list(expr.items[1:]))

    for key, val_expr in kwargs.items():
        # Convert keyword names: :lair-cnt -> lair-cnt
        world.globals[key] = sexpr_to_value(val_expr)


@form("room")
def _parse_room(expr: SList, world: GrueWorld) -> None:
    """Parse (room NAME :description "..." :flags (...) :exits (...)).

    Nested forms like (def ...) and (defn ...) can appear anywhere in the body
    (interleaved with keyword arguments) to define scoped bindings visible
    only within this room's behaviors.
    """
    if len(expr) < 2:
        raise FormParseError("room requires a name")

    name = expect_symbol(expr[1], "room name")
    room = GrueRoom(name=name)

    # Parse body - handles interleaved nested forms and kwargs
    nested_forms, kwargs = parse_entity_body(list(expr.items[2:]), f"room {name}")
    room.nested_forms = nested_forms

    if "description" in kwargs:
        room.description = expect_string(kwargs["description"], "room description")
    if "ldesc" in kwargs:
        room.ldesc = expect_string(kwargs["ldesc"], "room ldesc")
    if "flags" in kwargs:
        room.flags = parse_flags(kwargs["flags"])
    if "exits" in kwargs:
        room.exits = parse_exits(kwargs["exits"])
    if "properties" in kwargs:
        room.properties = parse_properties(kwargs["properties"])
    if "behaviors" in kwargs:
        room.behaviors = parse_behaviors(kwargs["behaviors"])

    world.rooms[room.name] = room


@form("object")
def _parse_object(expr: SList, world: GrueWorld) -> None:
    """Parse (object NAME :description "..." :location LOC :flags (...) :behaviors (...)).

    Nested forms like (def ...) and (defn ...) can appear anywhere in the body
    (interleaved with keyword arguments) to define scoped bindings visible
    only within this object's behaviors.
    """
    if len(expr) < 2:
        raise FormParseError("object requires a name")

    name = expect_symbol(expr[1], "object name")
    obj = GrueObject(name=name)

    # Parse body - handles interleaved nested forms and kwargs
    nested_forms, kwargs = parse_entity_body(list(expr.items[2:]), f"object {name}")
    obj.nested_forms = nested_forms

    if "description" in kwargs:
        obj.description = expect_string(kwargs["description"], "object description")
    if "fdesc" in kwargs:
        obj.fdesc = expect_string(kwargs["fdesc"], "object fdesc")
    if "ldesc" in kwargs:
        obj.ldesc = expect_string(kwargs["ldesc"], "object ldesc")
    if "location" in kwargs:
        obj.location = expect_symbol(kwargs["location"], "object location")
    if "flags" in kwargs:
        obj.flags = parse_flags(kwargs["flags"])
    if "properties" in kwargs:
        obj.properties = parse_properties(kwargs["properties"])
    if "behaviors" in kwargs:
        obj.behaviors = parse_behaviors(kwargs["behaviors"])

    world.objects[obj.name] = obj


@form("victory")
def _parse_victory(expr: SList, world: GrueWorld) -> None:
    """Parse (victory :when EXPR :context (...))."""
    kwargs = parse_kwargs(list(expr.items[1:]))

    if "when" not in kwargs:
        raise FormParseError("victory requires :when condition")

    context: list[tuple[str, Any]] = []
    if "context" in kwargs:
        context = parse_context(kwargs["context"])

    world.victory = GrueVictory(when=kwargs["when"], context=context)


@form("defeat")
def _parse_defeat(expr: SList, world: GrueWorld) -> None:
    """Parse (defeat NAME :when EXPR :context (...))."""
    if len(expr) < 2:
        raise FormParseError("defeat requires a name")

    name = expect_symbol(expr[1], "defeat name")
    kwargs = parse_kwargs(list(expr.items[2:]))

    if "when" not in kwargs:
        raise FormParseError("defeat requires :when condition")

    context: list[tuple[str, Any]] = []
    if "context" in kwargs:
        context = parse_context(kwargs["context"])

    defeat = GrueDefeat(name=name, when=kwargs["when"], context=context)
    world.defeat[defeat.name] = defeat


@form("event")
def _parse_event(expr: SList, world: GrueWorld) -> None:
    """Parse (event NAME :location ROOM :on-turn BODY).

    Turn-based event handlers that run once per turn when queued.
    The body is evaluated at runtime like a behavior.

    Example:
        (event hacker-helps
          :location @terminal-room   ; Only fires when player is here
          :on-turn (cond
            ((= hacker-help 1) (success :effects (...) :context (...)))
            ((= hacker-help 2) ...)
            (true (success :effects ((dequeue! hacker-helps)) ...))))

    With scoped definitions:
        (event compulsion
          (def page1-desc "...")
          :location @terminal-room
          :on-turn (condp = comp-cnt
            0 (success :context ((description page1-desc)))
            ...))
    """
    if len(expr) < 2:
        raise FormParseError("event requires a name")

    name = expect_symbol(expr[1], "event name")
    nested_forms, kwargs = parse_entity_body(list(expr.items[2:]), "event")

    if "on-turn" not in kwargs:
        raise FormParseError(f"event {name} requires :on-turn handler")

    # Parse optional location constraint
    location: str | None = None
    if "location" in kwargs:
        loc_expr = kwargs["location"]
        location = expect_symbol(loc_expr, "event location")

    # Store the body expression directly (evaluated at runtime)
    body = kwargs["on-turn"]

    event = GrueEvent(name=name, location=location, body=body, nested_forms=nested_forms)
    world.events[event.name] = event


@form("default")
def _parse_default(expr: SList, world: GrueWorld) -> None:
    """Parse (default VERB BODY).

    Defines a default behavior for a verb that applies when an object
    doesn't define its own behavior for that verb.

    Example:
        (default take (cond
          ((not (has-flag ?self TAKEBIT)) (blocked :reason not-takeable))
          (true (success :effects ((move! ?self ?actor))))))
    """
    if not isinstance(expr, SList) or len(expr) < 3:
        raise FormParseError(f"Expected (default VERB BODY), got {expr}")

    verb = expect_symbol(expr[1], "default verb")
    body = expr[2]

    behavior = GrueBehavior(verb=verb, body=body)
    world.defaults[behavior.verb] = behavior


# Skip-able forms (handled elsewhere or ignored)
@form("test")
def _skip_test(expr: SList, world: GrueWorld) -> None:
    """Skip test forms (handled by test_dsl module)."""
    pass


@form("test-sequence")
def _skip_test_sequence(expr: SList, world: GrueWorld) -> None:
    """Skip test-sequence forms (handled by test_dsl module)."""
    pass


@form("defn")
def _parse_defn(expr: SList, world: GrueWorld) -> None:
    """Parse (defn name (params) body...) or (defn name "docstring" (params) body...).

    Supports:
    - (defn name (params) body)                    - single body expression
    - (defn name (params) "docstring" body)        - Scheme-style docstring in body
    - (defn name "docstring" (params) body)        - Clojure-style docstring before params
    - (defn name (params) body1 body2 ...)         - multiple body expressions

    If there's a docstring as first body expression, it's stripped.
    Multiple body expressions are wrapped in (do ...).
    """
    if len(expr) < 4:
        raise FormParseError(f"'defn' expects at least 3 arguments, got {len(expr) - 1}")

    name_expr = expr[1]
    if not isinstance(name_expr, Symbol):
        raise FormParseError(f"'defn' name must be a symbol, got: {name_expr}")
    name = name_expr.name

    # Determine where params and body start
    # Check if expr[2] is a string (Clojure-style docstring before params)
    if isinstance(expr[2], str):
        # (defn name "docstring" (params) body...)
        params_expr = expr[3]
        body_exprs = list(expr.items[4:])
    else:
        # (defn name (params) body...)
        params_expr = expr[2]
        body_exprs = list(expr.items[3:])

    if not isinstance(params_expr, SList):
        raise FormParseError(f"'defn' params must be a list, got: {params_expr}")
    params: list[str] = []
    for p in params_expr.items:
        if not isinstance(p, Symbol):
            raise FormParseError(f"'defn' parameter must be a symbol, got: {p}")
        # Strip leading ? if present
        param_name = p.name[1:] if p.name.startswith("?") else p.name
        params.append(param_name)

    # Strip leading docstring from body if present (Scheme-style)
    if body_exprs and isinstance(body_exprs[0], str):
        body_exprs = body_exprs[1:]

    # Wrap multiple body expressions in (do ...)
    if len(body_exprs) == 0:
        raise FormParseError(f"'defn' requires at least one body expression")
    elif len(body_exprs) == 1:
        body = body_exprs[0]
    else:
        body = SList([Symbol("do")] + body_exprs)

    world.functions[name] = GrueFunction(name=name, params=params, body=body)


@form("def")
def _parse_def(expr: SList, world: GrueWorld) -> None:
    """Parse (def name value) and store in world.constants.

    Unlike globals, constants are immutable and evaluated at load time.
    The value is stored as an unevaluated S-expression to be evaluated
    when first accessed at runtime.
    """
    if len(expr) != 3:
        raise FormParseError(f"'def' expects 2 arguments (name, value), got {len(expr) - 1}")

    name_expr = expr[1]
    if not isinstance(name_expr, Symbol):
        raise FormParseError(f"'def' name must be a symbol, got: {name_expr}")
    name = name_expr.name

    value = expr[2]
    world.constants[name] = value


# === Form Dispatcher ===

class FormDispatcher:
    """Dispatch S-expression forms to their handlers."""

    def __init__(self, strict: bool = True):
        """Initialize dispatcher.

        Args:
            strict: If True, raise on unknown forms. If False, skip them.
        """
        self.strict = strict

    def dispatch(self, expr: SExpr, world: GrueWorld) -> None:
        """Dispatch a single top-level form to its handler."""
        if not isinstance(expr, SList) or len(expr) == 0:
            raise FormParseError(f"Expected top-level form, got {expr}")

        form_sym = expr[0]
        if not isinstance(form_sym, Symbol):
            raise FormParseError(f"Expected form name, got {form_sym}")

        name = form_sym.name.lower()
        handler = get_form_handler(name)

        if handler is None:
            if self.strict:
                raise FormParseError(f"Unknown top-level form: {name}")
            return  # Skip in non-strict mode

        handler(expr, world)

    def dispatch_all(self, exprs: list[SExpr], world: GrueWorld) -> None:
        """Dispatch multiple top-level forms."""
        for expr in exprs:
            self.dispatch(expr, world)
