---
id: gnusto-9e7
title: Replace case ladder with cond
type: task
priority: 1
created: '2026-01-11T01:36:58.685168-05:00'
updated: '2026-02-08T19:07:10.974828Z'
depends_on:
- gnusto-aws
---

Refactor behavior syntax to use standard Lisp constructs.

## Changes
1. Replace `(case COND :outcome TYPE ...)` with `(COND (TYPE ...))`
2. Wrap clauses in `(cond ...)` form
3. Use keyword map for behaviors: `:verb (cond ...)`

## Before
```lisp
:behaviors (
  (take
    (case (not (has-flag self TAKEBIT))
      :outcome blocked
      :reason not-takeable
      :context ((message "Can't take that.")))
    (case true
      :outcome success
      :effects ((move! self ?actor)))))
```

## After
```lisp
:behaviors (
  :take (cond
    ((not (has-flag self TAKEBIT))
      (blocked :reason not-takeable :message "Can't take that."))
    (true
      (success :effects ((move! self ?actor))))))
```

## Benefits
- Aligns with Scheme/Clojure conventions
- `cond` is a well-known construct
- Outcome type is now the form head, clearer semantics
- Keyword map for behaviors is more explicit

Merged from frotzlm-aws and frotzlm-4x0.
