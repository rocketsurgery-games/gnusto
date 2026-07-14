---
id: gnusto-6b4f
title: 'Randomness in game conversions: deterministic vs. analyzable design'
type: task
priority: 3
created: '2026-07-14T02:17:40Z'
updated: '2026-07-14T02:18:24Z'
labels:
- design
- runtime
---

---
▸ 2026-07-14T02:17:55Z
Root design theme (hoisted out of the Zork epic gnusto-fa93). Infocom games lean on RNG everywhere: the thief's wandering/thieving/melee (I-THIEF), the grue death roll, combat hit/miss and knockout/flee outcomes, monster movement, dig counts, etc. Our conversions DROP or replace that randomness so the world stays statically analyzable (frotz reach / deadends / winnability), since RNG makes the state space unsound to explore.

Deterministic tactics used so far (precedent): grue = a configurable dark-turn GRACE then certain death (not a per-turn roll); troll/cyclops/thief = strength-based deterministic duels; cyclops = the 'Odysseus' magic word; dam/exorcism/diamond = scripted multi-step puzzles; dig = a fixed count; hazards modeled as turn-based events (LH freezing / the grue) queued from turn 1.

Open question this yak owns: how to reintroduce BOUNDED, ANALYZABLE variety so conversions keep their flavor (a roving menace, unpredictable combat) WITHOUT breaking static analysis. Options to weigh:
  - Scripted/turn-indexed patterns (a patrol route; state-triggered theft) — deterministic but lively.
  - Seeded/replayable RNG the analyzer can enumerate or bound (explore all seeds / worst-case).
  - A first-class defhazard-style construct (see gnusto-5818) unifying grue/freezing/thief-style menaces.
  - Frotz support for probabilistic transitions (bounded branching) if we keep any RNG.

Concrete instance: gnusto-6b4f.1 (richer analyzable thief) is reparented under this. Cross-ref: gnusto-5818 (defhazard design), the grue hazard event, and the LH freezing pattern.
