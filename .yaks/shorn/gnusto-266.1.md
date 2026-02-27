---
id: gnusto-266.1
title: 'Phase 1: Grue partial evaluator'
type: task
priority: 1
created: '2026-01-23T17:55:29.487569-05:00'
updated: '2026-02-08T19:07:10.956156Z'
---

Implement a partial evaluator for Grue expressions that:

1. Inlines pure function calls (defn)
2. Simplifies conditionals where branches are statically determined
3. Propagates constants through expressions
4. Handles recursion conservatively (depth limit or mark as 'complex')

Output: Reduced expressions where state dependencies are explicit.

Example transformation:
  Before: (waxer-next-loc ?loc true)
  After:  (cond ((= ?loc @inf-5) @inf-4) ((= ?loc @inf-4) @inf-3) ...)

This is foundational - all subsequent analysis operates on reduced expressions.

Deliverables:
- src/grue/reduce.py with Reducer class
- Unit tests for reduction of various expression patterns
- Integration with existing behavior analysis
