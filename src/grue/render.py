"""
Render spec & brief evaluation for Grue entities (the "variant" model).

An entity's illustration is keyed by a small, finite set of **variants**. Asset
keys are *derived* from the entity name plus a variant **tag**, so authors never
hand-maintain filenames. Keys are **extension-less**; the runtime resolver finds
the file on disk across supported formats (.jpg/.png/.webp):

    @microwave + :open  ->  microwave-open   ->  assets/microwave-open.jpg

A variant tag is a **keyword** (``:open``) — a self-denoting name, distinct from
a string. A *string* in ``:render`` means something different: a verbatim asset
key. This keyword/string split is the type-directed contract:

- ``:render`` selects the current **variant** (only needed when an entity has
  more than one). It is one of:
    * absent              -> a single variant; key = ``<base>``
    * a keyword ``:tag``  -> key ``<base>-<tag>`` (a literal variant tag)
    * a string ``"key"``  -> that verbatim key (escape hatch for sharing one
                             image across entities, e.g. a door reusing its
                             room's art)
    * ``(fn () ...)`` returning a keyword tag -> key ``<base>-<tag>``
      (or a string for a verbatim key, or nil for ``<base>``)

- ``:rdesc`` is the generation **brief** (prompt text), one of:
    * a string                          -> the brief for the single variant
    * a map ``(:open "..." :closed "...")`` -> a brief per variant tag

The variant set is therefore *declared data* (the ``:rdesc`` map keys), which
makes the keyset trivially enumerable for static pre-generation. The world-level
``:visual-style`` keyword-map supplies a style prefix (``:prompt``) and hooks
(``:palette``, ``:aspect-ratio``, ...) woven into briefs.

``:render`` selectors are evaluated lazily with ``self`` bound to the entity and
must be pure, so the same state always selects the same variant.
"""

from dataclasses import dataclass
from typing import Any, Literal

from .expr import Environment, ExprEvaluator, GrueFn
from .sexpr import Keyword, SExpr, SList, Symbol


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
) -> Any:
    """Evaluate a (fn () ...) :render selector, returning its raw value.

    The result is interpreted by ``_interpret_render_value``: a ``Keyword`` is a
    variant tag, a ``str`` is a verbatim key, ``None`` falls back to the base.
    """
    if isinstance(spec, SList) and len(spec) >= 1:
        first = spec[0]
        if isinstance(first, Symbol) and first.name == "fn":
            if len(spec) < 3:
                raise RenderError(f"fn requires params and body, got {spec}")
            body = spec[2]
            evaluator = ExprEvaluator(state, functions or {})
            env = Environment(bindings={"self": entity_name})
            return evaluator.eval(body, env)
    raise RenderError(
        f":render selector must be a keyword, string, or (fn () ...), "
        f"got {type(spec).__name__}"
    )


def _interpret_render_value(base: str, value: Any) -> str:
    """Map a :render value (or selector result) to an asset key.

    Type-directed, mirroring the keyword/string distinction:

    - ``Keyword(name)`` -> ``"<base>-<name>"`` (a variant **tag**)
    - ``str``           -> the string verbatim (a literal/alias **key**); empty
                           string falls back to ``"<base>"``
    - ``None``          -> ``"<base>"`` (single variant)
    """
    if value is None:
        return base
    if isinstance(value, Keyword):
        return f"{base}-{value.name}"
    if isinstance(value, str):
        return value if value else base
    raise RenderError(
        f":render must yield a keyword tag or a string key, got {type(value).__name__}"
    )


def resolve_asset_key(
    entity_name: str,
    render: SExpr,
    state: Any,  # WorldState protocol
    functions: dict[str, GrueFn] | None = None,
) -> str:
    """Resolve the extension-less asset key for an entity's current state.

    - render is None      -> "<base>" (single variant)
    - render is a Keyword -> "<base>-<name>" (a literal variant tag)
    - render is a str     -> the string verbatim (literal alias / shared key)
    - render is (fn..)     -> interpret the returned keyword/str/None

    Keyword tags and string keys are distinct: ``:open`` -> ``<base>-open``,
    while ``"open"`` -> the verbatim key ``open``. The runtime resolver maps a
    key to a file on disk by trying supported extensions. Callers should gate on
    is_renderable() first.
    """
    base = asset_base(entity_name)
    if render is None:
        return base
    if isinstance(render, (str, Keyword)):
        return _interpret_render_value(base, render)
    value = _eval_selector(render, entity_name, state, functions)
    return _interpret_render_value(base, value)


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
        return {render}  # literal string -> verbatim alias / shared key
    base = asset_base(entity_name)
    variants = render_variants(entity)
    if variants:
        return {f"{base}-{v}" for v in variants}
    if isinstance(render, Keyword):
        return {f"{base}-{render.name}"}  # literal keyword tag, single variant
    if is_renderable(entity):
        return {base}
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


def _kind_style(
    visual_style: dict[str, Any] | None, kind: str | None
) -> dict[str, Any]:
    """The per-kind style overrides for ``kind`` from ``:visual-style :kinds``."""
    kinds = (visual_style or {}).get("kinds")
    if kind and isinstance(kinds, dict):
        ks = kinds.get(kind)
        if isinstance(ks, dict):
            return ks
    return {}


def assemble_style(visual_style: dict[str, Any] | None, kind: str | None = None) -> str:
    """The shared style preamble prepended to every brief.

    Built from the world ``:visual-style`` (``:prompt`` + ``:palette``). When a
    ``kind`` ("room" | "object" | "event") is given, the matching entry under
    ``:kinds`` layers in: its ``:prompt`` is appended (additive) after the base
    style. It does not vary per entity, so the manifest carries it once per kind
    rather than repeating it in every entry's brief.
    """
    style = visual_style or {}
    parts: list[str] = []
    prompt_prefix = style.get("prompt")
    if prompt_prefix:
        parts.append(str(prompt_prefix))
    # Per-kind prompt is additive: the base style still applies, plus framing
    # specific to rooms (wide stages) or objects (isolated subjects).
    kind_prompt = _kind_style(style, kind).get("prompt")
    if kind_prompt:
        parts.append(str(kind_prompt))
    palette = style.get("palette")
    if palette:
        parts.append(f"Palette: {palette}.")
    # If structured swatches are declared, anchor the art to the same hex values
    # that drive the UI chrome (single source -> art and chrome cannot drift).
    swatches = style.get("swatches")
    if isinstance(swatches, dict) and swatches:
        hexes = ", ".join(str(v) for v in swatches.values())
        parts.append(f"Anchor the palette to these colors: {hexes}.")
    return " ".join(parts)


def assemble_brief(
    visual_style: dict[str, Any] | None,
    brief_text: str | None,
    kind: str | None = None,
) -> str:
    """Assemble a full generation prompt: shared style preamble + entity brief.

    The style preamble (``assemble_style``, kind-aware) leads, followed by the
    entity's per-variant brief. Spatial framing and reference images are layered
    on later (filfre fill, gnusto-eaec.4). Pure; safe for static manifest building.
    """
    parts = [p for p in (assemble_style(visual_style, kind), brief_text) if p]
    return " ".join(parts)


def render_aspect(visual_style: dict[str, Any] | None, kind: str | None = None) -> str:
    """Resolve the output aspect ratio for an entity ``kind``.

    A ``:kinds`` entry's ``:aspect-ratio`` overrides the world default; absent
    that, the world ``:visual-style :aspect-ratio`` (or "1:1") is used. So rooms
    can breathe (e.g. "2:1" establishing stages) while objects stay square.
    """
    style = visual_style or {}
    kind_aspect = _kind_style(style, kind).get("aspect-ratio")
    if kind_aspect:
        return str(kind_aspect)
    return str(style.get("aspect-ratio", "1:1"))


def has_render_spec(entity: Any) -> bool:
    """Check if an entity has a :render selector (string or fn)."""
    return getattr(entity, "render", None) is not None


def get_render_spec(entity: Any) -> SExpr | None:
    """Get the :render selector from an entity, or None if not present."""
    return getattr(entity, "render", None)


# =============================================================================
# Static analysis of :render selectors (the "explosion guard")
#
# These functions interpret a :render selector *abstractly* — without running
# it — to recover (a) the finite set of variant tokens it can return (its
# codomain) and (b) the set of state paths it reads. Together with the
# declarative variant set (the :rdesc keys), this lets us enumerate the exact
# image keyset for pre-generation and statically guarantee the scene-variant
# cross-product stays bounded.
# =============================================================================


def _selector_body(spec: SExpr | None) -> SExpr | None:
    """The body of a ``(fn () body)`` :render selector, or None if not a fn."""
    if isinstance(spec, SList) and len(spec) >= 3:
        first = spec[0]
        if isinstance(first, Symbol) and first.name == "fn":
            return spec[2]
    return None


def _owner_of(ref: SExpr) -> str | None:
    """Resolve the owning entity of a read target.

    ``self`` / ``?self`` -> "self"; ``@name`` -> "@name"; anything else -> None
    (a non-entity expression, e.g. a computed value, which we can't attribute).
    """
    if isinstance(ref, Symbol):
        if ref.name in ("self", "?self"):
            return "self"
        if ref.name.startswith("@"):
            return ref.name
    return None


@dataclass(frozen=True)
class RenderRead:
    """A state path read by a :render selector.

    - ``kind``  : "prop" | "loc" | "queue"
    - ``owner`` : "self", an "@entity" name, or None (unattributable); for
                  queues this is None (queues are not owned by an entity).
    - ``detail``: property name for "prop", event name for "queue", else None.
    """

    kind: Literal["prop", "loc", "queue"]
    owner: str | None
    detail: str | None = None


def render_reads(spec: SExpr | None) -> set[RenderRead]:
    """Collect the state paths a :render selector reads (static walk).

    Returns an empty set for literal/absent selectors. Recognizes the read
    forms a pure selector can use: ``(:prop X ...)``, ``(queued? E)``,
    ``(held? X)``, ``(loc X)``, ``(in-room? X ...)``.
    """
    body = _selector_body(spec)
    if body is None:
        return set()
    reads: set[RenderRead] = set()

    def walk(expr: SExpr) -> None:
        if not isinstance(expr, SList) or len(expr) == 0:
            return
        head = expr[0]
        if isinstance(head, Keyword) and len(expr) >= 2:
            # (:prop X ...) - property read
            reads.add(RenderRead("prop", _owner_of(expr[1]), head.name))
            for item in expr.items[2:]:
                walk(item)
            return
        if isinstance(head, Symbol):
            name = head.name
            if name in ("loc", "held?", "in-room?") and len(expr) >= 2:
                reads.add(RenderRead("loc", _owner_of(expr[1])))
                for item in expr.items[2:]:
                    walk(item)
                return
            if name == "queued?" and len(expr) >= 2:
                ev = expr[1]
                ev_name = ev.name if isinstance(ev, Symbol) else None
                reads.add(RenderRead("queue", None, ev_name))
                return
        for item in expr.items:
            walk(item)

    walk(body)
    return reads


def render_codomain(spec: SExpr | None) -> set[str] | None:
    """The finite set of variant **tag names** a selector can return, or None.

    Statically evaluates the *shape* of the selector body (``if`` / ``cond`` /
    ``when`` / ``do``), collecting the names of the ``Keyword`` variant tags it
    can yield. Branches that yield nil or a verbatim string key contribute no
    tag. Returns ``None`` when any reachable branch can produce a value we cannot
    prove (i.e. the tag codomain is not statically bounded).
    """
    body = _selector_body(spec)
    if body is None:
        # A literal string/keyword selector is its own key, handled elsewhere.
        return None
    tokens, exact = _codomain_of(body)
    return tokens if exact else None


def _codomain_of(expr: SExpr) -> tuple[set[str], bool]:
    """(variant tag names, exact?) for an expression's return value.

    Only ``Keyword`` leaves count as variant tags. ``exact`` is False if some
    branch can return an unprovable value. nil, booleans, and verbatim string
    keys contribute no tag but keep ``exact`` True.
    """
    if isinstance(expr, Keyword):
        return {expr.name}, True
    if expr is None or isinstance(expr, str):
        # nil or a verbatim string key -> not a variant tag.
        return set(), True
    if isinstance(expr, bool):
        # true/false branch markers (e.g. cond's `true`) carry no tag.
        return set(), True
    if not isinstance(expr, SList) or len(expr) == 0:
        return set(), False

    head = expr[0]
    if isinstance(head, Symbol):
        name = head.name
        if name == "if":
            # (if test then [else])
            branches = expr.items[2:]
            if not branches:
                return set(), False
            tokens: set[str] = set()
            exact = True
            for br in branches:
                t, e = _codomain_of(br)
                tokens |= t
                exact = exact and e
            if len(branches) == 1:
                # No else -> may fall through to nil (base key); still exact.
                pass
            return tokens, exact
        if name in ("when", "unless"):
            # (when test body...) -> last body expr, or nil if test fails.
            if len(expr) >= 3:
                return _codomain_of(expr.items[-1])
            return set(), True
        if name == "cond":
            # (cond (test body...) ...) -> union of each clause's last expr.
            tokens = set()
            exact = True
            for clause in expr.items[1:]:
                if isinstance(clause, SList) and len(clause) >= 2:
                    t, e = _codomain_of(clause.items[-1])
                    tokens |= t
                    exact = exact and e
                else:
                    exact = False
            return tokens, exact
        if name in ("do", "begin", "progn"):
            if len(expr) >= 2:
                return _codomain_of(expr.items[-1])
            return set(), True
    # Any other call form: value is not a provable literal token.
    return set(), False


# =============================================================================
# Render manifest + explosion-guard lint
# =============================================================================


@dataclass(frozen=True)
class RenderManifestEntry:
    """One pre-generatable image: an asset key plus its per-entity brief.

    ``brief`` is the entity's own brief text only (its ``:rdesc``); the shared
    world style preamble is carried once on the manifest, not repeated here. The
    full generation prompt is ``assemble_brief(visual_style, brief)``.
    """

    key: str  # extension-less asset key, e.g. "microwave-open"
    entity: str  # owning entity name, e.g. "@microwave"
    kind: Literal["room", "object", "event"]
    variant: str | None  # variant token, or None for single-variant entities
    brief: str | None  # per-entity brief (rdesc), without the shared style


@dataclass
class RenderLintError:
    """A static render-config violation."""

    entity: str
    message: str
    severity: Literal["error", "warning"] = "error"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.entity}: {self.message}"


def _iter_renderable(world: Any):
    """Yield (entity_name, entity, kind) for every renderable room/object/event.

    Events are renderable when they declare a beat ``:rdesc`` catalog; their
    asset keys are ``<event>-<tag>``, exactly like an entity's variant keys.
    """
    for name, room in getattr(world, "rooms", {}).items():
        if is_renderable(room):
            yield name, room, "room"
    for name, obj in getattr(world, "objects", {}).items():
        if is_renderable(obj):
            yield name, obj, "object"
    for name, event in getattr(world, "events", {}).items():
        if is_renderable(event):
            yield name, event, "event"


def event_render_tags(body: SExpr | None) -> tuple[set[str], bool]:
    """Collect the beat tags emitted by ``(success/blocked :render :tag ...)``.

    Walks an event ``:on-turn`` body (through quotes/conditionals) and gathers
    the ``Keyword`` tag names selected at emission sites. Returns
    ``(tag_names, exact)``; ``exact`` is False if any ``:render`` value is not a
    literal keyword (i.e. the emitted tag set is not statically bounded).
    """
    tags: set[str] = set()
    exact = True

    def walk(expr: Any) -> None:
        nonlocal exact
        if not isinstance(expr, SList) or len(expr) == 0:
            return
        head = expr[0]
        if isinstance(head, Symbol) and head.name in ("success", "blocked", "victory"):
            items = expr.items
            i = 1
            while i < len(items):
                kw = items[i]
                if isinstance(kw, Keyword) and kw.name == "render":
                    val = items[i + 1] if i + 1 < len(items) else None
                    if isinstance(val, Keyword):
                        tags.add(val.name)
                    else:
                        exact = False
                    i += 2
                else:
                    i += 1
        for item in expr.items:
            walk(item)

    walk(body)
    return tags, exact


def build_render_manifest(world: Any) -> list[RenderManifestEntry]:
    """Enumerate every pre-generatable image keyed by the world's render specs.

    For each renderable entity, emit one entry per asset key in its declarative
    keyset (``render_keyset``). Each entry carries only its per-variant
    ``:rdesc`` brief; the shared world style preamble is not folded in here (use
    ``assemble_style(world.visual_style)`` once, or ``assemble_brief`` for the
    full per-key prompt). Pure and deterministic; sorted by key for stable
    output.
    """
    entries: list[RenderManifestEntry] = []
    seen: set[str] = set()
    for name, entity, kind in _iter_renderable(world):
        variants = render_variants(entity)
        # Map each asset key back to the variant token that produced it.
        if variants:
            base = asset_base(name)
            key_variant = {f"{base}-{v}": v for v in variants}
        else:
            key_variant = {k: None for k in render_keyset(name, entity)}
        for key in sorted(render_keyset(name, entity)):
            if key in seen:
                # Shared/aliased key (e.g. a door reusing its room art) — the
                # owning entity already contributed the manifest entry.
                continue
            seen.add(key)
            variant = key_variant.get(key)
            brief = brief_for_variant(entity, variant)
            entries.append(
                RenderManifestEntry(
                    key=key, entity=name, kind=kind, variant=variant, brief=brief
                )
            )
    entries.sort(key=lambda e: e.key)
    return entries


def lint_render(world: Any) -> list[RenderLintError]:
    """Statically check render specs for the explosion-guard invariants.

    Entity rules:

    1. **Codomain ⊆ declared variants.** Every variant token a ``(fn)`` selector
       can return must have a matching ``:rdesc`` brief, so every selected key
       is generatable (and the keyset is exactly enumerable).
    2. **Locality (the explosion guard).** A *room* render may not read any
       foreign object/room state — baking object state into a room image is
       what makes the scene-variant cross-product explode. An *object* render
       may read only its own state. Reads of ``self`` (own properties) and
       queues are always allowed.

    Event rule:

    3. **Emitted beats ⊆ declared catalog.** Every ``(success/blocked :render
       :tag)`` an event emits must have a matching ``:rdesc`` catalog entry
       (else there is no brief / key). Catalog entries never emitted are flagged
       as unused (warning). Events have no state-reading selector, so the
       locality rule does not apply.
    """
    errors: list[RenderLintError] = []
    errors.extend(_lint_events(world))
    for name, entity, kind in _iter_renderable(world):
        if kind == "event":
            continue  # handled by _lint_events
        spec = getattr(entity, "render", None)
        if _selector_body(spec) is None:
            continue  # literal / absent selector: nothing to interpret

        # Rule 1: codomain ⊆ declared variants.
        variants = render_variants(entity)
        codomain = render_codomain(spec)
        if variants is not None and codomain is not None:
            extra = codomain - set(variants)
            if extra:
                errors.append(
                    RenderLintError(
                        name,
                        f":render can return {sorted(extra)} which have no "
                        f":rdesc variant (declared: {sorted(variants)}).",
                    )
                )
        elif variants is not None and codomain is None:
            errors.append(
                RenderLintError(
                    name,
                    ":render selector is not statically bounded; its returned "
                    "variant tokens cannot be enumerated for pre-generation.",
                    severity="warning",
                )
            )

        # Rule 2: locality.
        for read in render_reads(spec):
            if read.kind == "queue":
                continue  # queues are global/temporal axes, always allowed
            owner = read.owner
            if owner in (None, "self", name):
                continue  # own state is always fine
            # A foreign entity read.
            what = (
                f"(:{read.detail} {owner})"
                if read.kind == "prop"
                else f"{read.kind} of {owner}"
            )
            if kind == "room":
                errors.append(
                    RenderLintError(
                        name,
                        f"room :render reads foreign object state {what}; "
                        f"object state must live in floated subject panels, not "
                        f"baked into the room image.",
                    )
                )
            else:
                errors.append(
                    RenderLintError(
                        name,
                        f"object :render reads foreign state {what}; an object's "
                        f"variant must depend only on its own state.",
                    )
                )
    return errors


def _lint_events(world: Any) -> list[RenderLintError]:
    """Lint event beat rendering (rule 3): emitted tags ⊆ declared catalog."""
    errors: list[RenderLintError] = []
    for name, event in getattr(world, "events", {}).items():
        catalog = render_variants(event)  # the :rdesc map keys, or None
        body = getattr(event, "body", None)
        tags, exact = event_render_tags(body)
        # Only events that declare a catalog or emit beats are of interest.
        if catalog is None and not tags:
            continue
        declared = set(catalog) if catalog else set()

        extra = tags - declared
        if extra:
            errors.append(
                RenderLintError(
                    name,
                    f"event emits beats {sorted(extra)} with no :rdesc catalog "
                    f"entry (declared: {sorted(declared)}).",
                )
            )
        if not exact:
            errors.append(
                RenderLintError(
                    name,
                    "event emits a :render beat tag that is not a literal keyword; "
                    "the beat set cannot be enumerated for pre-generation.",
                    severity="warning",
                )
            )
        unused = declared - tags
        if unused:
            errors.append(
                RenderLintError(
                    name,
                    f"event declares :rdesc beats {sorted(unused)} that are never "
                    f"emitted via (success/blocked :render ...).",
                    severity="warning",
                )
            )
    return errors
