---
id: gnusto-d4ui.1
title: Three-zone layout scaffold and framework migration
type: task
priority: 2
created: '2026-02-24T12:00:00Z'
updated: '2026-02-24T12:00:00Z'
---

Replace the single-column vanilla TS frontend with a three-zone layout in a lightweight
reactive framework. This is the foundation for everything else.

Subsumes gnusto-04d2 (restructure UI to remove infinite scrolling).

## Scope

1. **Choose and set up framework** — Svelte or Solid. Configure Vite build, replace
   the current vanilla TS entry point. Preserve the existing WebSocket protocol and
   content block types (no backend changes).

2. **Three-zone desktop layout** — Room header (fixed top), left sidebar (placeholder),
   narrative stream (center, scrolling), right sidebar (placeholder), input bar (fixed
   bottom). Sidebars start as empty shells to be filled in subsequent yaks.

3. **Room-scoped narrative** — When a RoomEnter block arrives, archive the previous
   room's narrative and start fresh. The stream only shows the current room's story.
   Previous content accessible via history (later yak).

4. **Responsive mobile layout** — Below breakpoint, collapse to single panel with
   swipe/tab navigation between left sidebar, narrative, and right sidebar. Include
   edge affordances (peek tabs or icons) for quick sidebar access.

5. **Migrate existing block rendering** — Port all content block renderers (Narrate,
   Speak, Think, Ambient, Focus, Reveal, Debug, SystemMessage) to framework components.
   Preserve current visual styling — this yak is about structure, not restyling.

6. **Input bar** — Same text input, but now a proper component. Prepare for future
   autocomplete (not implemented here).

## Non-goals

- Sidebar content (inventory, objects, map) — those are separate yaks
- Overlay panels
- Room transition animations (but the architecture should make them easy to add)
- Restyling block content
