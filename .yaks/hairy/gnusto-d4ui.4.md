---
id: gnusto-d4ui.4
title: Overlay panels — /state, /help, save/load, object detail
type: task
priority: 3
created: '2026-02-24T12:00:00Z'
updated: '2026-02-24T12:00:00Z'
---

Commands like /state, /help, and save/load currently dump text into the scrolling
stream. Move them to overlay panels that don't pollute the narrative.

## Scope

1. **Overlay infrastructure** — Modal or slide-in panel component. Dismissable via
   close button, escape, or clicking outside. Supports arbitrary content. Could slide
   from left, right, or center depending on context.

2. **/state overlay** — Full game state view (what the agent sees). Structured display
   of room, objects, inventory, known entities, behaviors. Much richer than the current
   text dump.

3. **/help overlay** — Command reference, gameplay tips. Static content, nicely formatted.

4. **Save/load overlay** — Save slots with timestamps, descriptions. Load confirmation.

5. **Object detail overlay** — When a player wants to examine an entity in depth (from
   sidebar or narrative click), show a larger view with full image, description, available
   behaviors, and history of interactions. This is the "inspect" view.

6. **Settings overlay** — Debug mode toggle, model selection, font size, etc.
