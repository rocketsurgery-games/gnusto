---
id: gnusto-krs.2
title: Add (set) effect for property mutation
type: task
priority: 1
created: '2026-01-17T17:54:07.954905-05:00'
updated: '2026-02-08T19:07:10.960705Z'
---

Add a (set @obj :prop value) effect for mutating object properties.

This replaces (set-prop! @obj prop val) with cleaner syntax that works within the effects system:

(success :effects ((set @obj :timer 120)
                   (set @obj :temp 4)))

Note: This is an EFFECT, not a function. Property mutation only happens through the effects system to maintain purity.
