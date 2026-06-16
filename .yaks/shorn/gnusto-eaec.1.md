---
id: gnusto-eaec.1
title: Teardown consolidation & cleanup
type: task
priority: 2
created: '2026-06-16T02:16:27Z'
updated: '2026-06-16T03:33:56Z'
---

Pure-win cleanup that unblocks the rest of Epic A. No behavior change.

- Move the retired dynamic-composition code out of the live tree into experiments/: src/filfre/scene_renderer.py, src/filfre/render_cache.py, src/filfre/IMPLEMENTATION-NOTES.md.
- Trim filfre CLI (src/filfre/cli.py) to the commands we actually keep (generate/list/log/clear) until the new brief/fill commands land (gnusto-eaec child).
- Consolidate the two experiment dirs (experiments/composition + experiments/layout) under a clear structure; preserve REPORT.md research notes as research, but relegate dead scripts/images.
- Prune stray gitignored caches and empty dirs (assets/refs/old, render caches).
- Write a single design note docs/render.md capturing the STATIC pipeline design (stage-vs-subject, single-subject-only rendering, UI-layer composition, manifest pipeline) so the scattered notes have one home. Update docs/filfre.md to match.
- Decide whether the local-FLUX stack (torch/diffusers under [render]) can be dropped now that we are external-model + static only; if so, drop it (hard cutover).
