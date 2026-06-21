---
id: gnusto-8c77
title: Auto-map
type: task
priority: 3
created: '2026-02-24T12:00:00Z'
updated: '2026-03-01T18:01:18Z'
depends_on:
- gnusto-6ba8
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

---
▸ 2026-06-21T00:12:00Z
UI FOLLOW-UP NEEDED (from Epic B). The auto-map's data/graph is the backbone for Epic B's summonable MAP PAGE + floating locator (gnusto-4ac5.2), which is DEFERRED until this lands. When building/landing auto-map, leave a note in the PR that it needs a panel-stream UI: restyle the explored map as a drawn/inked MAP PAGE (not a node graph) summoned on demand, plus an optional minimal floating "you are here" locator. The comic-idiom map UI is tracked under gnusto-4ac5.2; this yak owns the underlying graph/layout.
