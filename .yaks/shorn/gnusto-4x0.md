---
id: gnusto-4x0
title: Standardize behaviors as keyword map
type: task
priority: 1
created: '2026-01-11T01:37:11.605269-05:00'
updated: '2026-02-08T19:07:10.97431Z'
depends_on:
- gnusto-9e7
---

Ensure all behaviors use keyword map syntax consistently.

Before (list of tuples):
```lisp
:behaviors (
  (examine (case ...) (case ...))
  (take (case ...) (case ...)))
```

After (keyword map):
```lisp
:behaviors (
  :examine (cond ...)
  :take (cond ...))
```

The parser already supports keyword syntax for behaviors - this ensures it's the canonical form.
