"""
Render spec evaluation for Grue entities.

A render spec on an entity evaluates to an image filename (relative to
the game's assets directory).

    :render "refs/lantern.png"
    :render (fn () (if (:open ?self) "refs/door-open.png" "refs/door-closed.png"))

The render spec is evaluated lazily at render time with `self` bound to
the entity being rendered.
"""

from typing import Any

from .sexpr import SExpr, Symbol, SList
from .expr import ExprEvaluator, Environment, GrueFn


class RenderError(Exception):
    """Error during render spec evaluation."""
    pass


def evaluate_render_spec(
    spec: SExpr,
    entity_name: str,
    state: Any,  # WorldState protocol
    functions: dict[str, GrueFn] | None = None,
) -> str | None:
    """Evaluate a render spec to produce an image filename.

    Render spec can be:
    - None: No render spec
    - String: Image filename, returned as-is
    - (fn () ...): Function evaluated with `self` bound; must return a filename

    Args:
        spec: The render spec SExpr
        entity_name: The object/room being rendered (bound to `self`)
        state: WorldState for property access and expression evaluation
        functions: User-defined functions available during evaluation

    Returns:
        An image filename (relative to game assets dir), or None if spec is None

    Raises:
        RenderError: If the spec is malformed or evaluation fails
    """
    if spec is None:
        return None

    # String: return as-is
    if isinstance(spec, str):
        return spec

    # Function: evaluate it
    if isinstance(spec, SList) and len(spec) >= 1:
        first = spec[0]
        if isinstance(first, Symbol) and first.name == "fn":
            return _evaluate_fn_spec(spec, entity_name, state, functions)

    raise RenderError(f"Render spec must be a string or (fn () ...), got {type(spec).__name__}")


def _evaluate_fn_spec(
    fn_expr: SList,
    entity_name: str,
    state: Any,
    functions: dict[str, GrueFn] | None,
) -> str:
    """Evaluate a (fn () body) expression with `self` bound.

    Returns the result as a string.
    """
    if len(fn_expr) < 3:
        raise RenderError(f"fn requires params and body, got {fn_expr}")

    body = fn_expr[2]

    evaluator = ExprEvaluator(state, functions or {})
    env = Environment(bindings={"self": entity_name})

    result = evaluator.eval(body, env)

    if result is None:
        return ""
    return str(result)


def has_render_spec(entity: Any) -> bool:
    """Check if an entity (object or room) has a render spec."""
    return hasattr(entity, "render") and entity.render is not None


def get_render_spec(entity: Any) -> SExpr | None:
    """Get the render spec from an entity, or None if not present."""
    if hasattr(entity, "render"):
        return entity.render
    return None
