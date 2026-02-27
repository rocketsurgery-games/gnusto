---
id: gnusto-gv2.8
title: Enhance backward analysis for OR-conditions
type: task
priority: 2
created: '2026-01-21T15:28:32.742832-05:00'
updated: '2026-02-08T19:07:11.00122Z'
---

Static backward analysis currently only finds ONE path through OR-conditions (e.g., unlock with key OR lockpick). This causes alternate solutions to be flagged as anomalies.

The issue: backward analysis extracts preconditions by looking for (blocked ...) patterns. But OR-conditions appear as multiple success branches in cond expressions, not as blocking conditions.

Example from testgame unlock:
  (cond
    ((held? @key) -> success)        ; Path A - not analyzed
    ((held? @lockpick) -> success)   ; Path B - not analyzed
    (else -> (blocked ...)))         ; Only this is analyzed

Options:
A) Analyze all cond branches that lead to effects (not just blocked)
B) Use effect analysis reads to infer what enables behaviors
C) Accept limitation, use dynamic analysis to discover alternatives

This would make static analysis more complete and reduce false-positive anomalies.
