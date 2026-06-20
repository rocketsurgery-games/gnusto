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

---
▸ 2026-06-20T23:45:00Z
HERD STATUS — this is the ONLY un-shorn child of Epic B; everything else (.1 .3 .4 .5 .6 .7 .8 .9 .10 .11) is shorn. BLOCKED: the defining deliverable (summonable inked MAP PAGE + locator) depends on the auto-map (gnusto-8c77 -> gnusto-6ba8), a separate track not in this herd.
CARVE-OUT OPPORTUNITY (for when we revisit): the three parts split cleanly by dependency —
  (a) SATCHEL — summonable inventory comic SPREAD reusing movable-object assets. INDEPENDENT of 8c77, and now cheap: it can reuse the EntityInset 'specimen plate' from .6 (resolveEntityImage) as the per-item panel. Could be a ready child today.
  (b) MAP PAGE + floating locator — needs 8c77. Stays blocked.
  (c) light object/character presence cues — independent, small.
DEFERRED (design judgement, wants a human): (a)/(c) introduce SUMMON-AFFORDANCE UX choices (where the satchel/map buttons live, the spread layout, how unobtrusive) that the design doc flags as open, and the inventory is empty at game start so a satchel can't be visually validated without play. Held back from the unsupervised plow-through for that reason. Suggest: when revisited, carve (a)+(c) into a ready child and build the satchel on EntityInset; leave (b) blocked on 8c77.
