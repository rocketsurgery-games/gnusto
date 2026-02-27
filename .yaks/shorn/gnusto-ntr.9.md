---
id: gnusto-ntr.9
title: Add map, filter, reduce collection functions
type: task
priority: 2
created: '2026-01-14T09:57:57.915303-05:00'
updated: '2026-02-08T19:07:11.031584Z'
labels:
- lang
---

The language is missing fundamental functional collection operations:
- `(map FN COLL)` - apply function to each element
- `(filter PRED COLL)` - keep elements matching predicate
- `(reduce FN INIT COLL)` - fold collection with accumulator

Example use case from elevator.grue (currently uses imperative loop):
```scheme
; Current imperative approach:
(let ((?glowing '()))
  (if (go-button-pressed? 0) (set! ?glowing (cons "B" ?glowing)))
  (if (go-button-pressed? 1) (set! ?glowing (cons "1" ?glowing)))
  ...)

; With filter + map:
(filter identity
  (map (fn (?i ?label) (when (go-button-pressed? ?i) ?label))
       '(0 1 2 3)
       '("B" "1" "2" "3")))
```

Also consider adding:
- `(map-indexed FN COLL)` - map with index
- `(keep FN COLL)` - like map but removes nil results
- `(remove PRED COLL)` - opposite of filter
