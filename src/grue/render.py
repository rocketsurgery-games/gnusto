"""
Render spec evaluation for visual composition.

A render spec is a mixed list that produces a prompt string and reference
images when evaluated:

    :render ["A brass lantern with glass panels"
             :ref "assets/objects/lantern.png"]

    :render ["A " @microwave " door "
             (if (= (:state self) :open) "open" "closed")
             :ref "assets/microwave.png"
             :ref-size 384]

    :render ["A brass lantern on a wooden table in a stone cellar"
             :ref "assets/rooms/cellar.png"
             :contents]  ; Include rendered images of objects at this location

Render spec elements:
    Strings         - Concatenated to form the prompt
    @obj refs       - Resolved recursively, their rendered images become input references
    Expressions     - Evaluated with `self` bound to the entity being rendered
    :ref "path"     - Base reference image file path
    :ref-size N     - Override reference size for this render (default 384)
    :anchor @obj    - Re-include atomic ref to reduce drift in deep compositions
    :contents       - Include rendered images of objects at this location (rooms only)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .sexpr import SExpr, Symbol, Keyword, SList
from .expr import ExprEvaluator, Environment, GrueFn


class RenderError(Exception):
    """Error during render spec evaluation."""
    pass


@dataclass
class ObjectRef:
    """Reference to another object to render."""
    name: str
    ref_size: int | None = None  # Override ref-size for this reference


@dataclass
class RenderResult:
    """Result of evaluating a render spec.

    Attributes:
        prompt: The text prompt for image generation (concatenated strings/expressions)
        ref_paths: List of file paths to reference images (:ref values)
        object_refs: List of object references (@obj) to render recursively
        anchors: List of object names to re-include as anchors
        include_contents: Whether to include rendered images of contained objects
        ref_size: Override reference size (from :ref-size)
    """
    prompt: str = ""
    ref_paths: list[str] = field(default_factory=list)
    object_refs: list[ObjectRef] = field(default_factory=list)
    anchors: list[str] = field(default_factory=list)
    include_contents: bool = False
    ref_size: int | None = None


def evaluate_render_spec(
    spec: SExpr,
    entity_name: str,
    state: Any,  # WorldState protocol
    functions: dict[str, GrueFn] | None = None,
) -> RenderResult:
    """Evaluate a render spec to produce a RenderResult.

    Args:
        spec: The render spec SExpr (typically an SList)
        entity_name: The object/room being rendered (bound to `self`)
        state: WorldState for property access and expression evaluation
        functions: User-defined functions available during evaluation

    Returns:
        RenderResult containing prompt, references, and options

    Raises:
        RenderError: If the spec is malformed or evaluation fails
    """
    if spec is None:
        return RenderResult()

    if not isinstance(spec, SList):
        raise RenderError(f"Render spec must be a list, got {type(spec).__name__}")

    result = RenderResult()
    prompt_parts: list[str] = []
    current_ref_size: int | None = None

    items = list(spec.items)
    i = 0

    while i < len(items):
        item = items[i]

        # Keywords with values: :ref, :ref-size, :anchor
        if isinstance(item, Keyword):
            kw_name = item.name

            if kw_name == "ref":
                # :ref "path/to/image.png"
                if i + 1 >= len(items):
                    raise RenderError(":ref requires a path argument")
                path = items[i + 1]
                if not isinstance(path, str):
                    raise RenderError(f":ref path must be a string, got {type(path).__name__}")
                result.ref_paths.append(path)
                i += 2
                continue

            elif kw_name == "ref-size":
                # :ref-size 384
                if i + 1 >= len(items):
                    raise RenderError(":ref-size requires a number argument")
                size = items[i + 1]
                if not isinstance(size, int):
                    raise RenderError(f":ref-size must be an integer, got {type(size).__name__}")
                result.ref_size = size
                current_ref_size = size
                i += 2
                continue

            elif kw_name == "anchor":
                # :anchor @obj
                if i + 1 >= len(items):
                    raise RenderError(":anchor requires an object reference")
                anchor = items[i + 1]
                if not isinstance(anchor, Symbol):
                    raise RenderError(f":anchor must be a symbol, got {type(anchor).__name__}")
                result.anchors.append(anchor.name)
                i += 2
                continue

            elif kw_name == "contents":
                # :contents (standalone keyword, no value)
                result.include_contents = True
                i += 1
                continue

            else:
                # Unknown keyword - could be object property access in expression
                # Pass through to expression evaluation below
                pass

        # String literals - add to prompt
        if isinstance(item, str):
            prompt_parts.append(item)
            i += 1
            continue

        # Object references (@obj) - add to object refs
        if isinstance(item, Symbol):
            name = item.name
            if name.startswith("@"):
                result.object_refs.append(ObjectRef(name=name, ref_size=current_ref_size))
                i += 1
                continue
            elif name == "self":
                # `self` in prompt context - resolve to entity name
                prompt_parts.append(entity_name)
                i += 1
                continue
            # Other symbols - try to evaluate as expression
            try:
                value = _evaluate_expression(item, entity_name, state, functions)
                if value is not None:
                    prompt_parts.append(str(value))
            except Exception as e:
                raise RenderError(f"Failed to evaluate symbol {name}: {e}")
            i += 1
            continue

        # Expressions (SList) - evaluate with self binding
        if isinstance(item, SList):
            try:
                value = _evaluate_expression(item, entity_name, state, functions)
                # None or empty results are skipped (for (when ...) that returns nil)
                if value is not None and value != "" and value != []:
                    if isinstance(value, list):
                        # Join list results
                        prompt_parts.append(" ".join(str(v) for v in value if v))
                    else:
                        prompt_parts.append(str(value))
            except Exception as e:
                raise RenderError(f"Failed to evaluate expression: {e}")
            i += 1
            continue

        # Other types - convert to string
        prompt_parts.append(str(item))
        i += 1

    # Join prompt parts, collapsing multiple spaces
    result.prompt = " ".join(part.strip() for part in prompt_parts if part.strip())

    return result


def _evaluate_expression(
    expr: SExpr,
    entity_name: str,
    state: Any,
    functions: dict[str, GrueFn] | None,
) -> Any:
    """Evaluate an expression with `self` bound to the entity name."""
    evaluator = ExprEvaluator(state, functions or {})

    # Create environment with self binding
    env = Environment(bindings={"self": entity_name})
    evaluator._env = env

    return evaluator.eval(expr, env)


def has_render_spec(entity: Any) -> bool:
    """Check if an entity (object or room) has a render spec."""
    return hasattr(entity, "render") and entity.render is not None


def get_render_spec(entity: Any) -> SExpr | None:
    """Get the render spec from an entity, or None if not present."""
    if hasattr(entity, "render"):
        return entity.render
    return None
