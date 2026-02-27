---
id: gnusto-gv2.12
title: 'Improve backward analysis: equality conditions, ?self resolution, runtime
  preconditions'
type: task
priority: 2
created: '2026-01-22T18:04:58.577338-05:00'
updated: '2026-02-08T19:07:11.000062Z'
---

Three improvements to backward precondition extraction:

1. **Equality conditions (= ?param @obj)**: When a behavior branches on parameter equality like (= ?tool @axe), we now extract this as a location constraint @axe:location = @player (the object must be held/accessible to be passed as argument).

2. **?self resolution in quasiquotes**: Effect detection in quasiquoted lists like `((set ?self :rmung true) ...) now resolves ?self to the actual object name using _resolve_object_ref(). Previously only @object symbols were recognized.

3. **runtime:take/drop preconditions**: Added special handling for these synthetic behaviors:
   - runtime:take on @obj requires @obj:takeable = True
   - runtime:drop on @obj requires @obj:location = @player (circular - can only drop what you hold)

Result: LH constraint hierarchy grew from 14 to 26 constraints, now including axe acquisition, glove acquisition, emergency cabinet breaking, and maintenance man defeat chains.
