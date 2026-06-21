---
id: gnusto-a07e.3
title: Object state variants as base + deltas (:rdesc)
type: feature
priority: 2
created: '2026-06-21T20:29:59Z'
updated: '2026-06-21T20:29:59Z'
depends_on:
- gnusto-a07e.1
- gnusto-a07e.2
labels:
- render
---

Object state-sets (microwave closed/open/running, fridge open/closed) should declare ONE base variant + per-variant edit deltas, not N independent briefs. Probe result: M3 edit off a frozen base kept the SAME unit (same body, controls, framing), only the door/glow changing; prompt-only gave a different microwave each time.

- :rdesc variant map gains a base designation + delta text per non-base variant (e.g. :base :closed, then :open 'open the door, interior visible').
- filfre (a07e.2) generates the base then edits for each delta.
- Wording fix surfaced: the closed base read half-open isolated on black -> 'opaque closed door, no interior visible'.

Update docs/render.md (variant model) + docs/grue.md.
