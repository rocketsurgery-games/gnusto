---
id: gnusto-4ac5.6
title: Graceful panel degradation + typographic fallback
type: feature
priority: 3
created: '2026-06-16T02:18:27Z'
updated: '2026-06-16T02:18:27Z'
depends_on:
- gnusto-4ac5.5
---

Guarantee panels never break when imagery is missing.

- Any panel that wants an image but has no pre-generated asset degrades to a text/caption panel.
- A SPLASH with no asset degrades to a TYPOGRAPHIC splash (full-bleed dramatic lettering) — itself a legit comic device, not a failure state.
- Insets/focus with no asset degrade to caption insets.
- Wire to the keyed-asset contract from gnusto-eaec.2/.4: missing key -> fallback treatment, never a broken image.

Relates to the expanded vocabulary (gnusto-4ac5.5) and the keyed-asset pipeline (gnusto-eaec). Can be built/tested with placeholders.
