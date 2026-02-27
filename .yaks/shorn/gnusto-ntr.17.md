---
id: gnusto-ntr.17
title: Empty list () should be nil/falsy, not error
type: task
priority: 2
created: '2026-01-14T10:03:00.006761-05:00'
updated: '2026-02-08T19:07:11.030791Z'
labels:
- lang
---

Empty form \`()\` raises "Empty form" error instead of being nil.

**Current code (expr.py _eval_form):**
```python
if len(form) == 0:
    raise EvalError("Empty form")
```

**Lisp norm:** \`()\` is typically \`nil\`/empty list:
- Self-evaluating (returns itself or nil)
- Falsy in boolean context
- Same as \`'()\` or \`nil\`

**Scheme:** \`()\` is the empty list, \`'()\` quotes it (but result is same)
**Clojure:** \`()\` in code position is an error (can't call nothing), but \`'()\` and \`nil\` are distinct

**Options:**
1. Scheme-style: \`()\` evaluates to empty list (which is falsy)
2. Clojure-style: \`()\` is an error in code position, have separate \`nil\`
3. Current error but better message

For IF game DSL, Clojure-style (option 2) is probably fine. We should have:
- \`nil\` as a distinct value
- \`'()\` evaluates to empty list
- \`()\` in call position is an error (current behavior, but cleaner)

This relates to frotzlm-ntr.12 (list unification).
