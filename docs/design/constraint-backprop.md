# Constraint Back-Propagation for Winnability Analysis

This document describes the constraint back-propagation algorithm used in Frotz
for static analysis of Grue games, with the goal of determining winnability
without exhaustive state exploration.

## Overview

**Goal**: Given a game's victory condition, determine what state must be tracked
during exploration to detect progress toward victory, and build a constraint tree
that enables guided search and black hole detection.

**Approach**: Work backwards from terminal conditions (victory/defeat) to find:
1. What state references the terminal condition depends on
2. What behaviors can achieve each required state value
3. What preconditions those behaviors have
4. Recursively expand until reaching initial state or constants

## Core Algorithm

### Phase 1: Effect Analysis

Before back-propagation, we perform forward effect analysis to build:

```
modifies: StateRef -> set[BehaviorRef]   # What can modify each state
modifies_to: StateRef -> BehaviorRef -> set[Value]  # What values each behavior sets
reads: StateRef -> set[BehaviorRef]       # What reads each state (for forward relevance)
constants: set[StateRef]                  # State that never changes
```

**State references** are typed:
- `PropertyRef(object, property)` - e.g., `@door:locked`
- `LocationRef(object)` - e.g., `@key:location`
- `QueueRef(event)` - e.g., `queue:hacker-helps`

**Behavior references** identify where code lives:
- `BehaviorRef(object, verb)` - e.g., `@door:unlock`
- Special: `BehaviorRef("runtime", verb)` - built-in behaviors
- Special: `BehaviorRef("event:name", "on_turn")` - event handlers

### Phase 2: Constraint Extraction

From the victory condition expression, extract constraints:

```grue
(victory
  :when (and (:severed @power-cord)
             (= (loc @stone) @player)))
```

Yields constraints:
- `@power-cord:severed = true`
- `@stone:location = @player`

### Phase 3: Backward Expansion

For each constraint, build a tree by finding achievers:

```
Constraint: @power-cord:severed = true
  └─ Achiever: @axe:cut-it
       └─ Preconditions:
            ├─ @axe:location = @player (held?)
            └─ @power-cord:severed = false (implicit: not already done)
```

**Expansion rules**:
1. If constraint is satisfied in initial state → mark as INITIAL (leaf)
2. If state is never modified → mark as CONSTANT (leaf)
3. Otherwise, find behaviors that:
   - Modify this state ref (from `modifies`)
   - Set it to the target value (from `modifies_to`)
4. For each achiever, extract preconditions and recurse

### Phase 4: State Ref Collection

Collect all state refs from the constraint tree:

```python
def collect_constraint_refs(trees: list[ConstraintTree]) -> set[StateRef]:
    refs = set()
    for tree in trees:
        for constraint in tree.all_nodes.keys():
            refs.add(constraint.ref)
    return refs
```

This gives the **minimal state fingerprint** for exploration—only these refs
matter for detecting progress toward victory.

## Theoretical Properties

### Soundness

The algorithm is **sound** (never claims unwinnable when winnable):
- Conservative fallbacks include behaviors when target values are unknown
- Cycles in constraint graph treated as potentially satisfiable
- Dynamic expressions (computed values) → include all possible achievers

### Completeness

The algorithm is **incomplete** (may claim winnable when unwinnable):
- Cannot detect ordering constraints (A must happen before B)
- Cannot prove constraint trees are unsatisfiable
- May include unreachable achievers

### Black Hole Detection

A state is a **black hole** if no achiever path remains satisfiable:
- All achievers have unsatisfiable preconditions, OR
- A constant constraint doesn't match

```python
def is_satisfiable(tree: ConstraintTree, state: dict) -> bool:
    # Returns True if at least one achiever path exists
    ...
```

## Precondition Extraction Strategies

### Strategy 1: Blocking Conditions

Walk behavior body looking for `(blocked ...)` outcomes:

```grue
(:cut-it (fn (?obj)
  (cond
    ((not (held? ?self))
      (blocked :reason "not-holding"))
    (true
      '((set ?obj :severed true))))))
```

The blocking path `(not (held? ?self))` implies precondition `held? = true`.

### Strategy 2: Effect Path Conditions

Walk behavior body tracking conditions that lead to target effects:

```grue
(:operate (fn ()
  (cond
    ((:powered @machine)
      '((set @target :active true)))
    (true
      (blocked :reason "no-power")))))
```

To achieve `@target:active = true`, we need `@machine:powered = true`.

### Condition Decomposition

Compound conditions are decomposed:

- `(and A B)` → both A and B must hold (conjunction)
- `(not (and A B))` → De Morgan: at least one of (not A), (not B)
  - Returns **multiple alternative paths** for proper OR handling

```python
def _decompose_condition(test, is_negated) -> list[tuple[condition, is_negated]]:
    if is_and_expr(test):
        if is_negated:
            # De Morgan: NOT (A AND B) = (NOT A) OR (NOT B)
            # Each part being false is an alternative
            return [(part, True) for part in and_parts(test)]
        else:
            # A AND B = both must be true
            return [(part, False) for part in and_parts(test)]
    return [(test, is_negated)]
```

## Runtime Special Cases

The Grue runtime implements several behaviors implicitly that require
special-casing in back-propagation:

### 1. Player Movement (`runtime:go`)

**Runtime behavior**: Player movement is handled by:
1. Look up exit in current room's exit table
2. If `:via @barrier` specified, call `@barrier:through`
3. Move player to destination

**Effect analysis models this as**:
```python
player_loc = LocationRef("@player")
analysis.add_modify(player_loc, BehaviorRef("runtime", "go"))
```

**Back-prop handles**:
```python
if behavior.object == "runtime" and behavior.verb == "go":
    # Extract preconditions from all door :through behaviors
    return _extract_go_preconditions()
```

**Gap**: The `:through` behavior's **reads** are tracked by effect analysis,
but back-prop doesn't automatically discover that `@floor-waxer:location` must
be tracked because `@waxer-exit-barrier:through` reads it. See "Navigation
Barrier Analysis" below.

### 2. Taking Objects (`runtime:take`)

**Runtime behavior**: Objects with `:takeable true` can be taken via default
behavior (move object to `@player`).

**Effect analysis models this as**:
```python
for obj with takeable=true:
    analysis.add_modify(LocationRef(obj), BehaviorRef("runtime", "take"), "@player")
```

**Back-prop handles**:
```python
if behavior.object == "runtime" and behavior.verb == "take":
    # Precondition: object must be takeable
    return [[Constraint(PropertyRef(obj, "takeable"), "=", True)]]
```

### 3. Dropping Objects (`runtime:drop`)

**Runtime behavior**: Held objects can be dropped (move to current room).

**Effect analysis models this as**:
```python
analysis.add_modify(LocationRef(obj), BehaviorRef("runtime", "drop"), None)  # Unknown dest
```

**Back-prop handles**:
```python
if behavior.object == "runtime" and behavior.verb == "drop":
    # Precondition: object must be held
    return [[Constraint(LocationRef(obj), "=", "@player")]]
```

### 4. Event Queue Handling

**Runtime behavior**: Events are queued with `(queue event-name countdown)` and
fire when countdown reaches 0.

**Effect analysis**: Tracks `QueueRef(event)` modifications.

**Back-prop handles**:
```python
if behavior.object.startswith("event:"):
    event_name = behavior.object.split(":")[1]
    # Implicit precondition: event must be queued
    return [[Constraint(QueueRef(event_name), "=", True)]]
```

## Navigation Barrier Analysis

Navigation barriers (`:via @barrier` in room exits) can block movement based on
game state. Their `:through` behaviors read arbitrary state to decide whether
to allow passage.

### How It Works

Effect analysis already tracks what `runtime:go` reads from barrier behaviors.
The `collect_navigation_refs()` function extracts these refs for exploration:

```python
def collect_navigation_refs(effects, include_locations=False) -> set[StateRef]:
    """Collect state refs that affect navigation."""
    refs = set()
    runtime_go = BehaviorRef("runtime", "go")
    for state_ref, behaviors in effects.reads.items():
        if runtime_go in behaviors:
            # Skip LocationRefs by default (state explosion)
            if not include_locations and isinstance(state_ref, LocationRef):
                if state_ref.object != "@player":
                    continue
            refs.add(state_ref)
    return refs
```

### Example: Floor Waxer Barrier

`@waxer-exit-barrier:through` in LH reads:
- `(loc @floor-waxer)` - where is the waxer?
- `(loc @maintenance-man)` - is he riding it?
- `(:severed @power-cord)` - has cord been cut?

These are now included in state fingerprinting (PropertyRefs directly, LocationRefs
only if `include_locations=True` to avoid state explosion).

### State Explosion Trade-off

Including LocationRefs (like `@floor-waxer:location`) multiplies the state space
by the number of possible locations (~50 rooms). For LH:
- Without location refs: 22 navigation refs
- With location refs: 25 navigation refs (+3 LocationRefs)

The CLI uses `include_locations=False` by default. For games where mobile object
positions affect navigation critically, set `include_locations=True`.

## Known Gaps and Future Work

### Abstract Object Predicates (gnusto-gv2.14)

**Problem**: Tracking `@object:location` for portable objects creates state
explosion (N objects × M possible locations).

**Observation**: Many constraints only care about **held vs not held**, not
the specific location.

**Solution direction**: Introduce abstract predicate `HeldRef(object)`:
- Models boolean "is player holding this?"
- Dramatically reduces state space (2 values vs M locations)
- Can be computed from `LocationRef` but tracked separately

### Conditional State Reads

**Problem**: Some behaviors read state conditionally—the read only happens
in certain branches.

```grue
(cond
  ((:flag @obj)
    ; reads :other-prop only if :flag is true
    (if (:other-prop @obj2) ...))
  (true ...))
```

**Current state**: Effect analysis records the read unconditionally.

**Impact**: Over-approximates relevant state, but doesn't affect correctness.

### Higher-Order Functions

**Problem**: If functions could take functions as arguments, we'd need flow
analysis to track which function is called.

**Current state**: Grue doesn't support HOF, so this is N/A.

## Implementation Notes

### File Structure

```
src/frotz/
├── effects.py    # Phase 1: Effect analysis
├── backward.py   # Phase 2-4: Constraint back-propagation
├── explorer.py   # State space exploration using constraint refs
└── cli.py        # CLI interface
```

### Key Classes

```python
# effects.py
class EffectAnalysis:
    modifies: dict[StateRef, set[BehaviorRef]]
    modifies_to: dict[StateRef, dict[BehaviorRef, set[Any]]]
    reads: dict[StateRef, set[BehaviorRef]]
    constants: set[StateRef]

# backward.py
class Constraint:
    ref: StateRef
    operator: str  # "=", "!=", ">=", etc.
    value: Any

class Achiever:
    behavior: BehaviorRef
    preconditions: list[Constraint]

class ConstraintNode:
    constraint: Constraint
    achievers: list[Achiever]
    is_initial: bool
    is_constant: bool
    children: dict[Constraint, ConstraintNode]

class ConstraintTree:
    root: ConstraintNode
    all_nodes: dict[Constraint, ConstraintNode]
```

### Function Inlining

User-defined functions are inlined during analysis to find effects/reads
inside them:

```python
if name in self.world.functions:
    fn = self.world.functions[name]
    if name not in self._inlining_stack:  # Cycle detection
        self._inlining_stack.add(name)
        self._walk_expr(fn.body)
        self._inlining_stack.discard(name)
```

### ?self Resolution

Behaviors can reference `?self` for the object they're defined on:

```grue
(object @door
  :behaviors (
    :unlock (fn ()
      (set ?self :locked false))))  ; ?self = @door
```

Both effect analysis and back-prop track `_current_self` during traversal
to resolve `?self` to the concrete object name.

## Example: LH Power Cord Puzzle

**Victory condition** (simplified):
```grue
(victory :when (:severed @power-cord))
```

**Constraint tree**:
```
@power-cord:severed = true
├─ Achiever: @axe:cut-it
│   └─ Preconditions:
│       ├─ @axe:location = @player
│       │   └─ Achiever: runtime:take
│       │       └─ Preconditions:
│       │           ├─ @axe:takeable = true [INITIAL]
│       │           └─ @axe accessible (implicit via runtime)
│       └─ @power-cord accessible (implicit via runtime)
└─ Achiever: @knife:cut-it (if exists)
    └─ ...
```

**Collected state refs**:
- `@power-cord:severed`
- `@axe:location`
- `@axe:takeable`

**Missing** (due to navigation barrier gap):
- `@floor-waxer:location` - needed because `@waxer-exit-barrier:through` blocks
  passage through the corridor when waxer is present

This gap is why exploration gets stuck even though the puzzle is solvable—
the player can't reach the CS basement to get gloves without the waxer state
being tracked.

## References

- `src/frotz/effects.py` - Effect analysis implementation
- `src/frotz/backward.py` - Back-propagation implementation
- `games/lurkinghorror/` - LH game files
- Yaks: gnusto-gv2.13 (navigation barriers), gnusto-gv2.14 (abstract predicates)
