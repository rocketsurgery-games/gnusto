---
id: gnusto-ntr.14
title: Keywords should evaluate to themselves, not strings
type: task
priority: 2
created: '2026-01-14T10:02:30.558265-05:00'
updated: '2026-02-08T19:07:11.031115Z'
labels:
- lang
---

Keywords currently evaluate to strings.

**Current code (expr.py lines 367-369):**
```python
if isinstance(expr, Keyword):
    return expr.name
```

**Clojure norm:** Keywords evaluate to themselves (the keyword object). They're used as:
- Map keys: `{:name "Alice"}`
- Lookup functions: `(:name person)` → looks up :name in person

**Solution:**
1. Keywords should eval to Keyword objects, not strings
2. When used as a function, implement lookup: `(:key obj)` → `(get obj :key)`
3. Comparisons: `:foo` = `:foo` but `:foo` ≠ "foo"

**Impact:** Need to audit where keywords are used and ensure proper handling.

Lower priority than P1 items but still important for Clojure compatibility.
