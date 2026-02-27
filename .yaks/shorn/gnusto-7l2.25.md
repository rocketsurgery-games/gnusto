---
id: gnusto-7l2.25
title: Simplify microwave heating logic with doseq
type: task
priority: 2
created: '2026-01-14T14:11:21.591521-05:00'
updated: '2026-02-08T19:07:11.029359Z'
labels:
- lh
---

kitchen.grue microwave-running event (lines 254-288) has duplicated heating logic in both the timer-expired and timer-running branches.

The heating code is:
```scheme
(when (inside? @chinese-food @microwave)
  (set-prop! @chinese-food heat (+ (prop @chinese-food heat) microwave-temp)))
(when (inside? @carton @microwave)
  (set-prop! @carton heat (+ (prop @carton heat) microwave-temp)))
(when (and (inside? @chinese-food @microwave) (> (prop @chinese-food heat) 20))
  (set-flag! @chinese-food RMUNGBIT))
```

Could extract to a helper function:
```scheme
(defn heat-microwave-contents ()
  (doseq (?item '(@chinese-food @carton))
    (when (inside? ?item @microwave)
      (set-prop! ?item heat (+ (prop ?item heat) microwave-temp))))
  (when (and (inside? @chinese-food @microwave) (> (prop @chinese-food heat) 20))
    (set-flag! @chinese-food RMUNGBIT)))
```

Or even better, use a heatable items list like the ZIL HEAT-TABLE:
```scheme
(def heatable-items '(@chinese-food @carton @smooth-stone @dead-rat @hand @coke @snack))

(defn heat-microwave-contents ()
  (doseq (?item heatable-items)
    (when (inside? ?item @microwave)
      (set-prop! ?item heat (+ (prop ?item heat) microwave-temp)))))
```
