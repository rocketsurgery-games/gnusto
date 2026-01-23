"""
Partial evaluator for Grue expressions.

This module provides a Reducer that performs symbolic reduction on Grue expressions:
- Inlines pure function calls (defn)
- Simplifies conditionals when branches are statically determined
- Propagates constants through expressions
- Handles recursion conservatively (depth limit)

The goal is to produce reduced expressions where state dependencies are explicit,
enabling downstream abstract interpretation analysis.

Example:
    Before: (waxer-next-loc ?loc true)
    After:  (cond ((= ?loc @inf-5) @inf-4) ((= ?loc @inf-4) @inf-3) ...)
"""

from dataclasses import dataclass, field
from typing import Any

from .sexpr import SExpr, Symbol, Keyword, SList, to_string

# Types that are considered "primitive" for equality comparison
_PRIMITIVE_TYPES = (str, int, bool, type(None))
from .forms import GrueWorld, GrueFunction


class ReduceError(Exception):
    """Error during expression reduction."""
    pass


@dataclass
class ReductionStats:
    """Statistics from reduction pass."""
    functions_inlined: int = 0
    conditionals_simplified: int = 0
    constants_propagated: int = 0
    recursion_limits_hit: int = 0

    def __repr__(self) -> str:
        return (f"ReductionStats(inlined={self.functions_inlined}, "
                f"simplified={self.conditionals_simplified}, "
                f"constants={self.constants_propagated}, "
                f"recursion_limits={self.recursion_limits_hit})")


@dataclass
class Reducer:
    """Partial evaluator for Grue expressions.

    The Reducer performs symbolic reduction on expressions without executing
    side effects. It operates on the pure subset of Grue, treating stateful
    operations (property reads, location checks) as opaque.

    Key operations:
    1. Function inlining: Replaces (func-name args...) with the function body,
       substituting parameters with arguments.
    2. Constant propagation: Replaces references to (def name value) with value.
    3. Conditional simplification: Evaluates (if ...), (cond ...), (and ...),
       (or ...) when the condition is a known constant.
    4. Recursion handling: Tracks inline depth and marks expressions as
       "irreducible" when the limit is hit.

    Attributes:
        world: The GrueWorld providing function and constant definitions.
        max_inline_depth: Maximum depth for recursive function inlining.
        stats: Statistics about reductions performed.
    """
    world: GrueWorld
    max_inline_depth: int = 10
    stats: ReductionStats = field(default_factory=ReductionStats)

    # Track inline call stack to detect recursion
    _inline_stack: list[str] = field(default_factory=list)

    def reduce(self, expr: SExpr) -> SExpr:
        """Reduce an expression as much as possible.

        Args:
            expr: The expression to reduce.

        Returns:
            A reduced expression with functions inlined and constants propagated.
            The result is semantically equivalent under any variable bindings.
        """
        self._inline_stack = []
        return self._reduce(expr, bindings={})

    def _reduce(self, expr: SExpr, bindings: dict[str, SExpr]) -> SExpr:
        """Internal reduction with current bindings."""
        # Atoms
        if isinstance(expr, Symbol):
            return self._reduce_symbol(expr, bindings)
        if isinstance(expr, (Keyword, str, int, bool)) or expr is None:
            return expr

        # Lists (function calls, special forms)
        if isinstance(expr, SList):
            if len(expr.items) == 0:
                return expr
            return self._reduce_list(expr, bindings)

        return expr

    def _reduce_symbol(self, sym: Symbol, bindings: dict[str, SExpr]) -> SExpr:
        """Reduce a symbol reference."""
        name = sym.name

        # Check for parameter binding (from function inlining)
        # Note: parameters may or may not have leading ?
        lookup_name = name[1:] if name.startswith("?") else name
        if lookup_name in bindings:
            return bindings[lookup_name]

        # Check for constant (from (def name value))
        if name in self.world.constants:
            self.stats.constants_propagated += 1
            value = self.world.constants[name]
            # Convert Python value back to SExpr if needed
            return self._value_to_sexpr(value)

        return sym

    def _reduce_list(self, expr: SList, bindings: dict[str, SExpr]) -> SExpr:
        """Reduce a list expression."""
        head = expr.items[0]
        if not isinstance(head, Symbol):
            # Non-symbol head - just reduce children
            return SList([self._reduce(item, bindings) for item in expr.items])

        name = head.name

        # Special forms that need custom handling
        if name == "if":
            return self._reduce_if(expr, bindings)
        if name == "cond":
            return self._reduce_cond(expr, bindings)
        if name == "and":
            return self._reduce_and(expr, bindings)
        if name == "or":
            return self._reduce_or(expr, bindings)
        if name == "not":
            return self._reduce_not(expr, bindings)
        if name == "let":
            return self._reduce_let(expr, bindings)
        if name == "fn":
            # Lambda - reduce body but with awareness of new bindings
            return self._reduce_fn(expr, bindings)
        if name == "quote":
            # Quoted expressions are not reduced
            return expr
        if name == "quasiquote":
            return self._reduce_quasiquote(expr, bindings)

        # Check for (= a b) where we can statically determine equality
        if name == "=":
            return self._reduce_equality(expr, bindings)

        # Check if it's a user-defined function call
        if name in self.world.functions:
            return self._reduce_function_call(name, expr, bindings)

        # Otherwise, reduce all children
        reduced_items = [self._reduce(item, bindings) for item in expr.items]
        return SList(reduced_items)

    def _reduce_if(self, expr: SList, bindings: dict[str, SExpr]) -> SExpr:
        """Reduce (if condition then else?)."""
        if len(expr.items) < 3:
            return expr  # Malformed, leave as-is

        cond = self._reduce(expr.items[1], bindings)
        then_expr = expr.items[2]
        else_expr = expr.items[3] if len(expr.items) > 3 else None

        # Try to evaluate condition
        if isinstance(cond, bool):
            self.stats.conditionals_simplified += 1
            if cond:
                return self._reduce(then_expr, bindings)
            elif else_expr:
                return self._reduce(else_expr, bindings)
            else:
                return Symbol("nil")

        # Condition not constant - reduce both branches
        reduced_then = self._reduce(then_expr, bindings)
        if else_expr:
            reduced_else = self._reduce(else_expr, bindings)
            return SList([Symbol("if"), cond, reduced_then, reduced_else])
        return SList([Symbol("if"), cond, reduced_then])

    def _reduce_cond(self, expr: SList, bindings: dict[str, SExpr]) -> SExpr:
        """Reduce (cond (test1 result1) (test2 result2) ...).

        Key principle for analysis: if there are unknown tests, preserve the
        cond structure so downstream analysis can see the relationship between
        test conditions and results. Only eliminate branches when tests are
        definitively known.
        """
        reduced_clauses = []

        for clause in expr.items[1:]:
            if not isinstance(clause, SList) or len(clause.items) < 2:
                # Malformed clause, keep as-is
                reduced_clauses.append(clause)
                continue

            test = self._reduce(clause.items[0], bindings)

            # Check if test is a known constant
            if isinstance(test, bool):
                if test:
                    if not reduced_clauses:
                        # No preceding unknown clauses - we can take this branch
                        self.stats.conditionals_simplified += 1
                        result = clause.items[1]
                        return self._reduce(result, bindings)
                    else:
                        # There are preceding unknown clauses - keep this as
                        # the else branch so analysis can see all possibilities
                        reduced_result = self._reduce(clause.items[1], bindings)
                        reduced_clauses.append(SList([test, reduced_result]))
                        # Stop processing - this is the catch-all
                        break
                else:
                    # This clause never matches - skip it
                    self.stats.conditionals_simplified += 1
                    continue

            # Test not constant - reduce the result and keep clause
            reduced_result = self._reduce(clause.items[1], bindings)
            reduced_clauses.append(SList([test, reduced_result]))

        if not reduced_clauses:
            # All clauses eliminated - return nil
            return Symbol("nil")

        return SList([Symbol("cond")] + reduced_clauses)

    def _reduce_equality(self, expr: SList, bindings: dict[str, SExpr]) -> SExpr:
        """Reduce (= a b) when we can determine result statically.

        Cases handled:
        - (= x x) for any identical expressions -> true
        - (= @sym1 @sym2) for different object symbols -> false
        - (= lit1 lit2) for different literals -> false
        - (= lit1 lit2) for same literals -> true
        """
        if len(expr.items) != 3:
            # Not a binary equality, just reduce children
            return SList([self._reduce(item, bindings) for item in expr.items])

        left = self._reduce(expr.items[1], bindings)
        right = self._reduce(expr.items[2], bindings)

        # Identical expressions
        if left == right:
            self.stats.conditionals_simplified += 1
            return True

        # Two different object symbols (@name) can never be equal
        if (isinstance(left, Symbol) and isinstance(right, Symbol) and
            left.name.startswith("@") and right.name.startswith("@")):
            self.stats.conditionals_simplified += 1
            return False

        # Two same-type primitives (strings, ints, bools)
        if isinstance(left, _PRIMITIVE_TYPES) and isinstance(right, _PRIMITIVE_TYPES):
            # Both are primitive literals of compatible types
            self.stats.conditionals_simplified += 1
            return left == right

        return SList([Symbol("="), left, right])

    def _reduce_and(self, expr: SList, bindings: dict[str, SExpr]) -> SExpr:
        """Reduce (and expr1 expr2 ...)."""
        reduced_args = []

        for arg in expr.items[1:]:
            reduced = self._reduce(arg, bindings)

            if isinstance(reduced, bool):
                if not reduced:
                    # Short-circuit: false and anything is false
                    self.stats.conditionals_simplified += 1
                    return False
                # true - skip this arg, continue with rest
                self.stats.conditionals_simplified += 1
                continue

            reduced_args.append(reduced)

        if not reduced_args:
            # (and) or all args were true
            return True
        if len(reduced_args) == 1:
            return reduced_args[0]
        return SList([Symbol("and")] + reduced_args)

    def _reduce_or(self, expr: SList, bindings: dict[str, SExpr]) -> SExpr:
        """Reduce (or expr1 expr2 ...)."""
        reduced_args = []

        for arg in expr.items[1:]:
            reduced = self._reduce(arg, bindings)

            if isinstance(reduced, bool):
                if reduced:
                    # Short-circuit: true or anything is true
                    self.stats.conditionals_simplified += 1
                    return True
                # false - skip this arg, continue with rest
                self.stats.conditionals_simplified += 1
                continue

            reduced_args.append(reduced)

        if not reduced_args:
            # (or) or all args were false
            return False
        if len(reduced_args) == 1:
            return reduced_args[0]
        return SList([Symbol("or")] + reduced_args)

    def _reduce_not(self, expr: SList, bindings: dict[str, SExpr]) -> SExpr:
        """Reduce (not expr)."""
        if len(expr.items) != 2:
            return expr

        reduced = self._reduce(expr.items[1], bindings)
        if isinstance(reduced, bool):
            self.stats.conditionals_simplified += 1
            return not reduced

        return SList([Symbol("not"), reduced])

    def _reduce_let(self, expr: SList, bindings: dict[str, SExpr]) -> SExpr:
        """Reduce (let ((name value) ...) body ...)."""
        if len(expr.items) < 3:
            return expr

        binding_list = expr.items[1]
        if not isinstance(binding_list, SList):
            return expr

        # Extend bindings with let bindings
        new_bindings = dict(bindings)

        for binding in binding_list.items:
            if isinstance(binding, SList) and len(binding.items) >= 2:
                name_expr = binding.items[0]
                if isinstance(name_expr, Symbol):
                    name = name_expr.name
                    # Strip leading ? if present
                    if name.startswith("?"):
                        name = name[1:]
                    value = self._reduce(binding.items[1], new_bindings)
                    new_bindings[name] = value

        # Reduce body expressions
        reduced_bodies = [self._reduce(body, new_bindings) for body in expr.items[2:]]

        # If all binding values are constants, we can potentially inline
        # For now, keep let structure but with reduced bodies
        reduced_binding_list = []
        for binding in binding_list.items:
            if isinstance(binding, SList) and len(binding.items) >= 2:
                name_expr = binding.items[0]
                name = name_expr.name if isinstance(name_expr, Symbol) else str(name_expr)
                lookup_name = name[1:] if name.startswith("?") else name
                if lookup_name in new_bindings:
                    reduced_binding_list.append(SList([name_expr, new_bindings[lookup_name]]))
                else:
                    reduced_binding_list.append(binding)
            else:
                reduced_binding_list.append(binding)

        return SList([Symbol("let"), SList(reduced_binding_list)] + reduced_bodies)

    def _reduce_fn(self, expr: SList, bindings: dict[str, SExpr]) -> SExpr:
        """Reduce (fn (params) body)."""
        if len(expr.items) < 3:
            return expr

        params = expr.items[1]
        body = expr.items[2]

        # Get parameter names to exclude from bindings
        param_names = set()
        if isinstance(params, SList):
            for p in params.items:
                if isinstance(p, Symbol):
                    name = p.name
                    if name.startswith("?"):
                        name = name[1:]
                    param_names.add(name)

        # Filter bindings to exclude shadowed parameters
        filtered_bindings = {k: v for k, v in bindings.items() if k not in param_names}

        # Reduce the body
        reduced_body = self._reduce(body, filtered_bindings)

        return SList([Symbol("fn"), params, reduced_body])

    def _reduce_quasiquote(self, expr: SList, bindings: dict[str, SExpr]) -> SExpr:
        """Reduce quasiquote expressions by reducing unquoted parts."""
        if len(expr.items) != 2:
            return expr

        def reduce_qq(e: SExpr) -> SExpr:
            if isinstance(e, SList):
                if len(e.items) >= 2 and isinstance(e.items[0], Symbol):
                    if e.items[0].name == "unquote":
                        # Reduce the unquoted expression
                        return SList([Symbol("unquote"), self._reduce(e.items[1], bindings)])
                    if e.items[0].name == "unquote-splicing":
                        return SList([Symbol("unquote-splicing"), self._reduce(e.items[1], bindings)])
                # Recurse into list
                return SList([reduce_qq(item) for item in e.items])
            return e

        return SList([Symbol("quasiquote"), reduce_qq(expr.items[1])])

    def _reduce_function_call(self, func_name: str, expr: SList, bindings: dict[str, SExpr]) -> SExpr:
        """Inline a user-defined function call."""
        func = self.world.functions[func_name]

        # Check recursion depth
        if self._inline_stack.count(func_name) >= self.max_inline_depth:
            self.stats.recursion_limits_hit += 1
            # Return with reduced args but don't inline
            reduced_args = [self._reduce(arg, bindings) for arg in expr.items[1:]]
            return SList([Symbol(func_name)] + reduced_args)

        # Check for direct recursion
        if func_name in self._inline_stack:
            # Already in call stack - this is recursive
            # We could inline a few times, but for safety just mark limit
            if self._inline_stack.count(func_name) >= 2:
                self.stats.recursion_limits_hit += 1
                reduced_args = [self._reduce(arg, bindings) for arg in expr.items[1:]]
                return SList([Symbol(func_name)] + reduced_args)

        # Build new bindings from arguments
        args = expr.items[1:]
        new_bindings = dict(bindings)

        for i, param in enumerate(func.params):
            if i < len(args):
                # Reduce argument before binding
                new_bindings[param] = self._reduce(args[i], bindings)
            else:
                # Missing arg - use nil
                new_bindings[param] = Symbol("nil")

        # Push to inline stack
        self._inline_stack.append(func_name)
        self.stats.functions_inlined += 1

        try:
            # Reduce the function body with new bindings
            result = self._reduce(func.body, new_bindings)
            return result
        finally:
            self._inline_stack.pop()

    def _value_to_sexpr(self, value: Any) -> SExpr:
        """Convert a Python value to SExpr."""
        if isinstance(value, (str, int, bool)):
            return value
        if value is None:
            return Symbol("nil")
        if isinstance(value, list):
            return SList([self._value_to_sexpr(v) for v in value])
        # Assume it's already an SExpr
        return value


def reduce_expr(world: GrueWorld, expr: SExpr, max_depth: int = 10) -> tuple[SExpr, ReductionStats]:
    """Convenience function to reduce an expression.

    Args:
        world: The GrueWorld providing definitions.
        expr: The expression to reduce.
        max_depth: Maximum inline recursion depth.

    Returns:
        Tuple of (reduced_expression, statistics).
    """
    reducer = Reducer(world=world, max_inline_depth=max_depth)
    result = reducer.reduce(expr)
    return result, reducer.stats
