---
id: gnusto-7hu
title: Design static analysis foundation for GRUE
type: task
priority: 3
created: '2026-01-11T11:50:09.347476-05:00'
updated: '2026-02-08T19:07:11.075981Z'
depends_on:
- gnusto-c0b
- gnusto-c65
---

Plan for future static analysis capabilities. This task is about designing the foundation, not implementing full analysis.

Potential analyses:
1. **Type checking** - Verify predicates return bools, effects return void, objects exist
2. **Dead code detection** - Behaviors that can never trigger
3. **Reachability** - Rooms/states that can't be reached
4. **Completeness** - Missing behavior handlers for common verbs
5. **Consistency** - Flag used in condition but never set, object referenced but not defined

Requirements for static analysis:
- Clean AST representation (forms.py refactor helps)
- Symbol table with type information
- Understanding of special form semantics
- Separate parse phase from evaluation phase

This task: Write design doc outlining:
- What analyses are valuable for IF authoring
- What AST/IR representation supports these
- How current architecture can evolve to support this

Depends on: frotzlm-c0b (semantics doc), frotzlm-c65 (parser refactor)
