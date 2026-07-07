---
id: gnusto-7256.2
title: 'P2: grue output-effect vocabulary (narrate/say/describe/focus/reveal/emphasize/splash/sfx)'
type: task
priority: 1
created: '2026-07-07T21:51:39Z'
updated: '2026-07-07T21:51:56Z'
labels:
- runtime
- lang
depends_on:
- gnusto-7256.1
---

Widen the engine output stream from (narrate|say, entity, text) to carry the full block vocabulary + entity refs, and add the grue effects that produce them: (narrate ...), (say @who ... [:manner]), (describe ...), (focus @obj ...), (reveal @obj ...), (emphasize ...), (splash @obj ...), (sfx ...). Map each to its ContentBlock in the P1 construction path. Keep effects simple (no inline :beat/:deploy/:group yet). Document in docs/grue.md.
