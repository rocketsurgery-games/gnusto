---
id: gnusto-d4ui
title: Web UI redesign
type: task
priority: 2
created: '2026-02-24T12:00:00Z'
updated: '2026-02-25T17:39:43Z'
---

Redesign the web UI from infinite-scroll to a structured three-zone layout optimized
for interactive fiction. Move from "chat log" to "game interface."

## Design principles

- **Room-centric.** The narrative stream is scoped to the current room. Previous rooms
  live in history, not the main view.
- **Structured sidebars.** Inventory, visible objects, exits, and characters are first-class
  UI elements with images/icons, not text dumped into the stream.
- **Clickable everything.** Entity references in narrative text and sidebar items both serve
  as interaction affordances. Let players discover which works best for them.
- **Overlays, not inline.** Commands like /state, /help, save/load use modal/slide-in
  panels instead of polluting the narrative.
- **Gamelike, not app-like.** Retain full control over layout, decorations, transitions.
  The UI should feel like a modern IF experience, not a desktop application.
- **Transition-ready.** Even before we have fancy room transitions, the architecture should
  support them (room changes as discrete events, not just more text appended).

## Desktop layout

```
┌──────────────────────────────────────────────────┐
│  ROOM HEADER  (name, image, short desc, exits)   │
├────────────┬─────────────────────┬───────────────┤
│            │                     │               │
│  LEFT      │   NARRATIVE STREAM  │   RIGHT       │
│  SIDEBAR   │   (room-scoped,     │   SIDEBAR     │
│            │    scrolling)        │               │
│  - Map     │                     │  - Inventory  │
│  - Notes   │                     │  - Objects    │
│  - History │                     │  - Characters │
│            │                     │               │
├────────────┴─────────────────────┴───────────────┤
│  INPUT BAR  (with autocomplete / quick actions)   │
└──────────────────────────────────────────────────┘
```

## Mobile / narrow layout

Single-panel with three states (left sidebar, narrative, right sidebar). The narrative
is the default view. Small, partially-off-viewport affordances (icons, edge tabs, or
peek strips) give quick access to sidebars without a full switch.

## Framework

Migrate from vanilla TypeScript to a lightweight reactive framework (Svelte or Solid)
for component structure, state management, and transitions. Keep full CSS control —
no component library. The content block system (RoomEnter, Narrate, Speak, etc.) and
WebSocket protocol remain unchanged; this is purely a frontend rewrite.

## Subsumes

- gnusto-04d2 (Restructure UI to remove infinite scrolling)
- gnusto-f9d7 (Expose object and room images)
