---
id: gnusto-krs.5
title: Add (inc) and (dec) helper effects
type: task
priority: 2
created: '2026-01-17T17:54:25.952367-05:00'
updated: '2026-02-08T19:07:11.014682Z'
---

Add convenience effects for incrementing/decrementing numeric properties:

(success :effects ((inc @player :score 10)
                   (dec @microwave :timer 60)))

Sugar for the common pattern of:
(set @obj :prop (+ (:prop @obj) amount))

Which would otherwise require quasi/unquote syntax.
