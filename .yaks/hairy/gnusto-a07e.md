---
id: gnusto-a07e
title: Consistency-reference render model
type: feature
priority: 2
created: '2026-06-21T20:29:26Z'
updated: '2026-06-21T20:29:26Z'
labels:
- render
- image
---

Model image-model consistency-references in Grue/filfre, per the experiment findings in experiments/consistency/README.md (yak gnusto-819a).

Core principle proven by the probes: a related set of images stays consistent when every dependent references a single FROZEN ROOT (base image / character plate / locale plate / portal seam) rather than referencing each other. That invariant is what keeps the generation graph acyclic even though the room visibility graph is cyclic.

Mechanism per requirement shape:
- object state variants  -> M3 in-place edit off a frozen base
- recurring character    -> M2 ref off a frozen character plate
- cross-visible rooms     -> M2 ref off a locale master plate
- locked-camera cutscene  -> M3 edit-chain (opt-in)
- style only              -> existing :visual-style preamble

Children break this into the manifest/lint plumbing, the filfre generation modes, and the three applications, plus wording fixes. gnusto-eadc (event :rdescs reference room/objects) is the beats application and depends on .1/.2.
