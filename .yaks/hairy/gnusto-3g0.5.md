---
id: gnusto-3g0.5
title: Extract actual required values from conditional guards
type: task
priority: 3
created: '2026-01-24T18:32:05.349031-05:00'
updated: '2026-02-08T19:07:11.067386Z'
---

Currently _preconditions_for() guesses required values based on property names (e.g., 'if behavior reads rmung, assume it needs rmung=True'). This is wrong when the behavior reads a property to BLOCK when it's already in a certain state.

Example: @high-voltage:cut reads :rmung to check (not (:rmung ?self)) - it blocks when rmung is True, not when it's False.

Proper fix: Analyze conditional structure to extract actual required values:
1. Find the success branch of a cond
2. Trace back what conditions led to that branch
3. Extract the required property values from those conditions

This is more complex static analysis - defer until quick fixes are done.
