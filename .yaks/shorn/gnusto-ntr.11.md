---
id: gnusto-ntr.11
title: Implement proper lexical environments instead of substitution
type: task
priority: 1
created: '2026-01-14T10:02:02.951662-05:00'
updated: '2026-02-08T19:07:10.968937Z'
labels:
- lang
---

CRITICAL: The current implementation uses textual substitution for variable binding in `let` and `fn`. This breaks fundamental Lisp semantics.

**Current approach:**
```python
# In _eval_let:
value = self.eval(binding[1])
result_expr = self._substitute(result_expr, name, value)
return self.eval(result_expr)
```

**Problems:**
1. Values substituted directly into code cause data/code confusion
2. SList values become forms to evaluate (had to hack _substitute to convert SList→list)
3. No proper lexical scope - closures don't capture environments correctly
4. Performance issues (re-parsing/transforming expressions)
5. Can't distinguish quoted data from code after substitution

**Solution:** Implement an Environment class:
```python
@dataclass
class Environment:
    bindings: dict[str, Any]
    parent: Optional["Environment"] = None

    def lookup(self, name: str) -> Any:
        if name in self.bindings:
            return self.bindings[name]
        if self.parent:
            return self.parent.lookup(name)
        raise UnboundVariableError(name)
```

Then evaluator carries current environment and extends it for let/fn:
```python
def eval(self, expr: SExpr, env: Environment) -> Any:
    if isinstance(expr, Symbol):
        return env.lookup(expr.name)
    # ...

def _eval_let(self, form: SList, env: Environment) -> Any:
    new_env = Environment({}, parent=env)
    for binding in bindings:
        new_env.bindings[name] = self.eval(value_expr, env)  # or new_env for let*
    return self.eval(body, new_env)
```

This is a significant refactor but essential for a sound language implementation.
