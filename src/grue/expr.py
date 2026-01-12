"""
Expression evaluator.

This module provides:
- Predicate evaluation (boolean expressions)
- Effect execution (state mutations)
- User-defined functions via (defn name (args) body)
- Type checking for expressions

Built-in Predicates:
    (has-flag OBJ FLAG)       - Check if object has flag
    (= A B)                   - Equality
    (> A B), (< A B), etc     - Numeric comparisons
    (and EXPR ...)            - Logical and
    (or EXPR ...)             - Logical or
    (not EXPR)                - Logical not
    (loc OBJ)                 - Get object location
    (prop OBJ PROP)           - Get object property value
    (flags OBJ)               - Get object flags
    (visible? OBJ)            - Is object visible to player
    (held? OBJ)               - Is object held by player
    (here? OBJ)               - Is object in player's room
    (in? OBJ CONTAINER)       - Is object in container
    (room? LOC)               - Is location a room
    (in-room? OBJ ROOM ...)   - Is object in any of listed rooms
    (any COLL PRED)           - Any element satisfies predicate
    (all COLL PRED)           - All elements satisfy predicate
    (exit? ACTOR DIR)         - Check if exit exists from actor's room
    (exit-to ACTOR DIR)       - Get destination room for exit
    (exit-via ACTOR DIR)      - Get door object for exit (if any)
    (queued? EVENT)           - Check if event is currently queued

Built-in Effects:
    (move! OBJ DEST)          - Move object to destination
    (set-flag! OBJ FLAG)      - Set flag on object
    (clear-flag! OBJ FLAG)    - Clear flag from object
    (set-prop! OBJ PROP VAL)  - Set property on object
    (set! GLOBAL VAL)         - Set global variable
    (inc! GLOBAL)             - Increment global by 1
    (inc! GLOBAL AMT)         - Increment global by amount
    (seq EFFECT ...)          - Execute effects in order
    (when COND EFFECT)        - Conditional effect
    (defn NAME (PARAMS) BODY) - Define user function
    (queue! EVENT)            - Queue an event (indefinite)
    (queue! EVENT N)          - Queue an event with countdown
    (dequeue! EVENT)          - Remove event from queue
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .sexpr import SExpr, Symbol, Keyword, SList, parse


@dataclass
class GrueFn:
    """A first-class function (lambda/closure).

    Functions capture their parameter names and body expression.
    When called, parameters are bound to arguments and the body is evaluated.

    Examples:
        (fn () (success))                    ; No params
        (fn (?x) (+ ?x 1))                   ; One param
        (fn (?a ?b) (and (held? ?a) ?b))     ; Multiple params

    Note: Parameter names conventionally start with ? but this is not required.
    The ? is stripped when stored (e.g., ?item -> "item").
    """
    params: list[str]
    body: SExpr
    # Captured bindings from lexical scope (for closures)
    captured: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        param_str = " ".join(f"?{p}" for p in self.params)
        return f"(fn ({param_str}) ...)"


# === Behavior Result Types ===
# These are returned by behavior expressions like (success), (blocked), etc.

@dataclass
class BehaviorSuccess:
    """Result indicating the behavior succeeded.

    Usage in behaviors:
        (success)                           ; Simple success
        (success :message "Done!")          ; With context
        (success :effect (move! @key @player))  ; With effect
    """
    context: dict[str, Any] = field(default_factory=dict)
    effects: list[SExpr] = field(default_factory=list)


@dataclass
class BehaviorBlocked:
    """Result indicating the behavior was blocked.

    Usage in behaviors:
        (blocked :reason locked)
        (blocked :reason no-key :message "The door is locked.")
    """
    reason: str = "unknown"
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorRedirect:
    """Result indicating the action should be redirected.

    Usage in behaviors:
        (redirect (do @other-door :open))
    """
    action: SExpr
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorDefault:
    """Result indicating the default action should be used.

    Usage in behaviors:
        (default)                           ; Use default
        (default (do @container :open))     ; With explicit action
    """
    action: SExpr | None = None
    context: dict[str, Any] = field(default_factory=dict)


class WorldState(Protocol):
    """Protocol for world state access."""

    def get_object_flag(self, obj: str, flag: str) -> bool:
        """Check if object has flag."""
        ...

    def get_object_location(self, obj: str) -> str | None:
        """Get object's current location."""
        ...

    def get_object_property(self, obj: str, prop: str) -> Any:
        """Get object property value."""
        ...

    def get_object_flags(self, obj: str) -> set[str]:
        """Get all flags on object."""
        ...

    def get_global(self, name: str) -> Any:
        """Get global variable value."""
        ...

    def get_player_location(self) -> str:
        """Get player's current room."""
        ...

    def get_player_name(self) -> str:
        """Get the player entity name (e.g., '@player' or 'PLAYER')."""
        ...

    def get_inventory(self) -> list[str]:
        """Get player's inventory."""
        ...

    def is_visible(self, obj: str) -> bool:
        """Check if object is visible to player."""
        ...

    def is_room(self, loc: str) -> bool:
        """Check if location is a room."""
        ...

    def get_contents(self, container: str) -> list[str]:
        """Get contents of container/room."""
        ...

    def get_exit(self, actor: str, direction: str) -> tuple[str, str | None] | None:
        """Get exit info for direction from actor's room. Returns (destination, via) or None."""
        ...

    def is_queued(self, event: str) -> bool:
        """Check if an event is currently queued."""
        ...


class MutableWorldState(WorldState, Protocol):
    """Protocol for mutable world state (effects)."""

    def set_object_flag(self, obj: str, flag: str) -> None:
        """Set flag on object."""
        ...

    def clear_object_flag(self, obj: str, flag: str) -> None:
        """Clear flag from object."""
        ...

    def set_object_property(self, obj: str, prop: str, value: Any) -> None:
        """Set object property value."""
        ...

    def set_global(self, name: str, value: Any) -> None:
        """Set global variable value."""
        ...

    def move_object(self, obj: str, dest: str) -> None:
        """Move object to new location."""
        ...

    def queue_event(self, event: str, countdown: int | None = None) -> None:
        """Queue an event. countdown=None means indefinite."""
        ...

    def dequeue_event(self, event: str) -> None:
        """Remove an event from the queue."""
        ...


class EvalError(Exception):
    """Error during expression evaluation."""
    pass


class ExprEvaluator:
    """
    Evaluate S-expressions against a world state.

    This evaluator handles both predicates (returning bool)
    and value expressions (returning any type).

    Supports user-defined functions via define_function():
        evaluator.define_function("double", ["x"], parse("(+ x x)"))
        evaluator.eval(parse("(double 5)"))  # Returns 10
    """

    def __init__(self, state: WorldState, functions: dict[str, tuple[list[str], SExpr]] | None = None):
        self.state = state
        # User-defined functions: name -> (params, body)
        self._functions: dict[str, tuple[list[str], SExpr]] = functions if functions is not None else {}
        # Map of special form names to handlers
        self._builtins: dict[str, Callable[..., Any]] = {
            # Boolean operators
            "and": self._eval_and,
            "or": self._eval_or,
            "not": self._eval_not,

            # Comparisons
            "=": self._eval_eq,
            ">": self._eval_gt,
            "<": self._eval_lt,
            ">=": self._eval_gte,
            "<=": self._eval_lte,

            # Object queries
            "has-flag": self._eval_has_flag,
            "loc": self._eval_loc,
            "prop": self._eval_prop,
            "flags": self._eval_flags,

            # Convenience predicates
            "visible?": self._eval_visible,
            "held?": self._eval_held,
            "here?": self._eval_here,
            "in?": self._eval_in,
            "contained-in?": self._eval_in,  # alias for in?
            "held-by?": self._eval_held_by,
            "at?": self._eval_at,
            "room?": self._eval_room,
            "in-room?": self._eval_in_room,
            "room-has-flag?": self._eval_room_has_flag,

            # Collections/quantifiers
            "any": self._eval_any,
            "all": self._eval_all,
            "inventory": self._eval_inventory,
            "contents": self._eval_contents,

            # Exit queries (for movement)
            "exit?": self._eval_exit_exists,
            "exit-to": self._eval_exit_to,
            "exit-via": self._eval_exit_via,

            # Event queue
            "queued?": self._eval_queued,

            # First-class functions
            "fn": self._eval_fn,
            "if": self._eval_if,
            "let": self._eval_let,
            "cond": self._eval_cond,

            # Behavior results
            "success": self._eval_success,
            "blocked": self._eval_blocked,
            "redirect": self._eval_redirect,
            "default": self._eval_default,
        }

    def eval(self, expr: SExpr) -> Any:
        """Evaluate an S-expression."""
        if isinstance(expr, bool):
            return expr
        if isinstance(expr, int):
            return expr
        if isinstance(expr, str):
            return expr
        if isinstance(expr, Symbol):
            # Handle boolean literals
            if expr.name.lower() == "true":
                return True
            if expr.name.lower() == "false":
                return False
            # Symbol lookup - try global first, then treat as literal
            try:
                return self.state.get_global(expr.name)
            except (KeyError, AttributeError):
                # Return as string literal (object name, flag name, etc.)
                return expr.name
        if isinstance(expr, Keyword):
            # Keywords evaluate to their string name (for property names)
            return expr.name
        if isinstance(expr, SList):
            return self._eval_form(expr)

        raise EvalError(f"Cannot evaluate: {expr}")

    def _eval_form(self, form: SList) -> Any:
        """Evaluate a list form (function call)."""
        if len(form) == 0:
            raise EvalError("Empty form")

        head = form[0]

        # If head is a symbol, look up builtins and user functions
        if isinstance(head, Symbol):
            name = head.name

            if name in self._builtins:
                return self._builtins[name](form)

            # Check user-defined functions
            if name in self._functions:
                return self._call_function(name, form)

            raise EvalError(f"Unknown function: {name}")

        # If head is a list, evaluate it - might be a fn expression
        if isinstance(head, SList):
            fn_value = self.eval(head)
            if isinstance(fn_value, GrueFn):
                # Apply the function to remaining arguments
                args = [self.eval(arg) for arg in form.items[1:]]
                return self.call_fn(fn_value, args)
            raise EvalError(f"Cannot call non-function: {fn_value}")

        raise EvalError(f"Expected function name or expression, got: {head}")

    def define_function(self, name: str, params: list[str], body: SExpr) -> None:
        """
        Define a user function.

        Args:
            name: Function name
            params: List of parameter names
            body: S-expression for function body
        """
        self._functions[name] = (params, body)

    def _call_function(self, name: str, form: SList) -> Any:
        """Call a user-defined function with argument binding."""
        params, body = self._functions[name]
        args = form.items[1:]

        if len(args) != len(params):
            raise EvalError(
                f"Function '{name}' expects {len(params)} arguments, got {len(args)}"
            )

        # Evaluate arguments
        arg_values = [self.eval(arg) for arg in args]

        # Substitute parameters in body
        result_expr = body
        for param, value in zip(params, arg_values):
            result_expr = self._substitute(result_expr, param, value)

        return self.eval(result_expr)

    # === Boolean operators ===

    def _eval_and(self, form: SList) -> bool:
        """(and EXPR ...)"""
        for item in form.items[1:]:
            if not self.eval(item):
                return False
        return True

    def _eval_or(self, form: SList) -> bool:
        """(or EXPR ...)"""
        for item in form.items[1:]:
            if self.eval(item):
                return True
        return False

    def _eval_not(self, form: SList) -> bool:
        """(not EXPR)"""
        if len(form) != 2:
            raise EvalError(f"'not' expects 1 argument, got {len(form) - 1}")
        return not self.eval(form[1])

    # === Comparisons ===

    def _eval_eq(self, form: SList) -> bool:
        """(= A B)"""
        if len(form) != 3:
            raise EvalError(f"'=' expects 2 arguments, got {len(form) - 1}")
        a = self.eval(form[1])
        b = self.eval(form[2])
        return a == b

    def _eval_gt(self, form: SList) -> bool:
        """(> A B)"""
        if len(form) != 3:
            raise EvalError(f"'>' expects 2 arguments, got {len(form) - 1}")
        return self.eval(form[1]) > self.eval(form[2])

    def _eval_lt(self, form: SList) -> bool:
        """(< A B)"""
        if len(form) != 3:
            raise EvalError(f"'<' expects 2 arguments, got {len(form) - 1}")
        return self.eval(form[1]) < self.eval(form[2])

    def _eval_gte(self, form: SList) -> bool:
        """(>= A B)"""
        if len(form) != 3:
            raise EvalError(f"'>=' expects 2 arguments, got {len(form) - 1}")
        return self.eval(form[1]) >= self.eval(form[2])

    def _eval_lte(self, form: SList) -> bool:
        """(<= A B)"""
        if len(form) != 3:
            raise EvalError(f"'<=' expects 2 arguments, got {len(form) - 1}")
        return self.eval(form[1]) <= self.eval(form[2])

    # === Object queries ===

    def _eval_has_flag(self, form: SList) -> bool:
        """(has-flag OBJ FLAG)"""
        if len(form) != 3:
            raise EvalError(f"'has-flag' expects 2 arguments, got {len(form) - 1}")
        obj = self.eval(form[1])
        flag = self.eval(form[2])
        return self.state.get_object_flag(obj, flag)

    def _eval_loc(self, form: SList) -> str | None:
        """(loc OBJ)"""
        if len(form) != 2:
            raise EvalError(f"'loc' expects 1 argument, got {len(form) - 1}")
        obj = self.eval(form[1])
        return self.state.get_object_location(obj)

    def _eval_prop(self, form: SList) -> Any:
        """(prop OBJ PROP)"""
        if len(form) != 3:
            raise EvalError(f"'prop' expects 2 arguments, got {len(form) - 1}")
        obj = self.eval(form[1])
        prop = self.eval(form[2])
        return self.state.get_object_property(obj, prop)

    def _eval_flags(self, form: SList) -> set[str]:
        """(flags OBJ)"""
        if len(form) != 2:
            raise EvalError(f"'flags' expects 1 argument, got {len(form) - 1}")
        obj = self.eval(form[1])
        return self.state.get_object_flags(obj)

    # === Convenience predicates ===

    def _eval_visible(self, form: SList) -> bool:
        """(visible? OBJ)"""
        if len(form) != 2:
            raise EvalError(f"'visible?' expects 1 argument, got {len(form) - 1}")
        obj = self.eval(form[1])
        return self.state.is_visible(obj)

    def _eval_held(self, form: SList) -> bool:
        """(held? OBJ) - shorthand for (= (loc OBJ) PLAYER)"""
        if len(form) != 2:
            raise EvalError(f"'held?' expects 1 argument, got {len(form) - 1}")
        obj = self.eval(form[1])
        loc = self.state.get_object_location(obj)
        return loc == self.state.get_player_name()

    def _eval_here(self, form: SList) -> bool:
        """(here? OBJ) - shorthand for (= (loc OBJ) (loc PLAYER))"""
        if len(form) != 2:
            raise EvalError(f"'here?' expects 1 argument, got {len(form) - 1}")
        obj = self.eval(form[1])
        obj_loc = self.state.get_object_location(obj)
        player_loc = self.state.get_player_location()
        return obj_loc == player_loc

    def _eval_in(self, form: SList) -> bool:
        """(in? OBJ CONTAINER)"""
        if len(form) != 3:
            raise EvalError(f"'in?' expects 2 arguments, got {len(form) - 1}")
        obj = self.eval(form[1])
        container = self.eval(form[2])
        return self.state.get_object_location(obj) == container

    def _eval_held_by(self, form: SList) -> bool:
        """(held-by? OBJ ACTOR) - check if OBJ's location is ACTOR."""
        if len(form) != 3:
            raise EvalError(f"'held-by?' expects 2 arguments, got {len(form) - 1}")
        obj = self.eval(form[1])
        actor = self.eval(form[2])
        return self.state.get_object_location(obj) == actor

    def _eval_at(self, form: SList) -> bool:
        """(at? OBJ ACTOR) - check if OBJ is at ACTOR's location (same room)."""
        if len(form) != 3:
            raise EvalError(f"'at?' expects 2 arguments, got {len(form) - 1}")
        obj = self.eval(form[1])
        actor = self.eval(form[2])
        obj_loc = self.state.get_object_location(obj)
        actor_loc = self.state.get_object_location(actor)
        return obj_loc == actor_loc

    def _eval_room(self, form: SList) -> bool:
        """(room? LOC)"""
        if len(form) != 2:
            raise EvalError(f"'room?' expects 1 argument, got {len(form) - 1}")
        loc = self.eval(form[1])
        return self.state.is_room(loc)

    def _eval_in_room(self, form: SList) -> bool:
        """(in-room? OBJ ROOM1 ROOM2 ...) - check if object is in any of the listed rooms.

        Typically used as (in-room? PLAYER MASS-AVE SMITH-ST) to check
        if the player is in one of several specific rooms.
        """
        if len(form) < 3:
            raise EvalError(f"'in-room?' expects at least 2 arguments, got {len(form) - 1}")

        obj = self.eval(form[1])
        obj_loc = self.state.get_object_location(obj)
        if obj_loc is None:
            return False

        # Check if object's location is any of the specified rooms
        for room_arg in form.items[2:]:
            room_name = self.eval(room_arg)
            if obj_loc == room_name:
                return True

        return False

    def _eval_room_has_flag(self, form: SList) -> bool:
        """(room-has-flag? FLAG) - check if player's current room has the specified flag."""
        if len(form) != 2:
            raise EvalError(f"'room-has-flag?' expects 1 argument, got {len(form) - 1}")

        flag = self.eval(form[1])
        player_room = self.state.get_player_location()
        return self.state.get_object_flag(player_room, flag)

    # === Collections/quantifiers ===

    def _eval_inventory(self, form: SList) -> list[str]:
        """(inventory PLAYER) - get player's inventory"""
        if len(form) != 2:
            raise EvalError(f"'inventory' expects 1 argument, got {len(form) - 1}")
        return self.state.get_inventory()

    def _eval_contents(self, form: SList) -> list[str]:
        """(contents CONTAINER) - get contents of container"""
        if len(form) != 2:
            raise EvalError(f"'contents' expects 1 argument, got {len(form) - 1}")
        container = self.eval(form[1])
        return self.state.get_contents(container)

    # === Exit queries (for movement) ===

    def _eval_exit_exists(self, form: SList) -> bool:
        """(exit? ACTOR DIRECTION) - check if exit exists from actor's room."""
        if len(form) != 3:
            raise EvalError(f"'exit?' expects 2 arguments, got {len(form) - 1}")
        actor = self.eval(form[1])
        direction = self.eval(form[2])
        result = self.state.get_exit(actor, direction)
        return result is not None

    def _eval_exit_to(self, form: SList) -> str | None:
        """(exit-to ACTOR DIRECTION) - get destination room for exit."""
        if len(form) != 3:
            raise EvalError(f"'exit-to' expects 2 arguments, got {len(form) - 1}")
        actor = self.eval(form[1])
        direction = self.eval(form[2])
        result = self.state.get_exit(actor, direction)
        return result[0] if result else None

    def _eval_exit_via(self, form: SList) -> str | None:
        """(exit-via ACTOR DIRECTION) - get door object for exit (if any)."""
        if len(form) != 3:
            raise EvalError(f"'exit-via' expects 2 arguments, got {len(form) - 1}")
        actor = self.eval(form[1])
        direction = self.eval(form[2])
        result = self.state.get_exit(actor, direction)
        return result[1] if result else None

    # === Event queue ===

    def _eval_queued(self, form: SList) -> bool:
        """(queued? EVENT) - check if event is currently queued."""
        if len(form) != 2:
            raise EvalError(f"'queued?' expects 1 argument, got {len(form) - 1}")
        event = self.eval(form[1])
        return self.state.is_queued(event)

    # === First-class functions ===

    def _eval_fn(self, form: SList) -> GrueFn:
        """(fn (params) body) - create a function value.

        Examples:
            (fn () (success))
            (fn (?x) (+ ?x 1))
            (fn (?a ?b) (if (> ?a ?b) ?a ?b))
        """
        if len(form) < 3:
            raise EvalError(f"'fn' expects (fn (params) body), got {len(form)} elements")

        params_expr = form[1]
        body = form[2]

        # Parse parameter list
        params: list[str] = []
        if isinstance(params_expr, SList):
            for p in params_expr.items:
                if isinstance(p, Symbol):
                    # Strip leading ? if present
                    name = p.name[1:] if p.name.startswith("?") else p.name
                    params.append(name)
                else:
                    raise EvalError(f"'fn' parameter must be a symbol, got {p}")
        elif params_expr is not None:
            raise EvalError(f"'fn' params must be a list, got {params_expr}")

        return GrueFn(params=params, body=body)

    def _eval_if(self, form: SList) -> Any:
        """(if condition then-expr else-expr) - conditional expression.

        Examples:
            (if (held? @key) (success) (blocked :reason no-key))
            (if (> score 10) "high" "low")
        """
        if len(form) < 3 or len(form) > 4:
            raise EvalError(f"'if' expects 2-3 arguments, got {len(form) - 1}")

        condition = self.eval(form[1])

        if condition:
            return self.eval(form[2])
        elif len(form) == 4:
            return self.eval(form[3])
        else:
            return None

    def _eval_let(self, form: SList) -> Any:
        """(let ((name value) ...) body) - local bindings.

        Examples:
            (let ((x 1)) (+ x 2))
            (let ((a (loc @player)) (b @room)) (= a b))
        """
        if len(form) != 3:
            raise EvalError(f"'let' expects 2 arguments, got {len(form) - 1}")

        bindings_expr = form[1]
        body = form[2]

        if not isinstance(bindings_expr, SList):
            raise EvalError(f"'let' bindings must be a list, got {bindings_expr}")

        # Evaluate bindings and substitute
        result_expr = body
        for binding in bindings_expr.items:
            if not isinstance(binding, SList) or len(binding) != 2:
                raise EvalError(f"'let' binding must be (name value), got {binding}")

            name_sym = binding[0]
            if not isinstance(name_sym, Symbol):
                raise EvalError(f"'let' binding name must be a symbol, got {name_sym}")

            name = name_sym.name
            if name.startswith("?"):
                name = name[1:]

            value = self.eval(binding[1])
            result_expr = self._substitute(result_expr, name, value)
            # Also substitute with ? prefix for convenience
            result_expr = self._substitute(result_expr, f"?{name}", value)

        return self.eval(result_expr)

    def _eval_cond(self, form: SList) -> Any:
        """(cond (test1 result1) (test2 result2) ... (true default))

        Evaluates conditions in order and returns the result of the first
        matching branch.
        """
        for clause in form.items[1:]:
            if not isinstance(clause, SList) or len(clause) < 2:
                raise EvalError(f"Invalid cond clause: {clause}")

            test = clause[0]
            result = clause[1]

            if self.eval(test):
                return self.eval(result)

        return None  # No clause matched

    def call_fn(self, fn: GrueFn, args: list[Any]) -> Any:
        """Call a GrueFn with the given arguments.

        This is used by the behavior system and can also be used for
        general function application.
        """
        if len(args) != len(fn.params):
            raise EvalError(
                f"Function expects {len(fn.params)} arguments, got {len(args)}"
            )

        # Start with captured bindings, then add parameters
        result_expr = fn.body
        for name, value in fn.captured.items():
            result_expr = self._substitute(result_expr, name, value)
            result_expr = self._substitute(result_expr, f"?{name}", value)

        for param, value in zip(fn.params, args):
            result_expr = self._substitute(result_expr, param, value)
            result_expr = self._substitute(result_expr, f"?{param}", value)

        return self.eval(result_expr)

    # === Behavior Results ===

    def _parse_kwargs(self, form: SList, start: int = 1) -> dict[str, Any]:
        """Parse keyword arguments from a form starting at given index."""
        kwargs: dict[str, Any] = {}
        items = list(form.items[start:])
        i = 0
        while i < len(items):
            if isinstance(items[i], Keyword):
                key = items[i].name
                if i + 1 < len(items):
                    # Don't evaluate the value - keep it as SExpr for effects
                    kwargs[key] = items[i + 1]
                    i += 2
                else:
                    raise EvalError(f"Keyword :{key} has no value")
            else:
                i += 1
        return kwargs

    def _parse_context_list(self, expr: SExpr) -> dict[str, Any]:
        """Parse context in format ((key value) (key value) ...)."""
        result: dict[str, Any] = {}
        if isinstance(expr, SList):
            for item in expr.items:
                if isinstance(item, SList) and len(item) >= 2:
                    key = item[0]
                    val = item[1]
                    key_str = key.name if isinstance(key, Symbol) else str(key)
                    val_str = val.name if isinstance(val, Symbol) else self.eval(val)
                    result[key_str] = val_str
        return result

    def _eval_success(self, form: SList) -> BehaviorSuccess:
        """(success [:key value ...])

        Examples:
            (success)
            (success :message "Done!")
            (success :effect (move! @key @player))
            (success :context ((mechanism push-bar)))  ; Legacy format
        """
        kwargs = self._parse_kwargs(form)
        context: dict[str, Any] = {}
        effects: list[SExpr] = []

        for key, val in kwargs.items():
            if key == "effect":
                effects.append(val)  # Keep as SExpr
            elif key == "effects":
                # Allow list of effects
                if isinstance(val, SList):
                    effects.extend(val.items)
            elif key == "context":
                # Legacy format: ((key value) ...)
                context.update(self._parse_context_list(val))
            else:
                # Direct key-value pair
                if isinstance(val, Symbol):
                    context[key] = val.name
                elif isinstance(val, SList):
                    context[key] = val  # Keep as SExpr for complex values
                else:
                    context[key] = self.eval(val)

        return BehaviorSuccess(context=context, effects=effects)

    def _eval_blocked(self, form: SList) -> BehaviorBlocked:
        """(blocked :reason REASON [:key value ...])

        Examples:
            (blocked :reason locked)
            (blocked :reason no-key :message "The door is locked.")
        """
        kwargs = self._parse_kwargs(form)
        reason = "unknown"
        context: dict[str, Any] = {}

        for key, val in kwargs.items():
            if key == "reason":
                if isinstance(val, Symbol):
                    reason = val.name
                else:
                    reason = str(self.eval(val))
            elif key == "context":
                context.update(self._parse_context_list(val))
            else:
                if isinstance(val, Symbol):
                    context[key] = val.name
                else:
                    context[key] = self.eval(val)

        return BehaviorBlocked(reason=reason, context=context)

    def _eval_redirect(self, form: SList) -> BehaviorRedirect:
        """(redirect ACTION [:key value ...]) or (redirect :action ACTION)

        Examples:
            (redirect (do @other-door :open))
            (redirect :action (do @other-door :open))
        """
        if len(form) < 2:
            raise EvalError("'redirect' requires an action")

        action = None
        context: dict[str, Any] = {}

        # Check if first arg is action (SList) or keywords
        if isinstance(form[1], SList):
            action = form[1]
            kwargs = self._parse_kwargs(form, start=2)
        else:
            kwargs = self._parse_kwargs(form, start=1)

        for k, v in kwargs.items():
            if k == "action":
                # Don't evaluate action - keep as SExpr
                action = v
            elif k == "context":
                context.update(self._parse_context_list(v))
            else:
                if isinstance(v, Symbol):
                    context[k] = v.name
                else:
                    context[k] = self.eval(v)

        if action is None:
            raise EvalError("'redirect' requires an action")

        return BehaviorRedirect(action=action, context=context)

    def _eval_default(self, form: SList) -> BehaviorDefault:
        """(default [ACTION] [:key value ...])

        Examples:
            (default)
            (default (do @container :open))
            (default :action (do @container :open))
        """
        action = None
        context: dict[str, Any] = {}

        if len(form) > 1:
            # Check if first arg is an action (SList) or keyword
            if isinstance(form[1], SList):
                action = form[1]
                kwargs = self._parse_kwargs(form, start=2)
            else:
                kwargs = self._parse_kwargs(form, start=1)

            for k, v in kwargs.items():
                if k == "action":
                    # Don't evaluate action - keep as SExpr
                    action = v
                elif k == "context":
                    context.update(self._parse_context_list(v))
                else:
                    if isinstance(v, Symbol):
                        context[k] = v.name
                    else:
                        context[k] = self.eval(v)

        return BehaviorDefault(action=action, context=context)

    # === Quantifiers ===

    def _eval_any(self, form: SList) -> bool:
        """(any COLLECTION (lambda (x) PRED))"""
        if len(form) != 3:
            raise EvalError(f"'any' expects 2 arguments, got {len(form) - 1}")

        collection = self.eval(form[1])
        lambda_form = form[2]

        if not isinstance(lambda_form, SList) or len(lambda_form) < 3:
            raise EvalError("'any' requires a lambda as second argument")
        if lambda_form[0] != Symbol("lambda"):
            raise EvalError("'any' requires a lambda as second argument")

        # Extract parameter name and body
        params = lambda_form[1]
        if not isinstance(params, SList) or len(params) != 1:
            raise EvalError("Lambda must have exactly 1 parameter")
        param_name = params[0]
        if not isinstance(param_name, Symbol):
            raise EvalError("Lambda parameter must be a symbol")

        body = lambda_form[2]

        # Evaluate predicate for each item
        for item in collection:
            # Create a new evaluator with the bound variable
            result = self._eval_with_binding(param_name.name, item, body)
            if result:
                return True
        return False

    def _eval_all(self, form: SList) -> bool:
        """(all COLLECTION (lambda (x) PRED))"""
        if len(form) != 3:
            raise EvalError(f"'all' expects 2 arguments, got {len(form) - 1}")

        collection = self.eval(form[1])
        lambda_form = form[2]

        if not isinstance(lambda_form, SList) or len(lambda_form) < 3:
            raise EvalError("'all' requires a lambda as second argument")
        if lambda_form[0] != Symbol("lambda"):
            raise EvalError("'all' requires a lambda as second argument")

        params = lambda_form[1]
        if not isinstance(params, SList) or len(params) != 1:
            raise EvalError("Lambda must have exactly 1 parameter")
        param_name = params[0]
        if not isinstance(param_name, Symbol):
            raise EvalError("Lambda parameter must be a symbol")

        body = lambda_form[2]

        for item in collection:
            result = self._eval_with_binding(param_name.name, item, body)
            if not result:
                return False
        return True

    def _eval_with_binding(self, name: str, value: Any, expr: SExpr) -> Any:
        """Evaluate expression with a temporary variable binding."""
        # Simple approach: substitute the variable in the expression
        substituted = self._substitute(expr, name, value)
        return self.eval(substituted)

    def _substitute(self, expr: SExpr, name: str, value: Any) -> SExpr:
        """Substitute all occurrences of symbol `name` with `value`."""
        if isinstance(expr, Symbol):
            if expr.name == name:
                if isinstance(value, str):
                    return Symbol(value)
                return value
            return expr
        elif isinstance(expr, SList):
            # Check for nested lambda that shadows the variable
            if (len(expr) >= 2 and
                isinstance(expr[0], Symbol) and expr[0].name == "lambda"):
                params = expr[1]
                if isinstance(params, SList):
                    for p in params:
                        if isinstance(p, Symbol) and p.name == name:
                            # Variable is shadowed, don't substitute in body
                            return expr
            # Recursively substitute in list items
            return SList([self._substitute(item, name, value) for item in expr.items])
        else:
            return expr


class EffectExecutor:
    """
    Execute effects (state mutations) against a world state.

    Supports user-defined functions via (defn name (params) body):
        executor.execute(parse("(defn at-lobby? () (= (loc PLAYER) LOBBY))"))
        evaluator.eval(parse("(at-lobby?)"))  # Uses shared function registry
    """

    def __init__(
        self,
        state: MutableWorldState,
        functions: dict[str, tuple[list[str], SExpr]] | None = None
    ):
        self.state = state
        # Shared function registry between evaluator and executor
        self._functions: dict[str, tuple[list[str], SExpr]] = functions if functions is not None else {}
        self._predicates = ExprEvaluator(state, self._functions)
        self._effects: dict[str, Callable[..., None]] = {
            "move!": self._exec_move,
            "set-flag!": self._exec_set_flag,
            "clear-flag!": self._exec_clear_flag,
            "set-prop!": self._exec_set_prop,
            "set!": self._exec_set_global,
            "inc!": self._exec_inc,
            "seq": self._exec_seq,
            "when": self._exec_when,
            "defn": self._exec_defn,
            "queue!": self._exec_queue,
            "dequeue!": self._exec_dequeue,
        }

    def execute(self, expr: SExpr) -> None:
        """Execute an effect expression."""
        if not isinstance(expr, SList):
            raise EvalError(f"Effect must be a list, got: {expr}")
        if len(expr) == 0:
            raise EvalError("Empty effect")

        head = expr[0]
        if not isinstance(head, Symbol):
            raise EvalError(f"Expected effect name, got: {head}")

        name = head.name
        if name not in self._effects:
            raise EvalError(f"Unknown effect: {name}")

        self._effects[name](expr)

    def _eval(self, expr: SExpr) -> Any:
        """Evaluate a value expression."""
        return self._predicates.eval(expr)

    def _exec_move(self, form: SList) -> None:
        """(move! OBJ DEST)"""
        if len(form) != 3:
            raise EvalError(f"'move!' expects 2 arguments, got {len(form) - 1}")
        obj = self._eval(form[1])
        dest = self._eval(form[2])
        self.state.move_object(obj, dest)

    def _exec_set_flag(self, form: SList) -> None:
        """(set-flag! OBJ FLAG)"""
        if len(form) != 3:
            raise EvalError(f"'set-flag!' expects 2 arguments, got {len(form) - 1}")
        obj = self._eval(form[1])
        flag = self._eval(form[2])
        self.state.set_object_flag(obj, flag)

    def _exec_clear_flag(self, form: SList) -> None:
        """(clear-flag! OBJ FLAG)"""
        if len(form) != 3:
            raise EvalError(f"'clear-flag!' expects 2 arguments, got {len(form) - 1}")
        obj = self._eval(form[1])
        flag = self._eval(form[2])
        self.state.clear_object_flag(obj, flag)

    def _exec_set_prop(self, form: SList) -> None:
        """(set-prop! OBJ PROP VALUE)"""
        if len(form) != 4:
            raise EvalError(f"'set-prop!' expects 3 arguments, got {len(form) - 1}")
        obj = self._eval(form[1])
        prop = self._eval(form[2])
        value = self._eval(form[3])
        self.state.set_object_property(obj, prop, value)

    def _exec_set_global(self, form: SList) -> None:
        """(set! GLOBAL VALUE)"""
        if len(form) != 3:
            raise EvalError(f"'set!' expects 2 arguments, got {len(form) - 1}")
        # Don't evaluate the global name - use it as-is
        if not isinstance(form[1], Symbol):
            raise EvalError("'set!' first argument must be a symbol")
        global_name = form[1].name
        value = self._eval(form[2])
        self.state.set_global(global_name, value)

    def _exec_inc(self, form: SList) -> None:
        """(inc! GLOBAL) or (inc! GLOBAL AMOUNT)"""
        if len(form) < 2 or len(form) > 3:
            raise EvalError(f"'inc!' expects 1-2 arguments, got {len(form) - 1}")

        if not isinstance(form[1], Symbol):
            raise EvalError("'inc!' first argument must be a symbol")
        global_name = form[1].name

        amount = 1
        if len(form) == 3:
            amount = self._eval(form[2])

        current = self.state.get_global(global_name)
        self.state.set_global(global_name, current + amount)

    def _exec_seq(self, form: SList) -> None:
        """(seq EFFECT ...)"""
        for effect in form.items[1:]:
            self.execute(effect)

    def _exec_when(self, form: SList) -> None:
        """(when COND EFFECT)"""
        if len(form) != 3:
            raise EvalError(f"'when' expects 2 arguments, got {len(form) - 1}")

        condition = form[1]
        effect = form[2]

        if self._eval(condition):
            self.execute(effect)

    def _exec_defn(self, form: SList) -> None:
        """
        (defn NAME (PARAMS) BODY)

        Define a user function that can be called in expressions.

        Example:
            (defn at-lobby? () (= (loc PLAYER) LOBBY))
            (defn door-open? (door) (not (has-flag door LOCKED)))
        """
        if len(form) != 4:
            raise EvalError(f"'defn' expects 3 arguments (name, params, body), got {len(form) - 1}")

        # Extract function name
        name_expr = form[1]
        if not isinstance(name_expr, Symbol):
            raise EvalError(f"'defn' name must be a symbol, got: {name_expr}")
        name = name_expr.name

        # Extract parameter list
        params_expr = form[2]
        if not isinstance(params_expr, SList):
            raise EvalError(f"'defn' params must be a list, got: {params_expr}")
        params: list[str] = []
        for p in params_expr.items:
            if not isinstance(p, Symbol):
                raise EvalError(f"'defn' parameter must be a symbol, got: {p}")
            params.append(p.name)

        # Body is kept as-is (not evaluated until called)
        body = form[3]

        # Register in shared function dictionary
        self._functions[name] = (params, body)

    def _exec_queue(self, form: SList) -> None:
        """(queue! EVENT) or (queue! EVENT COUNTDOWN)"""
        if len(form) < 2 or len(form) > 3:
            raise EvalError(f"'queue!' expects 1-2 arguments, got {len(form) - 1}")

        event = self._eval(form[1])
        countdown = None
        if len(form) == 3:
            countdown = self._eval(form[2])

        self.state.queue_event(event, countdown)

    def _exec_dequeue(self, form: SList) -> None:
        """(dequeue! EVENT)"""
        if len(form) != 2:
            raise EvalError(f"'dequeue!' expects 1 argument, got {len(form) - 1}")

        event = self._eval(form[1])
        self.state.dequeue_event(event)


def eval_predicate(expr: str | SExpr, state: WorldState) -> bool:
    """
    Convenience function to evaluate a predicate expression.

    Args:
        expr: S-expression string or parsed expression
        state: World state to evaluate against

    Returns:
        Boolean result of predicate
    """
    if isinstance(expr, str):
        expr = parse(expr)
    evaluator = ExprEvaluator(state)
    result = evaluator.eval(expr)
    return bool(result)


def execute_effect(expr: str | SExpr, state: MutableWorldState) -> None:
    """
    Convenience function to execute an effect expression.

    Args:
        expr: S-expression string or parsed expression
        state: Mutable world state to modify
    """
    if isinstance(expr, str):
        expr = parse(expr)
    executor = EffectExecutor(state)
    executor.execute(expr)
