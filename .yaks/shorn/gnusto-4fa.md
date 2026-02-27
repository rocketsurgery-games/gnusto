---
id: gnusto-4fa
title: Implement OUTSIDE-DOOR as DSL behavior test case
type: task
priority: 1
created: '2026-01-09T12:27:03.338764-05:00'
updated: '2026-02-08T19:07:10.978035Z'
depends_on:
- gnusto-bkv
---

Hand-implement OUTSIDE-DOOR from Lurking Horror in the new behavioral DSL. This is a good test case because it has: location-dependent behavior (OUTSIDE flag check), verb dispatching (THROUGH, OPEN, UNLOCK), object interactions (MASTER-KEY), state checks and transitions. Use this to validate the DSL design before automating translation.
