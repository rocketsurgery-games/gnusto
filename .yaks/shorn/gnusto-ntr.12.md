---
id: gnusto-ntr.12
title: Unify list representation (SList vs Python list)
type: task
priority: 1
created: '2026-01-14T10:02:13.495202-05:00'
updated: '2026-02-08T19:07:10.968625Z'
labels:
- lang
---

The evaluator currently treats SList and Python list differently:
- SList: code (forms to evaluate)
- Python list/tuple: data (self-evaluating)

This causes problems when substitution mixes evaluated values (Python objects) into the AST (SList). We had to add a hack to convert SList→list in _substitute.

**Current code (expr.py lines 352-354, 370-371):**
```python
if isinstance(expr, (tuple, list)):
    # Data values (e.g., quoted lists) evaluate to themselves
    return expr
# ...
if isinstance(expr, SList):
    return self._eval_form(expr)
```

**Lisp norm:** Have ONE list type. The distinction between code and data is syntactic (quote), not type-based. `'(1 2 3)` is the same type as `(+ 1 2)`, just with a quote wrapper.

**Solution options:**
1. Always use SList, add a "quoted" flag or wrapper
2. Always use Python list, have quote return Python lists
3. Use SList for AST only, convert to Python list when evaluating quotes

Option 3 is cleanest - keep SList internal to parser, evaluate quoted expressions to Python lists.

This depends on frotzlm-ntr.11 (lexical environments) since proper environments would eliminate the substitution hack.
