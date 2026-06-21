---
id: gnusto-4ac5.15
title: Render deploy=background (asset behind panel text)
type: feature
priority: 4
created: '2026-06-21T00:10:00Z'
updated: '2026-06-21T00:10:00Z'
---

Follow-on from gnusto-4ac5.5/.6. The asset-deployment field accepts
`feature | inset | background`, and `inset` renders (framed specimen plate via
EntityInset, with caption-inset fallback). `background` is accepted by the
schema/parser but currently falls through to the default treatment — no distinct
rendering yet.

Scope:
- On reveal/focus with deploy=background, render the entity art as a dim,
  full-width BACKGROUND plate behind the block text (legible overlay; subtle so
  text stays readable), degrading to no-background (plain text) when the asset
  is missing — same never-break contract as .6.
- Keep it engine-owned (LLM only picks the deploy intent).

Low priority; no degradation risk today (background already degrades to the
default treatment).
