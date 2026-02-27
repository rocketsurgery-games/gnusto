---
id: gnusto-d4ui.6
title: Auto-map
type: task
priority: 3
created: '2026-02-24T12:00:00Z'
updated: '2026-02-24T12:00:00Z'
---

A map that builds as the player explores. Lives in the left sidebar (or expands to
an overlay for detail).

## Scope

1. **Graph construction** — Track rooms visited and connections between them. Each
   RoomEnter block provides the current room ID and available exits. Build an adjacency
   graph incrementally.

2. **Compact sidebar view** — Small node graph showing the current room highlighted,
   adjacent rooms, and explored connections. Fits in the sidebar width. Current room
   is visually distinct.

3. **Expanded overlay view** — Click to expand into a full-screen overlay with the
   complete explored map. Zoom/pan for large game maps.

4. **Room annotations** — Show icons or markers on map nodes for notable things:
   unresolved puzzles, NPCs, items of interest. Driven by history data.

5. **Layout algorithm** — Non-trivial for IF maps (they're not planar, directions
   don't always compose geographically). Options: force-directed, grid-based with
   compass alignment, or manual hints from game data. Start with force-directed
   and iterate.

## Open questions

- Should the map reveal unexplored exits (doors you can see but haven't gone through)?
  Probably yes, shown differently from explored connections.
- How to handle non-standard directions (up/down, in/out, nw/se)?
- Should room names appear on the map, or only on hover?
