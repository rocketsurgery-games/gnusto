---
id: gnusto-f95a.2
title: Elevator 'scenic detour' has almost no feedback
type: idea
priority: 3
created: '2026-07-11T14:37:53Z'
updated: '2026-07-12T00:09:29Z'
labels:
- lurkinghorror
- elevator
---

Pressing DOWN at floor 2 with the car at floor 1 sends it UP to floor 3 first, then back down to 2 (a correct elevator SCAN algorithm), costing ~3 waits with only 'You hear the elevator...' as feedback. Behavior is arguably faithful, so possibly WAI -- but the sparse narration makes it feel broken to a player. Consider richer in-transit narration, or simplifying the call logic. Low priority; revisit after gnusto-f95a.1 (soft-lock) is fixed and the elevator is actually usable.

---
▸ 2026-07-12T00:09:29Z
Done (0f6cd33). elevator-moves keep-moving branch now narrates for floor-waiting players: 'The elevator passes your floor, still heading up/down.' on a non-stopping pass, else 'You hear the elevator moving.' Fixed latent direction bug (narration read :direction after pick-direction lookahead flip; now captures ?moving-up before). Regression test added. Filed gnusto-b1f2 for the broader event description->narrate straggler.
