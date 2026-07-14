---
id: gnusto-zbg
title: 'Higher-order functions: analysis implications'
type: task
priority: 3
created: '2026-01-22T16:19:25.316818-05:00'
updated: '2026-07-12T00:45:33Z'
labels:
- lang
- analysis
---

Research and document what higher-order functions (passing functions as values, returning functions) would require from our static analysis.

Key questions:
- Effect analysis: If a function is passed as argument, how do we know what state it modifies?
- Backward analysis: How do we extract preconditions from a behavior that calls an arbitrary function?
- Conservative fallback: Can we still analyze code that doesn't use HOFs while supporting them in the language?

Notes:
- Current function inlining in effect analyzer assumes statically known function names
- Closures already work (frotzlm-ntr.15), but we don't pass them around yet
- map/filter/reduce (frotzlm-ntr.9) are built-ins, not HOFs in the general sense

Options to consider:
1. No HOFs - keep functions non-first-class
2. HOFs with mandatory effect annotations
3. HOFs with conservative 'unknown effects' fallback
4. Full HOF support with flow-sensitive analysis (complex)
