---
id: gnusto-eaec.2
title: Static :render model (stage-vs-subject, :rdesc, :visual-style)
type: feature
priority: 2
created: '2026-06-16T02:16:39Z'
updated: '2026-06-18T04:05:37Z'
---

Extend the Grue :render model from a bare filename string into a static, keyed, brief-bearing spec. Language work — also track under the language epic (gnusto-ntr per CLAUDE.md).

- :render evaluates (statically and at runtime) to an asset KEY. State-conditional (fn () (cond ...)) forms already return distinct filenames per state — that codomain IS the keyset.
- Reintroduce :rdesc — a render BRIEF distinct from player-facing :description, may be state-aware (a fn). Drives generation prompts / artist briefs.
- Add a world-level :visual-style block (style prefix + palette hooks) as a static brief prefix. (Presentation THEME — fonts/colors/chrome — lives in per-game CSS, not here; see the theme child.)
- Encode the STAGE-vs-SUBJECT discipline in the model:
  * room renders key only on a small DECLARED set of room-global axes (light, flood, power...);
  * object renders key only on their own state;
  * fixed-object briefs may be contextual (in-situ), movable-object briefs neutral (reusable as inventory thumbnails).
- Runtime resolve: :render -> key -> asset path, with graceful fallback (empty stage / text) when a key is missing.

Update grue/forms.py, grue/render.py, gnusto/render.py accordingly. Add Grue tests. Update docs/grue.md.
