---
id: gnusto-vo2
title: 'Simplify REPL: use unified evaluation instead of special-cased commands'
type: task
priority: 2
created: '2026-01-11T11:49:49.038048-05:00'
updated: '2026-02-08T19:07:11.054398Z'
---

Current REPL (repl.py) has special-case handling for each command type:
- `look`, `inventory`, `exits`, `state`, `reset`, `help`, `quit` - meta commands
- `go` - movement with custom arg parsing
- `do` - actions with custom arg parsing and result display
- Effects (`move!`, `set-flag!`, etc.) - delegated to EffectExecutor
- Queries - delegated to ExprEvaluator

Goal: REPL should be a thin layer that:
1. Parses input via sexpr parser
2. Evaluates via a unified evaluator
3. Prints results

Implementation:
- Define meta-commands as built-in functions: `(look)` -> returns room description data
- `(go :direction D)` and `(do :verb V ...)` become function calls
- Result printing based on return type, not command type
- REPL loop becomes: parse -> eval -> print

This aligns REPL behavior with how a static analyzer would process code.
