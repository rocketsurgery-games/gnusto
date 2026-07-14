---
id: gnusto-9f40
title: :generate — per-emission LLM text opt-in into the block stream
type: feature
priority: 3
created: '2026-07-07T21:51:39Z'
updated: '2026-07-12T00:44:31Z'
labels:
- lang
- render
depends_on:
- gnusto-7256.4
---

A grue directive like (generate "brief" :refs (...)) that the harness expands by calling the LLM and splicing the produced block(s) into the same ordered stream, in order. Explicit, local, opt-in text generation — mostly for new games. Deferred until P1-P4 land.
