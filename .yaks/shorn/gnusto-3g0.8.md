---
id: gnusto-3g0.8
title: Skip precondition inference for runtime:go
type: task
priority: 2
created: '2026-01-24T20:11:44.066231-05:00'
updated: '2026-02-08T19:07:10.994266Z'
---

runtime:go reads many PropertyRef and LocationRef values to check room-specific conditions (floor-waxer position, gloves worn, pentagram rubbed, etc). The decomposer was treating ALL these as preconditions for ANY runtime:go action.

Fix: Skip both PropertyRef and LocationRef reads when inferring preconditions for runtime:go. Player movement is now 'free' with no preconditions, allowing complete backward chains.

Proper room-specific preconditions require frotzlm-3g0.7 (room connectivity analysis).
