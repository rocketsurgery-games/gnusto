---
id: gnusto-4ac5.2
title: 'Comic-idiom live state: summonable satchel, map, locator'
type: feature
priority: 2
created: '2026-06-16T02:17:45Z'
updated: '2026-06-16T02:17:45Z'
depends_on:
- gnusto-8c77
---

Render the LIVE ground-truth side (what's here / where am I / affordances) in comic idiom, mostly summonable rather than pinned. Lean chrome-less, with small floating affordances when appropriate.

- Inventory -> a summonable 'satchel' comic SPREAD: a page of object panels reusing the movable-object single-subject assets (closes the thumbnail question: yes, but as a page, not a pinned list).
- Map / 'where am I' -> a summonable inked MAP PAGE (restyle auto-map gnusto-8c77 as a drawn map, not a node graph) + an optional minimal floating locator.
- Visible objects / characters present -> light comic-idiom cues, not a traditional tray/strip; keep summon affordances small and unobtrusive.
- Keep only what must be persistent (minimal locator + the command input); everything else is summoned.

Depends on gnusto-4ac5.1 (stream) and gnusto-8c77 (auto-map backbone).
