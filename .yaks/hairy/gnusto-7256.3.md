---
id: gnusto-7256.3
title: 'P3: migrate Lurking Horror to the block vocabulary (canonical conversion)'
type: task
priority: 1
created: '2026-07-07T21:51:39Z'
updated: '2026-07-07T21:51:56Z'
labels:
- lurkinghorror
- lang
depends_on:
- gnusto-7256.2
---

Migrate LH grue to the P2 vocabulary as the canonical Infocom-conversion reference: :message (x471) -> (narrate ...)/(say @who ...); :describe :context((description)) (x123) -> (describe ...) for rooms/objects (object examine -> focus); :context((hint)) (x4) -> (say @hacker ...); :transition / compulsion pages -> (emphasize ...)/(splash ...); drop :page/:stage from output (keep as state). Remove now-vestigial context-text folding from the P1 path once migrated. Document conventions in docs/grue.md as the reference.
