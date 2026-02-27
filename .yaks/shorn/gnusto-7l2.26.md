---
id: gnusto-7l2.26
title: Use condp for elevator floor dispatch
type: task
priority: 2
created: '2026-01-14T14:11:30.076264-05:00'
updated: '2026-02-08T19:07:11.028886Z'
labels:
- lh
---

elevator.grue has several places using cascading cond for floor dispatch. These could use condp:

**door-at-elevator (lines 33-39):**
```scheme
; Current
(defn door-at-elevator ()
  (cond
    ((= elevator-loc 0) @elevator-door-b)
    ((= elevator-loc 1) @elevator-door-1)
    ((= elevator-loc 2) @elevator-door-2)
    (true @elevator-door-3)))

; Could be
(defn door-at-elevator ()
  (condp = elevator-loc
    0 @elevator-door-b
    1 @elevator-door-1
    2 @elevator-door-2
    @elevator-door-3))
```

**@elevator-exit :through (lines 150-153):**
```scheme
; Current
(cond
  ((= elevator-loc 0) (redirect :to @cs-basement))
  ((= elevator-loc 1) (redirect :to @comp-center))
  ((= elevator-loc 2) (redirect :to @cs-2nd))
  (true (redirect :to @cs-3rd)))

; Could be
(condp = elevator-loc
  0 (redirect :to @cs-basement)
  1 (redirect :to @comp-center)
  2 (redirect :to @cs-2nd)
  (redirect :to @cs-3rd))
```

Or even better, use a lookup table:
```scheme
(def floor-rooms '(@cs-basement @comp-center @cs-2nd @cs-3rd))
(redirect :to (nth floor-rooms elevator-loc))
```
