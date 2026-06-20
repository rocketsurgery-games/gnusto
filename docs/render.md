# Rendering & Visual Style

How Gnusto games get their illustrations and visual identity. This is the design
note for the **static illustration pipeline** (epic `gnusto-eaec`) and the
**graphic-novel panel stream** UI (epic `gnusto-4ac5`).

> Status: design + early implementation. The dynamic, runtime-composition system
> described in earlier work was retired (see History below). This document
> describes where we are going, and flags what is not built yet.

## Core stance

The image model only ever renders **single subjects** or **empty / global-state
stages**. All multi-element composition happens in the **UI layout (DOM/CSS)**,
never in the image model.

This is the lesson from the retired dynamic system: reference-conditioned
composition drifts badly past 1–2 references, and "compute the one correct image
for the current room state" explodes combinatorially. By keeping every generated
image to a single subject (or an empty stage), generation stays reliable even on
modest models, and the *comic layout* does the composing — exactly as a graphic
novel cuts between an establishing panel and inset panels rather than redrawing
the whole room every beat.

## Stage-level vs. subject-level state

The axis that matters is **not** movable-vs-fixed, but whether a state change
affects the *whole panel* or just *one subject*:

| Kind | Examples | How it renders |
|------|----------|----------------|
| **Stage-level** | lights on/off, flooded, power cut, room destroyed | Bake into **scene variants**. The room's `:render` keys on a small, *declared* set of room-global axes. |
| **Subject-level** | microwave open/closed/running, fridge open/closed, item held/dropped | A separate **single-subject image**, floated into the narrative as a panel. **Never** baked into the room. |

A fixed object like the kitchen microwave is still rendered as a single-subject
panel — being fixed only means its brief may be **contextual** (drawn in-situ,
since it never travels). Movable objects get **neutral backgrounds** and double
as inventory thumbnails.

The establishing shot therefore shows a *default* depiction that does not track
live subject state; live state lives in the floated panels and the text. That is
an accepted, comic-consistent tradeoff. If a designer ever needs an object's
in-scene depiction to matter, they **promote that axis to a declared room-global
state** and accept the bounded scene-variant set for that one room.

## The explosion guard (lint)

What keeps the scene-variant cross-product from blowing up is a **static lint**,
not discipline-by-hope. Via abstract interpretation over render specs:

- a **room** render may read only its **declared room-global axes**;
- an **object** render may read only **its own** state.

A room render that reads e.g. `(:open @microwave)` is a lint error. The finite
set of asset keys a render spec can return (its codomain), optionally intersected
with frotz reachability, **is** the set of images to pre-generate.

The lint and the keyset enumeration both run via `frotz render`:

```bash
frotz render games/lurkinghorror            # coverage + lint
frotz render games/lurkinghorror --briefs   # also print each assembled brief
frotz render games/lurkinghorror --json     # manifest + lint as JSON (artist handoff)
frotz render games/lurkinghorror --strict   # also fail on missing / orphan assets
```

It lists every render key, marks which resolve on disk (`ok`/`MISS`), flags
orphan image files with no manifest key, and reports any lint violations
(non-zero exit on error). Implemented in `grue.render`
(`build_render_manifest`, `lint_render`, `render_reads`, `render_codomain`).

## Pipeline

```
Grue :render specs + :rdesc briefs + world :visual-style
      │
      ▼   frotz / abstract interpretation
enumerate the finite reachable render-config set
      │
      ▼
render manifest  { asset-key, brief, refs }
      │
      ▼   filfre fill
frontier image model     OR     printable artist briefs
      │                                │
      └──────────────┬─────────────────┘
                     ▼
        pre-generated keyed assets
                     │
                     ▼   runtime resolves :render → key
        web UI composes layers (establishing stage + floated subjects)
```

The same manifest drives either a frontier image model **or** a human artist —
both fill the identical keyset.

## The variant model (`:render` / `:rdesc` / `:visual-style`)

An entity's art is keyed by a small set of **variants**, and filenames are
*derived* (`<base>-<tag>.jpg`) — authors never hand-maintain filenames.

A variant **tag is a keyword** (`:open`), distinct from a string. A *string* in
`:render` means a verbatim asset key (the escape hatch) — keyword/string is the
type-directed contract.

- **`:render`** is the **variant selector**: a pure `(fn () ...)` returning a
  variant tag keyword (e.g. `:open`). Omit it for single-variant entities
  (key = `<base>`). Returning (or supplying as a literal) a **string** instead
  means "use this verbatim key" (e.g. a door reusing its room's image).
- **`:rdesc`** declares the **brief per variant** — a `(:open "..." :closed "...")`
  map, or a single brief string. The map keys *are* the variant set, so the
  keyset is declarative (no need to run the selector to enumerate it). Falls
  back to `:description` when absent.
- **world `:visual-style`** — a keyword-map (`:prompt`, `:palette`,
  `:swatches`, `:aspect-ratio`) prepended to every brief for a consistent look.
  `:swatches` declares the palette as structured `:token "#hex"` pairs that drive
  the web chrome (`--game-*` CSS vars). Swatches are *not* injected into briefs
  (raw hex lists make image models draw a colour-swatch chart); the art's
  palette comes from the prose `:palette`. `:kinds` specializes the style
  per entity kind: a kind's `:prompt` is appended (additive) and its
  `:aspect-ratio` overrides the default — so rooms render wide (e.g. `2:1`
  establishing stages) while objects stay square subjects on a flat field.
  `assemble_style`/`assemble_brief`/`render_aspect` take the entity `kind`; the
  manifest entry's `kind` selects the right specialization.

```scheme
(object @microwave
  :render (fn () (cond ((:open self)                :open)
                       ((queued? microwave-running) :running)
                       (true                        :closed)))
  :rdesc (:open    "A 1980s microwave, door open, interior visible, above a counter."
          :running "A 1980s microwave running, interior light on, above a counter."
          :closed  "A 1980s microwave, door closed, above a counter."))
; keys: microwave-open.jpg / microwave-running.jpg / microwave-closed.jpg
```

The set of keys an entity can resolve to, intersected with reachable state, is
exactly what gets generated. Each manifest entry is a `{key, entity, kind,
variant, brief}` record where `brief` is the entity's own `:rdesc` text. The
world `:visual-style` preamble is *not* repeated per entry — it is carried once
for the whole manifest (`assemble_style`), and the full per-key generation prompt
is `assemble_brief(visual-style, brief)` (style preamble + entity brief).

### Beats (events): a third render source

State imagery answers "what does X look like *now*?". A scripted multi-turn
sequence (a cutscene like the alchemy ritual) instead needs **beat imagery**: a
series of transient panels. Events render these without a state-reading selector
— the firing control-flow arm *is* the selector. An event declares a `:rdesc`
**catalog** (`(:tag "brief" ...)`), and each `(success/blocked :render :tag ...)`
selects a beat; keys are `<event>-<tag>` (`kind: "event"`). Beats are a 1-D
sequence, so they can't explode; the lint only checks that emitted tags ⊆ the
declared catalog. They flow through the same manifest / `filfre fill` pipeline.
Unlike establishing shots, a beat is a one-off narrative panel and may depict the
full moment (figures, mist, etc.). The runtime carries the selected tag in the
result context; *displaying* beat panels is the panel-stream UI's job (Epic B).

Presentation **theme** (fonts, colors, panel chrome, UI imagery) lives in
per-game CSS (`theme.css` / `game.json`), *not* in Grue — push content/briefs into
Grue, keep CSS in CSS (`gnusto-eaec.6`).

## On disk

All keyed art lives **flat** in `games/<game>/assets/`. There is no `refs/` vs
`renders/` split anymore — there is just the one keyed asset set.

Keys are **extension-less**; the runtime resolver finds the file by trying
supported formats in order (`.jpg`, `.jpeg`, `.png`, `.webp`). We store art as
**JPG** — full-color painted scenes compress far better as JPG than PNG, and we
do not rely on alpha (image models don't reliably emit it, and composition is
done by the UI layer, not by stacking transparent cutouts).

```
games/lurkinghorror/assets/
  terminal-room.jpg          # @terminal-room  (single variant)
  microwave-open.jpg         # @microwave      (variant "open")
  microwave-closed.jpg       #                 (variant "closed")
  microwave-running.jpg      #                 (variant "running")
  cs-elevator-room.jpg       # @cs-elevator-room — also reused by @elevator-door
  ...
```

Superseded / unused source art is kept out of the asset path entirely under
[`experiments/old-art/`](../experiments/old-art/) so there's no confusion.

## Visual style: Lurking Horror

The aesthetic is full-color **graphic-novel horror** — dark, moody, comic ink
plus painted shading, desaturated dark-blue palette. It is declared in the game's
world `:visual-style` and carried by the art in `games/lurkinghorror/assets/`,
replacing the earlier black-and-white pencil sketches (`gnusto-eaec.5`).

## History (retired dynamic system)

An earlier system composed scenes dynamically at runtime: hierarchical
composition (atomic refs → composites → scenes), recursive `:render` specs
(`ObjectRef`, `:contents`, `:through`, `:anchor`), content-addressed two-tier
caching, and integration into the TUI/web loops. It was retired because
multi-reference composition was unreliable and state-dependent caching exploded.

That code is archived for reference (not maintained, imports may be stale) in
[`experiments/dynamic-composition/`](../experiments/dynamic-composition/), along
with `README.md` documenting what worked and what didn't. The overlay/stepwise
follow-up experiments live in [`experiments/composition/`](../experiments/composition/)
and the graphic-novel layout prototype in [`experiments/layout/`](../experiments/layout/).

## See also

- [`docs/filfre.md`](filfre.md) — the standalone image-generation CLI.
- [`docs/frotz.md`](frotz.md) — the static analysis engine that enumerates render configs.
- [`docs/grue.md`](grue.md) — `:render` and entity-field reference.
