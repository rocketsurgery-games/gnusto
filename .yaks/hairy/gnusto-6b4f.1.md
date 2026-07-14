---
id: gnusto-6b4f.1
title: 'Richer analyzable thief: scripted wandering/thieving without RNG'
type: task
priority: 4
created: '2026-07-12T18:51:05Z'
updated: '2026-07-14T02:18:24Z'
labels:
- design
---

---
▸ 2026-07-12T18:51:13Z
Follow-up to fa93.8. The initial thief is a stationary lair encounter (deterministic duel), dropping ZIL's random wandering (I-THIEF), random treasure theft, and random melee. Come back and design a RICHER but still statically-analyzable thief: e.g. a scripted/turn-indexed patrol route instead of RNG wandering; deterministic theft triggered by state (entering a room with a loose treasure while the thief is present) rather than probability; and the knockout/flee outcomes as deterministic branches. Goal: preserve the flavor of a roving menace while keeping frotz reach/deadends sound. Cross-ref the LH hazard-event pattern + the grue for precedent.
