---
id: gnusto-muv
title: Context messages show unevaluated S-expressions
type: bug
priority: 3
created: '2026-01-14T21:26:39.433802-05:00'
updated: '2026-02-08T19:07:11.074341Z'
---

When behaviors return context values that are S-expressions (like (if ...) forms), they show as raw Symbol strings instead of being evaluated. Example: microwave :open shows 'description=(Symbol(if) (Symbol(queued?) ...' instead of the evaluated result. Context values should be evaluated before display.
