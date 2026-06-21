---
id: gnusto-819a
title: Consistency-reference probes (Nano Banana Pro)
type: task
priority: 2
created: '2026-06-21T14:57:12Z'
updated: '2026-06-21T20:28:07Z'
labels:
- render
- image
---

Experimental probes to find which Gemini image-model mechanisms actually hold visual identity/structure consistent across related images, before modeling it in Grue/filfre.

Three consistency cases from the game:
1. Multiple states of one object (microwave closed/open/running).
2. Cross-visible adjacent rooms (cs-2nd hallway / kitchen / elevator / stairs) that must agree at shared boundaries.
3. Repeated character across beats (professor through the alchemy ritual).

Candidate mechanisms to probe (style held fixed via world :visual-style):
- M1 prompt-only (control).
- M2 single frozen reference image -> fresh generation (redraw THIS, now doing X).
- M3 in-place edit of the prior image (Nano Banana is an editing model; closed->open->running as edits on one canvas).
- M4 single-call model-sheet / grid, then PIL-slice (max identity, one call, lower res).
- M5 master establishing plate -> per-room crop/outpaint (breaks the kitchen<->hallway visibility cycle: master is the pre-merge root, rooms are post-merge crops).

Deliverable: experiments/consistency/ harness that runs each case x mechanism, lays out comparison contact-sheets, and prototypes the dependency DAG (frozen roots -> dependents, no cycles). Dry-run prints DAG + prompts with no API spend. Feed findings into gnusto-eadc and the render docs.

---
▸ 2026-06-21T15:14:58Z
Built experiments/consistency/ harness (probe.py + README). Mechanisms M1 prompt / M2 frozen-ref / M3 in-place edit / M4 model-sheet grid / M5 master-plate crop+reframe, run as a topo-sorted DAG (frozen roots -> dependents, cycle-checked). Real briefs lifted from the game. --dry-run prints DAG+prompts+call counts with no spend; --sheet builds per-case contact sheets.

SDK gotcha fixed: a fresh google-genai Client() per call hits 'client has been closed' (httpx transport); cache one module-level client.

Ran case 1 (microwave, 8 calls, Nano Banana Pro ~1K). Findings: M3 edit = excellent identity (same unit, same framing, only door/glow changes); M2 ref = very good (small pose drift); M1 prompt-only = poor (each state a different microwave); M4 grid = failed as built (object framing made one round blob, equal-column slicing invalid -> deprioritized). Closed base reads ambiguously (looks half-open) due to black-isolated object framing -> brief-wording fix ('opaque closed door, no interior visible').

Model implication: object state variants want a 'base + deltas' :rdesc model (one frozen root, others derived as edits/refs), not N independent briefs. rooms (6 calls) + professor (25 calls) cases built but not yet run pending spend go-ahead.

---
▸ 2026-06-21T20:12:03Z
Ran rooms (6) + professor (24) cases. Full findings in experiments/consistency/README.md.

CASE 2 rooms: master-plate DAG works. cluster-master root baked in cross-visibility (elevators+stairs+kitchen-through-doorway). kitchen-ref inherited master palette+layout (microwave/fridge arrangement) vs kitchen-prompt = different warmer kitchen. hallway-crop = exact free seam but subset-only. => crop where room is a literal sub-view, ref where it needs its own framing.

CASE 3 professor: most decisive. M2 ref off frozen prof-plate = default: same gaunt white-coated man across all 8 beats WITH correct per-beat framing (stage8 trapdoor view). M3 edit-chain = excellent locked-camera continuity (identity+pentagram+geometry survive 5+ edits deep) BUT locks framing (stage8 stayed wide) and accumulates finish/detail off the rough style. M1 prompt-only FAILS: drifts face+costume (younger man, dark jacket not white coat), even painted 'MOCKUP - PANEL 3' caption into art.

SYNTHESIS / recommended model: requirement-shape picks mechanism. Object states -> M3 edit (base+deltas rdesc). Recurring character -> M2 ref off frozen plate (beats ref plate, never each other -> acyclic). Locked-camera cutscene -> M3 chain (opt-in). Cross-visible rooms -> M5 crop / M2 ref off a locale master plate. Common thread: introduce a frozen ROOT and have dependents ref it, never each other.

CYCLES IN THE WILD: room visibility graph is cyclic/symmetric, won't topo-sort. Derive acyclic GEN graph via (1) locale master plates, (2) per-portal seam assets, (3) explicit author :ref edges + cycle-rejecting lint (reuse the scene-variant explosion-guard machinery). Auto via spanning tree, explicit override where needed.

FOLLOW-UPS to spin out: closed-microwave brief wording ('opaque closed door'); edit detail-creep style-reassertion/chain cap; style preamble wording 'rough mockup' gets painted as literal caption text; M4 grid deprioritized (failed).

---
▸ 2026-06-21T20:28:07Z
SHORN: experiment complete across all 3 cases. Mechanism is picked by requirement shape; common thread is a frozen ROOT that dependents reference (never each other) -> acyclic. M1 prompt-only fails on identity; M4 grid dead; M5 crop demoted to opportunistic optimization (NOT a cycle-breaker) per discussion. Findings + recommended Grue model in experiments/consistency/README.md. Next: sketch the modeling design as a yak herd (base+deltas rdesc, :ref edges + cycle lint, locale plates/portal seams, wording fixes) feeding gnusto-eadc.
