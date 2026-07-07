---
id: gnusto-7256.4
title: 'P4: de-drift renderers — declare vocabulary once, exhaustive TUI + web dispatch'
type: task
priority: 2
created: '2026-07-07T21:51:39Z'
updated: '2026-07-07T21:51:56Z'
labels:
- render
depends_on:
- gnusto-7256.1
---

Declare the block vocabulary in ONE place and derive from it: dict serialization (block_to_dict), the LLM structured-output schema, and exhaustive dispatch on BOTH renderers so a missing type is a caught error not a silent drop. TUI gains Caption/Splash/Sfx (currently omitted). Reconcile web-only treatments (EstablishingBlock/CommandBlock/EntityInset) against the canonical vocabulary. Subsumes the old ntr notes: presentation-intent mixin + consolidated block-vocab reference.
