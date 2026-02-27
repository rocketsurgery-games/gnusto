---
id: gnusto-ntr.8
title: Support symbol references in :behaviors
type: task
priority: 2
created: '2026-01-14T09:32:12.460192-05:00'
updated: '2026-02-08T19:07:11.032354Z'
labels:
- lang
---

Currently `:behaviors` expects a literal list at parse time:

```scheme
; This works:
(object @foo
  :behaviors (
    :examine (fn () (success))))

; This doesn't work:
(def shared-behaviors '(:examine (fn () (success))))
(object @foo
  :behaviors shared-behaviors)  ; Error: Expected behaviors list, got Symbol
```

This prevents sharing behavior definitions across similar objects. The workaround is to use shared functions called from thin wrappers:

```scheme
(defn foo-examine (?obj) (success))
(object @foo
  :behaviors (:examine (fn () (foo-examine ?self))))
```

Options to fix:
1. Resolve `def` references at parse time in `parse_behaviors()`
2. Add a behavior mixin system
3. Add macros that expand before parsing

Discovered while refactoring elevator doors - 4 nearly identical objects that could share a single behavior definition.
