---
id: gnusto-eaec.3
title: Render-config enumeration + explosion-guard lint
type: feature
priority: 2
created: '2026-06-16T02:16:54Z'
updated: '2026-06-18T22:53:45Z'
depends_on:
- gnusto-eaec.2
---

Use frotz / abstract interpretation to enumerate the finite set of render configs and emit a render manifest, with a static lint that GUARANTEES the set stays bounded.

- Codomain extraction: for each entity, statically collect the finite set of asset keys its :render spec can return (the cond/if branches). This is trivial for data-only specs.
- Reachability pruning (optional/iterative): intersect declared-codomain configs with frotz reachability (src/frotz explorer) to drop impossible global-axis combinations. Start with declared codomain (simpler), add reachability as an optimization.
- EXPLOSION-GUARD LINT (the key correctness property, in the spirit of this project): via abstract interpretation, enforce that a ROOM render reads only its declared room-global axes, and an OBJECT render reads only its own state. A room render that reads e.g. (:open @microwave) is a lint error. This is what keeps the scene-variant cross-product tiny by construction rather than by hope.
- Output: a render manifest (list of {asset-key, brief, optional refs}) consumed by the filfre fill tool.

Depends on the static :render model (gnusto-eaec.2).
