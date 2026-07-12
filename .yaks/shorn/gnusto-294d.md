---
id: gnusto-294d
title: and/or should return the deciding value, not a coerced bool (Clojure/LISP)
type: task
priority: 3
created: '2026-07-11T23:59:44Z'
updated: '2026-07-12T00:52:28Z'
labels:
- lang
- runtime
---

Related Python-leak found while fixing truthiness (gnusto-be0a): ExprEvaluator._eval_and/_eval_or return Python True/False instead of the deciding value. In Clojure/Scheme/CL, (or nil 5) => 5, (and 1 2) => 2, (or a b) => first truthy or last. Grue booleanizes. Low urgency (most call sites use the result as a condition, where truthiness is preserved now that be0a uses is_truthy), but it's a real divergence: code can't use (or x default) as a value-select idiom. Fix: return the actual deciding operand (and: last if all truthy else first falsy; or: first truthy else last). Audit call sites that depend on a strict bool result first. Keep (not ...) returning bool (matches Clojure).
