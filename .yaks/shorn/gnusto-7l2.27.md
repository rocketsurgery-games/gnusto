---
id: gnusto-7l2.27
title: Use shared snow-drifts behavior in cs-building.grue
type: task
priority: 2
created: '2026-01-14T14:11:39.280871-05:00'
updated: '2026-02-08T19:07:11.02789Z'
labels:
- lh
---

cs-building.grue has two identical snow drift barriers (lines 113-127):

```scheme
(object @snow-drifts-west
  :location @smith-st
  :description "snow drifts"
  :flags (INVISIBLE)
  :behaviors (
    :through (fn ()
      (blocked :reason snow-drifts :message "Impenetrable snow drifts block the street."))))

(object @snow-drifts-east
  :location @smith-st-2
  :description "snow drifts"
  :flags (INVISIBLE)
  :behaviors (
    :through (fn ()
      (blocked :reason snow-drifts :message "Impenetrable snow drifts block the street."))))
```

Could use shared behaviors like we did for elevator doors:
```scheme
(def snow-drift-behaviors
  '(:through (fn ()
      (blocked :reason snow-drifts :message "Impenetrable snow drifts block the street."))))

(object @snow-drifts-west
  :location @smith-st
  :description "snow drifts"
  :flags (INVISIBLE)
  :behaviors snow-drift-behaviors)

(object @snow-drifts-east
  :location @smith-st-2
  :description "snow drifts"
  :flags (INVISIBLE)
  :behaviors snow-drift-behaviors)
```

Similarly, the on-enter handlers for @smith-st and @smith-st-2 are identical (freezing trigger). Could share.
