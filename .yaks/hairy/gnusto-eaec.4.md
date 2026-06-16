---
id: gnusto-eaec.4
title: 'filfre brief/fill: manifest -> images or artist briefs'
type: feature
priority: 2
created: '2026-06-16T02:17:03Z'
updated: '2026-06-16T02:18:47Z'
depends_on:
- gnusto-eaec.3
---

New filfre subcommands that turn a render manifest into pre-generated assets OR human-fillable briefs — the same keyset either way.

- filfre brief (or manifest): read the render manifest (gnusto-eaec.3) and emit per-key BRIEFS: structured prompt = world :visual-style prefix + entity :rdesc + spatial framing + state. Printable for a human artist to fill the exact same key set.
- filfre fill: consume the manifest and generate via a frontier model (keep nanobanana/Gemini path; drop local FLUX if retired in cleanup), writing keyed assets.
- Honor the single-subject discipline: rooms render as EMPTY/global-state STAGES (no movable objects); objects/characters render as single subjects (fixed=in-situ contextual, movable=neutral bg). Per experiments/composition/REPORT.md, empty stages + single-subject is the reliable regime.
- Keep the keyed-asset output contract stable so runtime resolve (gnusto-eaec.2) and the UI fallback (Epic B) can depend on it.

Update docs/filfre.md. Depends on gnusto-eaec.3.
