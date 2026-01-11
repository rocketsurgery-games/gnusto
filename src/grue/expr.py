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
"""

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .sexpr import SExpr, Symbol, Keyword, SList, parse


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
        if not isinstance(head, Symbol):
            raise EvalError(f"Expected function name, got: {head}")

        name = head.name

        if name in self._builtins:
            return self._builtins[name](form)

        # Check user-defined functions
        if name in self._functions:
            return self._call_function(name, form)

        raise EvalError(f"Unknown function: {name}")

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
        return loc == "PLAYER"

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
