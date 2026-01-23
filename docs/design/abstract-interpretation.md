# Abstract Interpretation for Grue Winnability Analysis

## Overview

This document describes the design for a principled abstract interpretation framework for analyzing Grue game winnability. The goal is to replace ad-hoc special cases (HeldRef, barrier analysis, etc.) with a unified framework grounded in abstract interpretation theory.

## Problem Statement

**Goal**: Determine if a Grue game is winnable - does there exist a sequence of player actions that reaches a victory state from the initial state?

**Challenge**: The concrete state space is enormous. We need sound abstractions that reduce state space while preserving reachability analysis precision.

**Current Issues**:
- `StateRef = PropertyRef | LocationRef | QueueRef | HeldRef` accumulates special cases
- Barrier analysis is a separate pass rather than emerging from dataflow
- No principled way to determine minimal value domains
- Floor-waxer timing barrier causes state explosion or missed victory paths

## Core Principles

1. **No special-case analyses** - All analysis (barriers, held predicates, etc.) emerges from unified dataflow/abstract interpretation. Builtins are formalized as rules within the framework.

2. **Partial evaluation first** - Reduce Grue expressions by inlining pure functions before analysis. This exposes actual state dependencies explicitly.

3. **Runtime parameters as constrained symbols** - When runtime provides values (like `?from` in barriers), model with domain constraints as part of builtin specification.

4. **Deterministic semantics** - No non-determinism. Random behavior uses tracked seed or enumerates finite outcomes.

5. **Precise value tracking** - Track concrete values; let domain inference determine abstractions. Only abstract when explosion is proven necessary.

## Theoretical Foundation

### Concrete Semantics

A Grue game state is:

```
State = (Locations, Properties, Queue, Turn)

where:
  Locations  : Object → Location           # Where each object is
  Properties : (Object × PropName) → Value # Property values
  Queue      : Event → Option<Countdown>   # Pending events
  Turn       : Nat                         # Current turn number
```

### Abstract Interpretation via State Projection

We abstract by projecting onto tracked state dimensions:

- **Concrete domain C**: P(State) - sets of concrete states
- **Abstract domain A**: Map<StatePath, Value> - tracked dimensions only

**Galois connection**:
```
α(S) = { path → {eval(s, path) | s ∈ S} | path ∈ TrackedPaths }
γ(abstract) = { s | ∀ path ∈ TrackedPaths: eval(s, path) ∈ abstract[path] }
```

### Soundness

Abstraction is sound for reachability when all behavior branching depends only on tracked paths. If a behavior reads an untracked path, we may lose precision (miss valid paths) but remain sound (won't claim false victories).

## Architecture

### Phase 1: Partial Evaluator

A Grue expression reducer that:
- Inlines pure function calls (defn)
- Simplifies conditionals where branches are statically determined
- Propagates constants
- Handles recursion conservatively (depth limit, mark as "complex")

**Output**: Reduced expressions where state dependencies are explicit.

Example:
```grue
; Before
(waxer-next-loc ?loc true)

; After (inlined)
(cond
  ((= ?loc @inf-5) @inf-4)
  ((= ?loc @inf-4) @inf-3)
  ...)
```

### Phase 2: Unified State Model

Replace `StateRef` variants with unified `StatePath`:

```python
@dataclass(frozen=True)
class StatePath:
    """A path into game state."""
    path: str  # e.g., "loc(@key)", "prop(@door,locked)", "queued(event)"
```

**Builtin specifications** define how runtime-provided symbols relate to state:

```python
@dataclass
class BuiltinSpec:
    """Specification for a runtime builtin."""
    name: str
    # Parameters provided by runtime with their domain constraints
    params: dict[str, DomainConstraint]
    # State paths read by this builtin
    reads: Callable[[...], set[StatePath]]
    # State paths written by this builtin
    writes: Callable[[...], set[StatePath]]
```

Example for navigation:
```python
BuiltinSpec(
    name="runtime:go",
    params={
        "?from": DomainConstraint.rooms(),      # Current player room
        "?to": DomainConstraint.rooms(),        # Destination room
        "?via": DomainConstraint.objects(),     # Barrier object if any
    },
    reads=lambda via: barrier_reads(via) if via else set(),
    writes=lambda: {StatePath("loc(@player)")},
)
```

Similarly, runtime functions can have range specifications:
```python
BuiltinFunc(
    name="loc",
    params={"obj": DomainConstraint.objects()},
    returns=DomainConstraint.locations(),  # rooms ∪ objects ∪ {nil}
)
```

### Phase 3: Value Domain Inference

Analyze reduced expressions to determine:

1. **Write domains**: For each StatePath, what values can be written?
   - Scan all writes, collect literal values
   - For variable writes, use conservative approximation

2. **Read patterns**: For each StatePath, how is it compared?
   - `(= (loc @obj) @player)` → equality check against @player
   - `(= (loc @obj) ?from)` → equality check against runtime param
   - `:prop @obj` in boolean context → truthiness check

3. **Minimal domain**: Choose smallest domain preserving comparison semantics
   - If only checked `= @player`, domain is {true, false} (held abstraction)
   - If checked against finite set, domain is that set
   - Otherwise, full concrete domain

### Phase 4: Exploration with Inferred Domains

```python
@dataclass
class AbstractionConfig:
    """Derived automatically from analysis."""
    tracked_paths: set[StatePath]
    domains: dict[StatePath, ValueDomain]

    def fingerprint(self, state: GameState) -> Fingerprint:
        """Project concrete state to abstract fingerprint."""
        ...
```

Explorer uses AbstractionConfig to:
- Generate state fingerprints for deduplication
- Determine which states are equivalent under abstraction

## The Floor-Waxer Case

How this framework handles the motivating example:

1. **Partial evaluation** inlines `waxer-next-loc`, exposing the room values

2. **Effect analysis** on reduced `waxer-moves` event finds:
   - Writes: `loc(@floor-waxer)` with values {inf-1, inf-2, inf-3, inf-4, inf-5}

3. **Barrier analysis** on reduced `@waxer-exit-barrier:through`:
   - Reads: `loc(@floor-waxer)`, compared to `?from`
   - Builtin spec says `?from` ∈ rooms (specifically, player's current room)

4. **Domain inference**:
   - `loc(@floor-waxer)` write domain: 5 rooms
   - `loc(@floor-waxer)` read pattern: equality with room
   - Minimal domain: {inf-1, inf-2, inf-3, inf-4, inf-5} (5 values)

5. **Exploration** tracks `loc(@floor-waxer)` with 5-value domain
   - 5x state multiplier is acceptable
   - Can now distinguish "waxer blocking" vs "waxer elsewhere"
   - Finds victory path through timing-dependent barrier

## Implementation Plan

See beads hierarchy under `frotzlm-abs` epic.

## Open Questions (Deferred)

1. **Subgoal decomposition** - Can we analyze "reach room X" independently? May relate to hierarchical state clustering.

2. **Abstraction refinement** - If exploration fails, how do we detect over-abstraction vs actual unwinnability?

3. **Compositional analysis** - Can we analyze behaviors in isolation and compose results?

## References

- Cousot & Cousot, "Abstract Interpretation: A Unified Lattice Model" (POPL 1977)
- [Abstract Interpretation in a Nutshell](https://www.di.ens.fr/~cousot/AI/IntroAbsInt.html)
- [Wisconsin CS704 Notes on Abstract Interpretation](https://pages.cs.wisc.edu/~horwitz/CS704-NOTES/10.ABSTRACT-INTERPRETATION.html)
- [Dataflow Analysis Lattice Theory](https://people.cs.vt.edu/ryder/516/sp06/lectures/DataflowAnalysis-1Feb5.pdf)
