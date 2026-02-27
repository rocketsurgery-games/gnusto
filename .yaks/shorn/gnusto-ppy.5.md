---
id: gnusto-ppy.5
title: Design event queue system for GRUE
type: task
priority: 1
created: '2026-01-11T09:59:44.948304-05:00'
updated: '2026-02-08T19:07:10.974033Z'
---

Implement simple queue flag support for GRUE runtime.

## Scope (Simplified)
Just the predicates and effects needed for behavior conditions - no turn-by-turn event handlers yet.

### Predicates:
- `(queued? EVENT-NAME)` - check if event is active

### Effects:
- `(queue! EVENT-NAME)` - activate event (indefinite)
- `(queue! EVENT-NAME N)` - activate with countdown (for future use)
- `(dequeue! EVENT-NAME)` - deactivate event

### Implementation:
- Add `queues: dict[str, int | None]` to GameState
- Add predicate to ExprEvaluator
- Add effects to EffectExecutor
- Countdown decrement can be deferred

## Use Cases
Terminal room behaviors check:
- `(queued? HACKER-HELPS)` - is hacker helping at terminal?
- `(queued? COMPULSION)` - is player under compulsion?

These are used in behavior conditions to alter responses, not for turn-by-turn processing.

## Out of Scope
- Turn-by-turn event handlers (see frotzlm-ppy.7)
- Automatic stage progression
- Event-triggered effects

## Source
games/lurkinghorror/terminal-room.grue - HACKER and PC behaviors reference queued events
