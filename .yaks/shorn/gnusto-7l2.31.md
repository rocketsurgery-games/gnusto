---
id: gnusto-7l2.31
title: Clean up unnecessary cond wrapping
type: task
priority: 2
created: '2026-01-14T14:12:09.9832-05:00'
updated: '2026-02-08T19:07:11.026544Z'
labels:
- lh
---

Several places have unnecessary (cond (true ...)) wrapping single expressions:

**pc.grue line 74-77:**
```scheme
:put-on (fn (?item)
  (cond
    (true
      (blocked :reason not-a-surface ...))))
```
Should just be:
```scheme
:put-on (fn (?item)
  (blocked :reason not-a-surface ...))
```

**pc.grue line 325-328:**
```scheme
:examine (fn ()
  (cond
    (true
      (redirect :action (do @odd-paper :read)))))
```
Should just be:
```scheme
:examine (fn ()
  (redirect :action (do @odd-paper :read)))
```

These patterns might have been placeholders for future conditions that never materialized.
