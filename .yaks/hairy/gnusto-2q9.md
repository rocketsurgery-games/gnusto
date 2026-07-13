---
id: gnusto-2q9
title: Implement real macro system
type: task
priority: 4
created: '2026-01-17T23:42:42.527111-05:00'
updated: '2026-07-12T19:47:28Z'
depends_on:
- gnusto-ntr
labels:
- lang
---

The threading macros (-> and ->>) are currently implemented as special forms in the evaluator. For better extensibility and to allow user-defined macros, implement a proper macro system with defmacro. This would allow macros to be defined in Grue itself rather than hardcoded in Python.

---
▸ 2026-07-12T19:47:28Z
Concrete motivating use case beyond ->/->>: (defhazard ...) — see docs/design/defhazard.md and gnusto-5818. It requires the macro system to support DEFINITIONAL macros (expand to top-level (event ...) forms), a macroexpand PRE-PASS that feeds both the runtime and frotz/lint (so expanded events are analyzed like hand-written ones — the key reason to prefer macros over HOFs/gnusto-zbg here), multi-form output, quasiquote + unquote-splice templates, keyword-arg macro params, and gensym/hygiene. Building 2q9 to satisfy defhazard lands it as a real Lisp macro system rather than defmacro-sugar over threading.
