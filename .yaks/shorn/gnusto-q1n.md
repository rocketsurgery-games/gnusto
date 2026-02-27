---
id: gnusto-q1n
title: Add default-value syntax for property access
type: task
priority: 2
created: '2026-01-17T23:58:57.859578-05:00'
updated: '2026-02-08T19:07:11.011786Z'
---

Enable `(:prop @obj default)` syntax for property access with fallback value.

Current: `(:prop @obj)` errors if property is missing
New: `(:prop @obj default)` returns default if missing, still errors with no default

This is the key enabler for checking optional boolean properties cleanly:
`(if (:open @door false) ...)` instead of verbose has-prop? checks.
