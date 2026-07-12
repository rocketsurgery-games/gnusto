---
id: gnusto-otr.11.1
title: Triage LH dangling refs found by frotz map (:visible @outside-door/@outlet;
  23 objects at undefined @global)
type: task
priority: 2
created: '2026-07-12T19:15:18Z'
updated: '2026-07-12T19:15:18Z'
labels:
- bug
---

---
▸ 2026-07-12T19:15:18Z
frotz map (gnusto-otr.11) surfaced latent LH issues that pass tests: (1) 6 dangling :visible refs -> @outlet (alchemy-dept/lab) and @outside-door (brown-building/courtyard/great-court/temporary-lab) are never defined as objects, so they silently no-op in room listings. (2) 23 objects declare :location @global, a sentinel that isn't a defined room/object (LH's LOCAL-GLOBALS convention) — should be :location nil or a defined @global entity. Triage: fix the :visible typos/removals; decide whether @global should be a real entity or nil. Not blocking Zork.
