---
id: gnusto-ntr.24
title: :visual-style :kinds — per-kind style/aspect specialization (room vs object)
type: feature
priority: 2
created: '2026-06-20T21:14:56Z'
updated: '2026-06-20T21:23:04Z'
---

Generalize the world :visual-style with an optional :kinds nested map keyed by entity kind (room|object|event), each a keyword-map that can override/extend style fields. Composition: :prompt is ADDITIVE (base + kind), :aspect-ratio OVERRIDES the default, :palette/:swatches inherited. Fixes: rooms breathe (2:1) vs square objects; objects forced to a consistent flat black background (kills white/black inconsistency incl. microwave-states). Touches: grue/forms parse, render.assemble_style/assemble_brief become kind-aware + new render_aspect helper, filfre fill/brief resolve per-entry kind, lurkinghorror.grue :kinds, EstablishingBlock native-wide display, docs, tests. Powers gnusto-4ac5 establishing panels.

---
▸ 2026-06-20T21:23:04Z
SHORN. Added :visual-style :kinds (per-kind style/aspect). forms.py: parse :kinds as kind->keyword-map (explicit nested, like :swatches). render.py: assemble_style/assemble_brief are kind-aware (kind :prompt additive after base) + new render_aspect(visual_style, kind) helper (kind :aspect-ratio overrides default); exported render_aspect. filfre/cli.py: fill + brief resolve prompt AND aspect per-entry kind; brief stdout now shows full composed prompt per key. lurkinghorror.grue: :kinds (:room 2:1 wide-stage / :object black-bg). EstablishingBlock: native-wide display (no 5:4 crop) so 2:1 rooms show full. Tests: kinds parse + additive prompt + render_aspect (+ updated the hoisted-style filfre test). Docs: grue.md/render.md/filfre.md. Verified: pytest 741, grue-test 477, filfre briefs show room(2:1/wide) vs object(black-bg). NOTE: lurkinghorror.grue commit also carries the user's in-progress alla-prima :prompt + :player relocation (inseparable hunks). Per-entity :style override deferred to ntr.25.
