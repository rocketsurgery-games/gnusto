---
id: gnusto-4ub
title: Refactor REPL to pure Grue syntax
type: task
priority: 1
created: '2026-01-10T16:24:24.974635-05:00'
updated: '2026-02-08T19:07:10.976228Z'
depends_on:
- gnusto-n0d
---

Replace hacky text parser in REPL with one that accepts only Grue syntax as input. This enables precise behavior validation without worrying about text parser limitations.
