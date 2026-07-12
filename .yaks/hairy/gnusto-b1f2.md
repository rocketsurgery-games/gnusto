---
id: gnusto-b1f2
title: Migrate remaining event description/ambient context to narrate (7256 straggler)
type: task
priority: 3
created: '2026-07-12T00:09:11Z'
updated: '2026-07-12T00:09:11Z'
labels:
- lurkinghorror
- render
- lang
---

Follow-up to the engine-authoritative migration (gnusto-7256.3). Several LH files still emit player-facing EVENT narration via (success :context ((description ...))) / ((ambient ...)) instead of the output vocabulary (narrate/say/...): alchemy, brown-building, elevator, great-dome, kitchen, maintenance-man, steam-tunnels, urchins, yuggoth. These render (description is in TEXT_CONTEXT_KEYS) so it's not broken, but it's inconsistent with the narrate stream and means (output? ...) assertions don't catch them (tests must fall back to brittle exact (context? description ...) matches -- see elevator.test.grue 'in-transit feedback'). Audit each: migrate EVENT bodies to narrate/emphasize/etc.; LEAVE room/object :describe structural (that's intentional). Then convert the (context? description ...) test assertions to (output? ...).
