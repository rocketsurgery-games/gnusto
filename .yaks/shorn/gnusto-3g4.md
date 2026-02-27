---
id: gnusto-3g4
title: set! doesn't work with let-bound variables
type: bug
priority: 2
created: '2026-01-15T18:32:25.499086-05:00'
updated: '2026-02-08T19:07:11.024653Z'
labels:
- LH
---

During frotzlm-68x fix, discovered that (set! ?local-var value) inside a let block doesn't actually modify the local variable - the value stays as nil and effects capture Symbol(?local-var) literally instead of the value.

Workaround: Use helper functions with explicit arguments instead of local mutation.

This is expected in pure functional languages but may be surprising. Should either:
1. Document this limitation clearly
2. Support local mutation via a different mechanism (atom? var!?)
3. Issue a warning when set! is called on a let-bound variable
