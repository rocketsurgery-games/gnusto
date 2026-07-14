---
id: gnusto-otr.14
title: 'Explorer defect B: sound ref selection — auto-track the target''s transitive
  precondition closure'
type: task
priority: 2
created: '2026-07-14T20:52:06Z'
updated: '2026-07-14T20:52:31Z'
labels:
- tooling
depends_on:
- gnusto-otr.13
---

---
▸ 2026-07-14T20:52:20Z
Defect B from the explorer diagnosis (see gnusto-otr.12). The forward explorer's fingerprint is only sound if the tracked-ref set includes EVERY ref that gates the path to the target; miss one (e.g. kitchen-window:open, lamp:lit, troll:dead) and distinct states collapse and the reachable transition is pruned -> false NO. Default reach tracks only target+player. Fix: seed the tracked set from the target's TRANSITIVE precondition closure via BackwardAnalyzer (achievers -> preconditions -> their achievers ...), plus navigation-barrier refs and hazard/darkness survival refs. Depends on A (gnusto-otr.13): the closure is only discoverable now that put/inc/dec/set-in/expose are modeled. Empirically confirmed the mechanism is otherwise sound: adding window:open unlocked the house interior (16 -> 19 rooms).
