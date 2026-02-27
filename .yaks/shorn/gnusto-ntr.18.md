---
id: gnusto-ntr.18
title: Consider adding range function for iteration
type: task
priority: 3
created: '2026-01-14T14:12:19.875532-05:00'
updated: '2026-02-08T19:07:11.074858Z'
labels:
- lang
---

While implementing for/doseq, I noticed we don't have a range function. This would be useful for elevator iteration:

```scheme
(for (?floor (range 4)) ...)         ; iterate 0-3
(for (?floor (range 1 4)) ...)       ; iterate 1-3
```

Clojure-style range:
- (range n) → (0 1 ... n-1)
- (range start end) → (start start+1 ... end-1)
- (range start end step) → (start start+step ...)

This is a language feature, not a LH task.
