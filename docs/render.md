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

> Not built yet — see `gnusto-eaec.3`.

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
*derived* (`<base>-<token>.png`) — authors never hand-maintain filenames.

- **`:render`** is the **variant selector**: a pure `(fn () ...)` returning a
  variant token (e.g. `"open"`). Omit it for single-variant entities
  (key = `<base>.png`). A literal string is an escape hatch meaning "use this
  exact key" (e.g. a door reusing its room's image).
- **`:rdesc`** declares the **brief per variant** — a `(:open "..." :closed "...")`
  map, or a single brief string. The map keys *are* the variant set, so the
  keyset is declarative (no need to run the selector to enumerate it). Falls
  back to `:description` when absent.
- **world `:visual-style`** — a keyword-map (`:prompt`, `:palette`,
  `:aspect-ratio`) prepended to every brief for a consistent look.

```scheme
(object @microwave
  :render (fn () (cond ((:open self)               "open")
                       ((queued? microwave-running) "running")
                       (true                        "closed")))
  :rdesc (:open    "A 1980s microwave, door open, interior visible, above a counter."
          :running "A 1980s microwave running, interior light on, above a counter."
          :closed  "A 1980s microwave, door closed, above a counter."))
; keys: microwave-open.png / microwave-running.png / microwave-closed.png
```

The set of keys an entity can resolve to, intersected with reachable state, is
exactly what gets generated. Each `{key, assemble_brief(visual-style, rdesc)}`
pair becomes a manifest entry.

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
