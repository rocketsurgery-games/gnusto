---
id: gnusto-d4ui.2
title: Right sidebar — inventory, visible objects, characters, exits
type: task
priority: 2
created: '2026-02-24T12:00:00Z'
updated: '2026-02-24T12:00:00Z'
---

Populate the right sidebar with structured, interactive game state. This is where
players see what's around them and what they're carrying.

Subsumes gnusto-f9d7 (expose object and room images).

## Scope

1. **Inventory panel** — List of held items with small icons/images (from render specs
   or asset refs). Each item is a visual card or row, not just text.

2. **Visible objects panel** — Objects in the current room. Same visual treatment as
   inventory. Distinguish interactable objects from scenery.

3. **Characters panel** — NPCs present in the room. Show portrait/avatar and name.
   Could show brief state info (mood, disposition) when available.

4. **Exits panel** — Available exits as directional indicators. Could be compass rose,
   labeled buttons, or directional arrows. Clicking an exit sends `(go direction)`.

5. **Image/icon resolution** — Use scene_context entity images when available. Fall back
   to a generic icon per entity type (object, person, container, etc.). Small thumbnails,
   not full-size images.

6. **Live updates** — Sidebar refreshes when room changes, inventory changes, or objects
   appear/disappear. Driven by the same content block stream (RoomEnter blocks contain
   all the data needed).

## Data source

RoomEnter blocks already contain: room name, description, exits, visible objects (with
descriptions), inventory (with descriptions), and the scene_context message provides
entity images. No backend changes needed.
