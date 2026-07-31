---
id: gnusto-266.5.1
title: 'Kernel oracle-honesty: make enumerate_actions a true sound superset (multi-arg
  cartesian + in-source constant pool for value args)'
type: task
priority: 2
created: '2026-07-31T03:45:49Z'
updated: '2026-07-31T03:49:51Z'
labels:
- tooling
---

---
▸ 2026-07-31T03:49:51Z
Done. Closed two enumerate_actions gaps in src/frotz/kernel.py that made the oracle's sound-superset claim false (either could yield a false NO). (1) Multi-arg behaviors: now the cartesian product (itertools.product) over per-param candidate pools, not a single arg. (2) Value args: new _literal_args harvests string/number/bool literals from each behavior body as the candidate value pool (passwords, combinations); _arg_pool narrows by param-type annotation (entity -> scope objects, string/number/symbol -> literals, untyped -> union). Residual: values known only by foreknowledge (never a literal in source) remain uncovered -> gnusto-266.5.4. Tests: 4 new in tests/frotz/test_kernel.py (value-arg enumerated + reachable via COMBO game; multi-arg enumerated as genuine 2-arg + reachable via TWOARG game). Full frotz suite 133 passed; Mini still 20 states (0-param behaviors unaffected). Updated docs/design/state-graph-kernel.md sections 2 and 6.
