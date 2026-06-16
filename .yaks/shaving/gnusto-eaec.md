---
id: gnusto-eaec
title: Static illustration pipeline & visual style
type: task
priority: 2
created: '2026-06-16T02:15:49Z'
updated: '2026-06-16T03:31:19Z'
---

Replace the retired dynamic-composition approach with a reliable STATIC pre-generation pipeline driven by Grue's static analysis.

Core stance: the image model only ever renders SINGLE SUBJECTS or empty/global-state stages. All multi-element composition happens in the UI layout (DOM/CSS), never in the image model. This sidesteps the composition-drift and cross-product-explosion problems that killed the dynamic system (see gnusto-dk41 / gnusto-9711, src/filfre/IMPLEMENTATION-NOTES.md, experiments/composition/REPORT.md).

Key framing — STAGE-LEVEL vs SUBJECT-LEVEL state:
- Stage-level state changes the whole panel (lights on/off, flooded, power, destruction) -> bake into scene VARIANTS; the room render keys on a small set of declared global axes.
- Subject-level state changes one thing (microwave open/closed/running, item held/dropped) -> render as a separate SINGLE-SUBJECT image, floated into the narrative as a panel. Never baked into the room.

Fixed objects (microwave/fridge) still render as single-subject panels, but their briefs may be contextual (drawn in-situ, since they never travel); movable objects get neutral backgrounds and double as inventory thumbnails.

Pipeline: Grue :render specs + :rdesc briefs + world :visual-style  ->  frotz/abstract-interp enumerates the finite reachable render-config set  ->  render manifest {key, brief, refs}  ->  filfre fill (frontier model OR printable artist briefs)  ->  pre-generated keyed assets  ->  runtime resolves :render to a key with graceful fallback.

Target aesthetic: full-color 'graphic novel horror' (see games/lurkinghorror/assets/refs/*.jpg), replacing the current black-and-white pencil sketches (assets/*.png).
