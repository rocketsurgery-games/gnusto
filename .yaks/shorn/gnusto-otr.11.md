---
id: gnusto-otr.11
title: 'frotz map: room-topology dump + dangling-reference lint'
type: task
priority: 2
created: '2026-07-12T19:12:32Z'
updated: '2026-07-12T19:18:06Z'
labels:
- tooling
---

---
▸ 2026-07-12T19:18:06Z
Done. Built 'frotz map' + grue.mapgraph (build_map/format_text/to_dot). Walks the static room graph: reports a FRONTIER (exits :to undefined rooms + objects at undefined :location — the 'what's left to wire' ledger; :location nil never flagged) and TYPO-PRONE dangling :via/:visible refs. Flags: --rooms (per-room exits, marks dark), --dot [FILE] (Graphviz; frontier dashed/gray, dark rooms shaded), --strict-refs (CI gate on via/visible), --strict (any dangling). 6 pytest. Docs: docs/frotz.md, AGENTS.md, cli docstring. Validated: found latent LH issues (-> gnusto-otr.11.1); Zork frontier = 10 rooms + @egg->@nest.
