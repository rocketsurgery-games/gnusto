"""
Render spec & brief evaluation for Grue entities (the "variant" model).

An entity's illustration is keyed by a small, finite set of **variants**. Asset
filenames are *derived* from the entity name plus a variant token, so authors
never hand-maintain filenames:

    @microwave + "open"  ->  microwave-open.png

Two fields describe an entity's art:

- ``:render`` selects the current **variant** (only needed when an entity has
  more than one). It is one of:
    * absent      -> a single variant; key = ``<base>.png``
    * a string    -> a literal asset key (escape hatch for sharing one image
                     across entities, e.g. a door that reuses its room's art)
    * ``(fn () ...)`` returning a variant token string -> key ``<base>-<token>.png``

- ``:rdesc`` is the generation **brief** (prompt text), one of:
    * a string                          -> the brief for the single variant
    * a map ``(:open "..." :closed "...")`` -> a brief per variant token

The variant set is therefore *declared data* (the ``:rdesc`` map keys), which
makes the keyset trivially enumerable for static pre-generation. The world-level
``:visual-style`` keyword-map supplies a style prefix (``:prompt``) and hooks
(``:palette``, ``:aspect-ratio``, ...) woven into briefs.

``:render`` selectors are evaluated lazily with ``self`` bound to the entity and
must be pure, so the same state always selects the same variant.
"""

from typing import Any

from .expr import Environment, ExprEvaluator, GrueFn
from .sexpr import SExpr, SList, Symbol

# Derived-filename extension. All pre-generated assets are PNGs for now.
ASSET_EXT = ".png"


class RenderError(Exception):
    """Error during render spec/brief evaluation."""

    pass


def asset_base(entity_name: str) -> str:
    """Base asset name for an entity: '@microwave' -> 'microwave'."""
    return entity_name.lstrip("@")


def is_renderable(entity: Any) -> bool:
    """An entity has art if it declares either a :render selector or a :rdesc."""
    return (
        getattr(entity, "render", None) is not None
        or getattr(entity, "rdesc", None) is not None
    )


def _eval_selector(
    spec: SExpr,
    entity_name: str,
    state: Any,
    functions: dict[str, GrueFn] | None,
) -> str | None:
    """Evaluate a (fn () ...) :render selector to a variant token string."""
    if isinstance(spec, SList) and len(spec) >= 1:
        first = spec[0]
        if isinstance(first, Symbol) and first.name == "fn":
            if len(spec) < 3:
                raise RenderError(f"fn requires params and body, got {spec}")
            body = spec[2]
            evaluator = ExprEvaluator(state, functions or {})
            env = Environment(bindings={"self": entity_name})
            result = evaluator.eval(body, env)
            return None if result is None else str(result)
    raise RenderError(
        f":render selector must be a string or (fn () ...), got {type(spec).__name__}"
    )


def resolve_asset_key(
    entity_name: str,
    render: SExpr,
    state: Any,  # WorldState protocol
    functions: dict[str, GrueFn] | None = None,
) -> str:
    """Resolve the asset key (filename) for an entity's current state.

    - render is None   -> "<base>.png" (single variant)
    - render is a str  -> the string verbatim (literal alias / shared key)
    - render is (fn..) -> "<base>-<token>.png" (or "<base>.png" if token empty)

    Callers should gate on is_renderable() first.
    """
    base = asset_base(entity_name)
    if render is None:
        return base + ASSET_EXT
    if isinstance(render, str):
        return render
    token = _eval_selector(render, entity_name, state, functions)
    if not token:
        return base + ASSET_EXT
    return f"{base}-{token}{ASSET_EXT}"


def render_variants(entity: Any) -> list[str] | None:
    """The declared variant tokens (from the :rdesc map), or None if single."""
    rdesc = getattr(entity, "rdesc", None)
    if isinstance(rdesc, dict):
        return list(rdesc.keys())
    return None


def render_keyset(entity_name: str, entity: Any) -> set[str]:
    """All asset keys this entity can resolve to (declarative; for manifests).

    Does not evaluate the selector — the keyset comes from the declared
    variants, so it is well-defined without runtime state.
    """
    render = getattr(entity, "render", None)
    if isinstance(render, str):
        return {render}  # literal alias -> single shared key
    base = asset_base(entity_name)
    variants = render_variants(entity)
    if variants:
        return {f"{base}-{v}{ASSET_EXT}" for v in variants}
    if is_renderable(entity):
        return {base + ASSET_EXT}
    return set()


def brief_for_variant(entity: Any, variant: str | None = None) -> str | None:
    """The render brief for a variant (or the single brief).

    - :rdesc is a map  -> the brief for `variant`
    - :rdesc is a str  -> that brief
    - no :rdesc        -> falls back to :description if it is a plain string
    """
    rdesc = getattr(entity, "rdesc", None)
    if isinstance(rdesc, dict):
        return rdesc.get(variant) if variant is not None else None
    if isinstance(rdesc, str):
        return rdesc
    desc = getattr(entity, "description", None)
    return desc if isinstance(desc, str) else None


def assemble_brief(visual_style: dict[str, Any] | None, brief_text: str | None) -> str:
    """Assemble a generation prompt from the world style and an entity brief.

    Basic assembly: style ``:prompt`` prefix + entity brief + ``:palette`` hint.
    Spatial framing and reference images are layered on later (filfre fill,
    gnusto-eaec.4). Pure; safe for static manifest building.
    """
    style = visual_style or {}
    parts: list[str] = []
    prompt_prefix = style.get("prompt")
    if prompt_prefix:
        parts.append(str(prompt_prefix))
    if brief_text:
        parts.append(brief_text)
    palette = style.get("palette")
    if palette:
        parts.append(f"Palette: {palette}.")
    return " ".join(parts)


def has_render_spec(entity: Any) -> bool:
    """Check if an entity has a :render selector (string or fn)."""
    return getattr(entity, "render", None) is not None


def get_render_spec(entity: Any) -> SExpr | None:
    """Get the :render selector from an entity, or None if not present."""
    return getattr(entity, "render", None)
