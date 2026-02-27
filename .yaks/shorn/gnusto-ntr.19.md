---
id: gnusto-ntr.19
title: Replace any/all with Clojure-style some/every?
type: task
priority: 3
created: '2026-01-14T15:10:26.372897-05:00'
updated: '2026-02-08T19:07:11.074551Z'
labels:
- lang
---

Replaced (any coll lambda) with (some pred coll) and (all coll lambda) with (every? pred coll) to match Clojure argument order. some returns first truthy result, every? returns boolean.
