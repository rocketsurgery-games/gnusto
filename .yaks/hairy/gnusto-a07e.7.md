---
id: gnusto-a07e.7
title: Event/beat refs to frozen plates (character + room grounding)
type: feature
priority: 2
created: '2026-06-20T21:27:40Z'
updated: '2026-06-21T20:58:32Z'
depends_on:
- gnusto-819a
- gnusto-a07e.1
- gnusto-a07e.2
---

Event rendering creates inconsistent scenes, without some grounding in existing room and object images / prompts.

---
▸ 2026-06-21T20:30:36Z
Scoped by gnusto-819a probes: this is the recurring-character / beats application of the consistency model (epic gnusto-a07e). Approach: each event beat :refs a FROZEN character/anchor plate (M2) -> same man across all 8 ritual beats with correct per-beat framing; beats never ref each other, so the beat graph is trivially acyclic. Builds on a07e.1 (ref edges + lint) and a07e.2 (filfre ordered gen w/ ref mode). Edit-chain (M3) is an opt-in alternative only for locked-camera cutscenes.

---
▸ 2026-06-21T20:58:32Z
Reparented into the herd as the EVENTS application (parallel to .3 objects, .4 rooms). Open wrinkle beyond the gnusto-819a probe: probe validated 1-ref beats (character plate only); eadc's original scope also wants beats grounded in their containing ROOM/object image -> potentially 2 refs/beat (character plate + room plate). Old dynamic-composition post-mortem says 1-2 refs is safe / 3+ breaks, so likely fine but UNTESTED here -> probe a 2-ref beat before committing the multi-ground path.
