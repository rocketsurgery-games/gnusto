---
id: gnusto-pwq
title: 'Simplify test DSL: collapse test/test-sequence, add (run) for action lists'
type: task
priority: 2
created: '2026-01-16T11:24:13.229675-05:00'
updated: '2026-02-08T19:07:11.022925Z'
---

Refactor the test infrastructure based on purity model discussion:

1. **Collapse (test) and (test-sequence)** into a single form
   - Both become sequences of actions + assertions
   - Remove the :action/:expect structure from (test)
   - Unified form: (test "name" (do ...) (assert ...) ...)

2. **Add (run ACTION-LIST)** form
   - Executes a quoted list of actions
   - Or a symbol referencing such a list: (run walkthrough/kitchen)
   - Available only in test context (not game logic)

3. **Keep (do), (assert), (until), (wait)** as test primitives
   - These are the imperative boundary
   - Not exposed to game logic

4. **Remove (seq)** - redundant with bare (do) calls in sequence

This sets up the infrastructure for walkthrough tests and clarifies the pure/impure boundary.
