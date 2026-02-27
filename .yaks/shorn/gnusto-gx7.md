---
id: gnusto-gx7
title: State-ref constraints for complex games
type: task
priority: 3
created: '2026-01-22T12:43:38.057055-05:00'
updated: '2026-02-08T19:07:11.07058Z'
---

## Status: DEFERRED
Backward static analysis now works with conservative fallbacks. This alternative approach is kept as a fallback if we encounter games where backward analysis truly fails.

## Context
When analyzing LH, backward analysis originally only found 3 constraints because it couldn't trace through complex mechanics.

## Resolution
The issues were fixed in frotzlm-6ca and related tasks:
- Function inlining now works
- Event queue preconditions implemented
- Cond skip condition accumulation added
- Conservative fallbacks for dynamic values

LH now has a meaningful constraint hierarchy with depth 0→1→2.

## Why Keep This Task?
The state-ref approach could still be valuable as:
1. **Fallback** for games with truly intractable static analysis
2. **Complementary** - use backward constraints where available, state-ref for gaps
3. **Validation** - compare constraint sets to find static analysis gaps

## Trade-offs (Original)
**Pros:**
- Works regardless of game mechanics complexity
- Better clustering/region detection

**Cons:**
- Loses semantic relationship to victory
- Can't use constraints to guide exploration priority
- Would need alternative exploration strategy

## Depends On
Only revisit if backward analysis proves insufficient for real games.
