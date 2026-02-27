---
id: gnusto-gv2.15
title: Subgoal-based exploration for LH
type: task
priority: 2
created: '2026-01-23T11:47:28.924145-05:00'
updated: '2026-02-08T19:07:10.999231Z'
---

Break exploration into subgoals derived from constraint trees. Instead of searching all 22k states, achieve intermediate goals in sequence: @axe:held -> @emergency-cabinet:rmung -> @maintenance-man fleeing -> etc. The constraint trees already have this info, just need to use it for guided search.
