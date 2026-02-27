---
id: gnusto-315
title: Improve backward analysis for event-driven games
type: task
priority: 1
created: '2026-01-22T12:43:52.448185-05:00'
updated: '2026-02-08T19:07:10.957526Z'
---

## Problem
Backward static analysis fails for LH because it can't trace
  through complex mechanics:

### Gap 1: Effect Analysis
- Dynamic moves like
  `(move @frob ,(loc @player))` not captured
- Effects inside helper functions (defn) not associated with behaviors
- Result: `@frob:location` shows 0 modifiers
  
### Gap 2: Backward Tracing
- Can't follow function calls to find preconditions
- Can't trace event queue relationships:
- `plug-power-line` calls `(queue frob-appears-1)`
- `frob-appears:on_turn` does `(set @frob :count ...)`
- Need to connect: behavior u2192 queue u2192 event u2192 effect
- Can't handle quasiquote conditional structures

## Investigation Areas

### 1. Event Queue Tracking
The key insight:
  `(queue event-name N)` is effectively a precondition for `event-name:on_turn`.
  
Could we:
- Track which behaviors call `(queue X ...)`
- Treat those as "achievers" for event X's effects
- Extract preconditions from those behaviors instead

### 2. Function Inlining
For `defn` helpers like `plug-power-line`:
- Could inline function bodies during effect analysis
- Or track which behaviors call which functions

### 3. Quasiquote Handling
The pattern `(cond (test1 `((effect1))) (test2 `((effect2))))` is common.
- Each branch's effects are conditional on the test
- Need to extract both the effects AND the conditions

## Acceptance Criteria
- [ ] Backward analysis finds preconditions for `@frob:count >= 2`
- [ ] Preconditions include: gloves worn, boots worn, etc.
- [ ] Constraint hierarchy has meaningful depth for LH"
