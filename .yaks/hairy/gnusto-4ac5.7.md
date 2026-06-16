---
id: gnusto-4ac5.7
title: Webtoon-responsive panel geometry (vertical spine)
type: feature
priority: 2
created: '2026-06-16T02:18:34Z'
updated: '2026-06-16T02:18:34Z'
depends_on:
- gnusto-4ac5.1
---

Establish the responsive layout 'spine' for the whole panel system.

- WEBTOON-style vertical reflow is the responsive BASE geometry: panels stack vertically and reflow cleanly across viewports (mobile-first). This is the reliability-defining call vs fixed multi-column print pages.
- Print-style multi-panel TIERS (rows) are a desktop-only PROGRESSIVE ENHANCEMENT layered on the vertical spine.
- Reconcile with bounded pages (gnusto-4ac5.4): scroll within a bounded page, page-flip between pages.
- Define the panel/gutter/lettering CSS primitives that the renderer and the per-game theme (gnusto-eaec.6) build on.

Foundational layout work alongside gnusto-4ac5.1.
