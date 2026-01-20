# Frotz: State-Space Analysis for Grue Games

Frotz is a static analysis system for verifying winnability and detecting soft-locks
in Grue interactive fiction games. Named after the light spell from Enchanter, Frotz
"illuminates" the dark passages of game state space.

## Goals

1. **Winnability verification**: Prove that victory is reachable from the initial state
2. **Soft-lock detection**: Find states where victory becomes unreachable
3. **Invariant checking**: Verify that game invariants hold in all reachable states
4. **Path extraction**: Generate winning paths and puzzle dependency graphs

## Theoretical Foundation

### Why Grue Makes This Tractable

Grue's design choices directly enable static analysis:

- **Pure effects model**: Behaviors return quoted effect lists, not imperative mutations
- **Explicit state**: All state lives in object properties and event queues
- **Deterministic transitions**: Same action in same state = same result
- **Finite action space**: Visible objects × defined verbs × valid arguments

### The State Explosion Problem

Naive state space: `locations^objects × 2^flags × ...` = astronomically large.

However, most of this space is irrelevant:
- Most properties never change (room descriptions, object flags)
- Most property combinations never occur together
- Many states are equivalent for winnability purposes

### Key Techniques

#### 1. Def-Use Analysis (What Can Change?)

Standard compiler technique: identify which statements can modify which variables.

For Grue:
- Scan all behaviors and effects for `(set @obj :prop ...)` and `(move @obj ...)`
- Build map: `property → {behaviors that can modify it}`
- Properties with empty modifier set are **statically constant**

Reference: [Reaching Definitions](https://en.wikipedia.org/wiki/Reaching_definition)

#### 2. Victory-Relevant Slice (What Matters?)

Work backwards from victory condition:

```
victory condition
    ↓ depends on
properties that must be true
    ↓ set by
behaviors that modify those properties
    ↓ require
preconditions (other properties)
    ↓ transitively...
puzzle-relevant property set
```

Everything outside this slice can be abstracted away.

Reference: [Program Slicing](https://en.wikipedia.org/wiki/Program_slicing)

#### 3. Bisimulation Quotient (Equivalence Classes)

Two states are **bisimilar** if:
1. Same values for puzzle-relevant properties
2. Same available actions
3. Every action leads to bisimilar successor states

The quotient automaton groups equivalent states, often exponentially smaller.

> "The reduced state space consists of representatives of the equivalence classes...
> Starting with the initial partition, in which all states are equivalent, the
> current partition is refined until states can no longer be distinguished."

Reference: [Multi-core symbolic bisimulation minimisation](https://link.springer.com/article/10.1007/s10009-017-0468-z)

#### 4. Abstract Interpretation (Automatic Invariants)

Framework for computing sound over-approximations:

1. Define abstract domain (what "shape" of invariants)
2. Define abstract transformers (how effects transform abstract state)
3. Iterate to fixed point (over-approximates all reachable states)

Reference: [Abstract Interpretation in a Nutshell](https://www.di.ens.fr/~cousot/AI/IntroAbsInt.html)

### CTL for Property Specification

Computation Tree Logic expresses temporal properties:

- `AG(EF(victory))` - "From all states, victory is eventually reachable" (no soft-locks)
- `EF(victory)` - "Victory is reachable from initial state" (winnable)
- `AG(¬defeat ∨ EF(victory))` - "Defeat only when victory was impossible"

Reference: [Softlock Detection for Super Metroid with CTL](https://dl.acm.org/doi/fullHtml/10.1145/3472538.3472542)

## Implementation Plan

### Phase 1: Effect Analysis

Scan world definitions and build:
- `modifies: property → set[behavior]` - which behaviors can modify each property
- `reads: property → set[behavior]` - which behaviors depend on each property
- `constants: set[property]` - properties that never change

This gives us the "def" side of def-use analysis.

### Phase 2: Relevance Analysis

Starting from victory/defeat conditions:
- Identify directly referenced properties
- Backward slice through behaviors to find transitive dependencies
- Result: minimal set of puzzle-relevant properties

### Phase 3: State Space Exploration

BFS/DFS with quotient construction:
- State = values of puzzle-relevant properties only
- Hash states for visited-set membership
- On visit: check victory/defeat conditions
- Track parent pointers for path reconstruction

### Phase 4: Output Generation

- **Winnability verdict**: yes/no with proof
- **Dead-end states**: counterexample traces showing how to reach them
- **Winning path**: shortest sequence of actions to victory
- **Puzzle dependency graph**: derived from state space structure

## Open Questions

### Numeric Properties

If a counter can be 0..1000, that's 1000 abstract states. Options:
- Abstract to intervals based on threshold checks: `[0..5], [6..∞]`
- Require bounded integers in language
- Widening operators from abstract interpretation

### Event Queue Complexity

Events with countdowns add temporal dimension. May need:
- Bounded countdown abstraction
- Separate analysis for timed vs untimed properties

### NPC State Machines

NPCs often have internal state (conversation progress, help stages).
Need to ensure these are captured in puzzle-relevant slice.

## References

### Directly Relevant

- Mawhorter & Smith (2021). [Softlock Detection for Super Metroid with CTL](https://dl.acm.org/doi/fullHtml/10.1145/3472538.3472542). FDG '21.
- Gilbert, Ron. [Puzzle Dependency Charts](https://grumpygamer.com/puzzle_dependency_charts/). Grumpy Gamer.

### Model Checking & State Space

- Clarke et al. [Model Checking and the State Explosion Problem](https://link.springer.com/chapter/10.1007/978-3-642-35746-6_1).
- [Counterexample-Guided Abstraction Refinement (CEGAR)](https://link.springer.com/chapter/10.1007/10722167_15).
- [Bisimulation minimisation](https://link.springer.com/article/10.1007/s10009-017-0468-z).

### Program Analysis

- [Reaching Definitions](https://en.wikipedia.org/wiki/Reaching_definition) - Wikipedia.
- [Data-flow Analysis](https://en.wikipedia.org/wiki/Data-flow_analysis) - Wikipedia.
- Cousot & Cousot. [Abstract Interpretation](https://www.di.ens.fr/~cousot/AI/IntroAbsInt.html).

### Formal Verification Tools

- [TLA+ Examples](https://github.com/tlaplus/Examples) - specification patterns.
- [Crossing the River with TLA+](https://surfingcomplexity.blog/2014/06/04/crossing-the-river-with-tla/) - puzzle solving approach.
