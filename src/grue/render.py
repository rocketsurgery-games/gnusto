"""
Render spec evaluation for visual composition.

A render spec is a mixed list that produces a prompt and reference images
when evaluated. The prompt is assembled from interleaved text and entity
references. Objects/rooms contribute their :description to the prompt;
references contribute only their rendered image (no text).

    :render ("A brass lantern with glass panels"
             :ref "assets/objects/lantern.png")

    :render (@terminal-room-bg "with the following objects:" :contents)

Render spec elements:
    Strings         - Literal text added to prompt
    @room/@object   - Contributes :description to prompt + rendered image as reference
    @reference      - Contributes only rendered image (no text) - caller wraps with text
    Expressions     - Evaluated with `self` bound to the entity being rendered
    :ref "path"     - Static file reference image (path relative to assets dir)
    :ref-size N     - Override reference size for this render (default 384)
    :anchor @obj    - Re-include atomic ref to reduce drift in deep compositions
    :contents       - Contributes contained objects' :descriptions + rendered images

Example:
    ; Reference - just a named render spec (no :description)
    (reference @terminal-room-bg
      :render "A large 1980s computer lab...")

    ; Reference using static image
    (reference @hacker-portrait
      :render (:ref "refs/hacker.jpg"))

    ; Room composing references with descriptive text
    (room @terminal-room
      :render ("In the" @terminal-room-bg "with the following objects:" :contents))

    When @terminal-room is rendered, if it contains @hacker and @pc:
    - Prompt: "In the with the following objects: hacker, pc"
    - Refs: [rendered @terminal-room-bg, rendered @hacker, rendered @pc]
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

from .sexpr import SExpr, Symbol, Keyword, SList
from .expr import ExprEvaluator, Environment, GrueFn


class RenderError(Exception):
    """Error during render spec evaluation."""
    pass


@dataclass
class ObjectRef:
    """Reference to another entity to render.

    When encountered in a render spec:
    - Objects/rooms: contribute :description to prompt + rendered image
    - References: contribute only rendered image (no text contribution)
    """
    name: str
    ref_size: int | None = None  # Override ref-size for this reference


@dataclass
class ContentsMarker:
    """Marker for :contents in a render spec.

    When encountered, contributes:
    - The :descriptions of objects at this location to the prompt
    - The rendered images of those objects as references
    """
    pass


@dataclass
class ThroughMarker:
    """Marker for (:through @portal @room) in a render spec.

    When the portal is open, contributes:
    - Descriptive text about what's visible through the portal
    - The target room's rendered image as a reference

    When the portal is closed, contributes nothing.
    """
    portal: str      # Entity ID of the door/portal
    target: str      # Entity ID of the room to show


# Type alias for prompt parts
PromptPart = Union[str, ObjectRef, ContentsMarker, ThroughMarker]


@dataclass
class RenderResult:
    """Result of evaluating a render spec.

    Attributes:
        prompt_parts: Ordered list of prompt components (strings, ObjectRefs, ContentsMarker)
        ref_paths: List of file paths to static reference images (:ref values)
        anchors: List of object names to re-include as anchors
        ref_size: Override reference size (from :ref-size)
    """
    prompt_parts: list[PromptPart] = field(default_factory=list)
    ref_paths: list[str] = field(default_factory=list)
    anchors: list[str] = field(default_factory=list)
    ref_size: int | None = None

    @property
    def prompt(self) -> str:
        """Join string parts into a single prompt string, normalizing whitespace."""
        raw = "".join(p for p in self.prompt_parts if isinstance(p, str))
        # Collapse multiple spaces from gaps left by non-string parts
        return " ".join(raw.split())

    @property
    def object_refs(self) -> list["ObjectRef"]:
        """Extract ObjectRef parts from prompt_parts."""
        return [p for p in self.prompt_parts if isinstance(p, ObjectRef)]

    @property
    def include_contents(self) -> bool:
        """True if any ContentsMarker in prompt_parts."""
        return any(isinstance(p, ContentsMarker) for p in self.prompt_parts)


def evaluate_render_spec(
    spec: SExpr,
    entity_name: str,
    state: Any,  # WorldState protocol
    functions: dict[str, GrueFn] | None = None,
) -> RenderResult:
    """Evaluate a render spec to produce a RenderResult.

    Render spec can be:
    - None: No render spec
    - String: Prompt-only (no refs)
    - (fn () ...): Function that returns a render spec (string or list)
    - List: Full render spec with prompt strings, refs, and options

    Args:
        spec: The render spec SExpr
        entity_name: The object/room being rendered (bound to `self`)
        state: WorldState for property access and expression evaluation
        functions: User-defined functions available during evaluation

    Returns:
        RenderResult containing prompt_parts, references, and options

    Raises:
        RenderError: If the spec is malformed or evaluation fails
    """
    if spec is None:
        return RenderResult()

    # String: check if it's an object reference (starts with @)
    if isinstance(spec, str):
        if spec.startswith("@"):
            # Object reference returned from expression evaluation
            return RenderResult(prompt_parts=[ObjectRef(name=spec)])
        return RenderResult(prompt_parts=[spec])

    # Symbol: treat as object reference (e.g., returned from a conditional render fn)
    if isinstance(spec, Symbol):
        name = spec.name
        if name.startswith("@"):
            return RenderResult(prompt_parts=[ObjectRef(name=name)])
        else:
            # Other symbols - try to evaluate
            return RenderResult(prompt_parts=[str(spec)])

    # Function: evaluate it first, then process the result
    if isinstance(spec, SList) and len(spec) >= 1:
        first = spec[0]
        if isinstance(first, Symbol) and first.name == "fn":
            # It's a (fn () ...) - evaluate it
            evaluated = _evaluate_fn_spec(spec, entity_name, state, functions)
            # Recursively process the result (could be string or list)
            return evaluate_render_spec(evaluated, entity_name, state, functions)

    # Must be a list at this point
    if not isinstance(spec, SList):
        raise RenderError(f"Render spec must be a string, fn, or list, got {type(spec).__name__}")

    result = RenderResult()
    current_ref_size: int | None = None

    items = list(spec.items)
    i = 0

    while i < len(items):
        item = items[i]

        # Keywords with values: :ref, :ref-size, :anchor
        if isinstance(item, Keyword):
            kw_name = item.name

            if kw_name == "ref":
                # :ref "path/to/image.png" - static file reference (no prompt contribution)
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
                # :contents - contributes contained objects' descriptions + images
                result.prompt_parts.append(ContentsMarker())
                i += 1
                continue

            else:
                # Unknown keyword - could be object property access in expression
                # Pass through to expression evaluation below
                pass

        # String literals - add to prompt parts
        if isinstance(item, str):
            result.prompt_parts.append(item)
            i += 1
            continue

        # Object references (@obj) - add to prompt parts as ObjectRef
        if isinstance(item, Symbol):
            name = item.name
            if name.startswith("@"):
                result.prompt_parts.append(ObjectRef(name=name, ref_size=current_ref_size))
                i += 1
                continue
            elif name == "self":
                # `self` in prompt context - resolve to entity name
                result.prompt_parts.append(entity_name)
                i += 1
                continue
            # Other symbols - try to evaluate as expression
            try:
                value = _evaluate_expression(item, entity_name, state, functions)
                if value is not None:
                    result.prompt_parts.append(str(value))
            except Exception as e:
                raise RenderError(f"Failed to evaluate symbol {name}: {e}")
            i += 1
            continue

        # Expressions (SList) - check for special forms first, then evaluate
        if isinstance(item, SList):
            # Check for (:through @portal @target) form
            if len(item) >= 3:
                first = item[0]
                if isinstance(first, Keyword) and first.name == "through":
                    portal = item[1]
                    target = item[2]
                    if isinstance(portal, Symbol) and isinstance(target, Symbol):
                        result.prompt_parts.append(ThroughMarker(portal.name, target.name))
                        i += 1
                        continue
                    else:
                        raise RenderError(
                            f":through requires two @symbols, got {type(portal).__name__} and {type(target).__name__}"
                        )

            # Generic expression - evaluate with self binding
            try:
                value = _evaluate_expression(item, entity_name, state, functions)
                # None or empty results are skipped (for (when ...) that returns nil)
                if value is not None and value != "" and value != []:
                    if isinstance(value, list):
                        # Join list results
                        result.prompt_parts.append(" ".join(str(v) for v in value if v))
                    else:
                        result.prompt_parts.append(str(value))
            except Exception as e:
                raise RenderError(f"Failed to evaluate expression: {e}")
            i += 1
            continue

        # Other types - convert to string
        result.prompt_parts.append(str(item))
        i += 1

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


def _evaluate_fn_spec(
    fn_expr: SList,
    entity_name: str,
    state: Any,
    functions: dict[str, GrueFn] | None,
) -> Any:
    """Evaluate a (fn () body) expression with `self` bound.

    Returns the result of calling the function, which should be
    a string or list suitable for further render spec processing.
    """
    # Parse the fn: (fn (params) body)
    if len(fn_expr) < 3:
        raise RenderError(f"fn requires params and body, got {fn_expr}")

    params_expr = fn_expr[1]
    body = fn_expr[2]

    # Validate params (should be empty for render fns, but allow any)
    params = []
    if isinstance(params_expr, SList):
        for p in params_expr.items:
            if isinstance(p, Symbol):
                name = p.name[1:] if p.name.startswith("?") else p.name
                params.append(name)

    # Evaluate body with self bound
    evaluator = ExprEvaluator(state, functions or {})
    env = Environment(bindings={"self": entity_name})

    result = evaluator.eval(body, env)

    # If result is a Python list (from quote), convert to SList for further processing
    if isinstance(result, list):
        # Recursively convert Python list to SList
        return _list_to_sexpr(result)

    return result


def _list_to_sexpr(lst: list) -> SExpr:
    """Convert a Python list back to SExpr for render spec processing."""
    items = []
    for item in lst:
        if isinstance(item, list):
            items.append(_list_to_sexpr(item))
        elif isinstance(item, str) and item.startswith(":"):
            # Keyword
            items.append(Keyword(item[1:]))
        elif isinstance(item, str) and item.startswith("@"):
            # Symbol (object ref)
            items.append(Symbol(item))
        else:
            items.append(item)
    return SList(items)


def has_render_spec(entity: Any) -> bool:
    """Check if an entity (object or room) has a render spec."""
    return hasattr(entity, "render") and entity.render is not None


def get_render_spec(entity: Any) -> SExpr | None:
    """Get the render spec from an entity, or None if not present."""
    if hasattr(entity, "render"):
        return entity.render
    return None
