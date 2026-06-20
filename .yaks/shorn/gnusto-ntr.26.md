---
id: gnusto-ntr.26
title: 'BUG: :swatches hexes in art brief render as a literal colour-swatch chart'
type: bug
priority: 1
created: '2026-06-20T21:33:59Z'
updated: '2026-06-20T21:33:59Z'
---

Regression from ntr.23. assemble_style appended 'Anchor the palette to these colors: #hex, #hex...' to every art brief, intending to key art to the chrome palette. But image models (NanoBanana/Gemini) render the raw hex list as a literal colour-swatch strip baked into the generated image (observed on a regenerated terminal-room). Fix: swatches drive the UI chrome ONLY; do not inject hex into briefs. Art palette comes from the prose :palette. Both still declared together in :visual-style. Updated assemble_style, test (swatches must not leak into preamble), docs (grue.md/render.md).

---
▸ 2026-06-20T21:33:59Z
SHORN. Removed the hex-anchoring block from assemble_style; swatches -> CSS chrome only (web theme message unchanged). Verified: filfre briefs contain 0 hex occurrences; pytest green. Lesson: never inject raw hex codes into image-gen prompts.
