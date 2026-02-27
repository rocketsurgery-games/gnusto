---
id: gnusto-ntr.13
title: Unbound symbols should error, not return string
type: task
priority: 1
created: '2026-01-14T10:02:23.120062-05:00'
updated: '2026-02-08T19:07:10.968335Z'
labels:
- lang
---

Undefined symbols silently become strings instead of raising errors.

**Current code (expr.py lines 361-366):**
```python
try:
    return self.state.get_global(expr.name)
except (KeyError, AttributeError):
    # Return as string literal (object name, flag name, etc.)
    return expr.name
```

**Problem:** This masks bugs. For example, `empty?` and `cons` were returning their names as strings for a long time because they weren't implemented. Code appeared to work but produced wrong results.

**Lisp norm:** Unbound symbols should raise an error. Exceptions:
- Self-quoting forms: keywords (Clojure), nil/t (Common Lisp)
- Intentionally undefined (should be explicit, not fallback)

**Solution:**
1. Raise `UnboundVariableError` for unknown symbols
2. If we need literal strings for object names (@player), use explicit syntax:
   - Keep @ prefix for object references
   - Or use symbols explicitly: `'player`
   - Or use strings: `"player"`

**Migration concern:** Existing code relies on this behavior for:
- Object names (@player → "@player")
- Flag names (TAKEBIT → "TAKEBIT")
- Maybe other cases

Need to audit usage patterns and decide on explicit syntax.

This is critical for language soundness - errors should be loud, not silent.
