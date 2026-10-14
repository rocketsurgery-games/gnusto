---
id: gnusto-uifont
title: 'Web UI: per-game reading font — :ui-font in :visual-style, uiFont in the theme message, bundled Comic Neue'
status: shorn
type: task
priority: 1
created: '2026-10-14T15:20:14Z'
updated: '2026-10-14T15:26:00Z'
labels:
- webui
---

A game should choose its own UI typography. Lurking Horror's reading text gets a
comic-style typeface (Comic Neue), declared in Grue and shipped to the browser on
the existing theme pipeline. A `:ui-font` token inside `:visual-style` rides the
`theme` websocket message as `uiFont`; the client owns the token -> font-family
map (Comic Neue with a Georgia fallback) and bundles the OFL webfont
(@fontsource/comic-neue, 400 + 700). Games declaring nothing are unchanged on the
wire and on screen. Spec: art_mmhasByC (per-game UI font).
