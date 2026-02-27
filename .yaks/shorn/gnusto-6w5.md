---
id: gnusto-6w5
title: 'Pure effects system: enforce declarative effects for static analysis'
type: task
priority: 1
created: '2026-01-16T11:26:33.37785-05:00'
updated: '2026-02-08T19:07:10.96389Z'
---

Implement a "monad-lite" effects system that enables static state analysis by enforcing purity in game logic.

**Core principle:** Game logic is pure. All state mutations are declared as data in :effects, never executed directly.

**Architecture:**
- PURE GAME LOGIC: Behaviors return Outcome with declared effects, never mutate directly
- RUNTIME: Applies declared effects to state (this is where mutation happens)

**Implementation tasks:**
1. Enforce purity in behaviors - lint/error if (move!) etc. appear outside :effects
2. Effect descriptors as data - (move! @x @y) in :effects constructs data, doesn't execute
3. Clarify (do) boundary - runtime primitive, not available in game logic
4. Allow defn to return effect lists - pure functions can construct effect descriptors
5. Test :setup remains a "cheat" - explicitly bypasses purity for test convenience

**Enables:** State-space exploration, winnability analysis, soft-lock detection, invariant checking.

**Key insight:** Effects as inspectable data means we can reason about state transitions without executing them.
