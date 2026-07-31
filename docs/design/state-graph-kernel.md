# State-graph analysis: a first-principles kernel

This is a ground-up restart of winnability / reachability analysis (superseding
the tangle in `explorer.py` and the deferred experiments in
`src/frotz/deferred/`). The strategy: define a tiny, obviously-correct **reference
kernel**, then grow scope only by adding abstraction layers that are each
*provably sound* against that kernel. We control state-space explosion by
construction, one proven layer at a time, rather than retrofitting graph theory
onto a big explorer.

## 1. The formal object

A game is a deterministic labeled transition system `(S, A, →, s₀, φ)`:

- **S** — concrete states: a total assignment to every state variable (each
  object's location and properties, and every event-queue countdown).
- **A** — actions: `(target, verb, args)` the player/engine can invoke.
- **→** — the transition function `step: S × A → S ∪ {⊥}`, given by the runtime's
  *pure* effect interpreter (dispatch behavior → apply its effect list).
  Deterministic, because effects are pure and randomness has been removed.
- **s₀** — the initial state (`runtime.reset()`).
- **φ** — the goal predicate (world victory, or a supplied target).

Winnability = "is some φ-state reachable from s₀ under →?". Everything downstream
is an *approximation* of this, and *correctness = soundness against this
definition*.

## 2. The kernel (`src/frotz/kernel.py`)

A concrete BFS over the reachable graph, states as exact value-tuples. It is the
**oracle**, not a production tool:

- `fingerprint(rt)` — the concrete state as a hashable frozenset. Dedup is exact
  *identity*, never a lossy projection.
- `enumerate_actions(rt)` — a sound *superset* of available actions (completeness
  obligation: never omit an action that could succeed; spurious ones just block).
  Behavior arguments are the cartesian product of each parameter's candidate pool
  — in-scope objects for entity params, source-derived literals for value params
  (passwords, combinations), the union when a param is untyped. This makes
  multi-arg and value-arg behaviors (the PC login flow) enumerable. The one
  residual gap is a value known only by *foreknowledge* (never a literal in
  source — e.g. a doc-check copy-protection password), modelled properly by the
  hidden-knowledge approach (gnusto-266.5.4).
- `step(rt, snapshot, action)` — pure successor via `GameState.copy()` +
  `runtime.do`.
- `explore(world, goal)` — BFS to a fixpoint or `max_states` (`hit_limit` is the
  honest "this game is beyond the concrete kernel" signal).

Because S is finite and → deterministic, `explore` is **sound and complete** for
the concrete semantics — the definition every abstraction must preserve.

## 3. Two lessons the kernel taught us immediately

Building the kernel and running it surfaced two things worth banking:

1. **"Fully concrete" isn't even finite.** The engine writes a **move counter**
   (`@player:moves`) on every successful action, so the raw state space is
   *infinite* (the counter grows without bound). The very first, obviously-sound
   reduction is therefore **cone-of-influence projection**: drop variables that
   no behavior guard and no goal reads. `kernel.BOOKKEEPING_PROPS` is the
   degenerate hand-coded case (moves, score); the general computed version is the
   first real abstraction layer (§4.1).

2. **Permissive actions manufacture explosion.** Allowing `put X` into arbitrary
   objects (not just containers/surfaces) blew a 2-room game past 100 000 states
   with bogus nesting. The action model must match real semantics: `put` targets
   containers/surfaces only — the same footprint the effect model uses.

Empirical scale, post-fix: **Mini = 20 states (instant); Zork = hits a 2 000-state
cap in ~42 s without finishing.** So: perfect oracle for tiny games, hopeless on
real ones — precisely the case for the layers below.

## 4. The abstraction stack (each a sound transformer over the kernel)

Every layer is a state-abstraction with an explicit soundness theorem and is
**differential-tested against the kernel**: on every game small enough to
enumerate concretely, the abstract analysis must agree with the kernel on
goal-reachability. This is how we "prove as we go" — proofs for the abstraction
functions, plus exhaustive metamorphic testing on a corpus of tiny games.

### 4.1 Cone-of-influence projection  (the "tracked variables" done right)
Drop every variable not (transitively) read by a transition guard or φ. **Sound**
because untracked variables cannot influence any tracked transition or the goal —
a bisimulation w.r.t. the tracked set. This is the rigorous version of the old
"tracked refs", and the fix for where the previous explorer went wrong (it
projected *too* aggressively and collapsed non-bisimilar states → false NO). The
effect model's `reads`/`modifies` (now complete) gives the exact dependency
relation to compute it. Related yaks: gnusto-266.3, gnusto-gv2.14.

### 4.2 Value-domain abstraction  (finite domains for wide/numeric state)
Map large/infinite value domains to small abstract ones via a Galois connection
(α/γ) with an over-approximating abstract `step`. Booleans and small enums are
already finite; the open work is **numeric intervals** for counters
(`inc`/`dec`) — e.g. a countdown abstracted to `{0, >0}` or an interval lattice.
`domains.py` already infers read-patterns; this layer consumes them. Related
yaks: gnusto-266.3, gnusto-l8k (queue countdowns), gnusto-81s (contained
location), the numeric-interval work.

### 4.3 Reversibility / independence quotient  (the explosion killer)
Collapse states related by reversible, independent operators — movement first
(the room-reachability quotient, `reachability.py`), then object placement, doors,
NPC positioning. **Sound** as a bisimulation quotient / partial-order reduction,
subject to the conditions in `reachability-quotient.md` (reversibility ⇒ SCCs
only; no per-move side effects; hazards/darkness; gate-parameterized regions;
independence can fail under inventory limits). Related yak: gnusto-otr.14.

### 4.4 Residual search
Whatever structure is left after 4.1–4.3 — the genuinely irreducible,
non-monotone puzzle core — is explored with the concrete kernel itself. If the
layers did their job, this residual is small.

## 5. Correctness methodology

- **Kernel = spec.** It is simple enough to trust and is asserted on the
  hand-enumerable Mini game (`tests/frotz/test_kernel.py`).
- **Each layer: theorem + differential test.** State and discharge the soundness
  obligation (α/γ, bisimulation, or POR independence), then assert agreement with
  the kernel across a growing corpus of tiny games (a metamorphic-testing
  harness — the natural next artifact).
- **Direction of soundness is explicit per query.** Over-approximate reachability
  for deadend/"provably unreachable" claims; under-approximate for "required"
  claims. Never silently mix.

## 6. Status / next

- Done: the kernel + Mini fixture (this doc, `kernel.py`, `mini/`).
- Done: **oracle-honesty pass** (gnusto-266.5.1) — `enumerate_actions` now covers
  multi-argument behaviors (cartesian product) and value arguments (source-
  literal pool, narrowed by param-type annotations), so the sound-superset claim
  actually holds for the LH login flow and combination locks. Residual
  foreknowledge-only values tracked by gnusto-266.5.4.
- Next increment (proposed): the **differential-test harness** (gnusto-266.5.2:
  kernel vs. a layer on a corpus of tiny games, comparison mode A = multi-goal
  reachability), then land **4.1 cone-of-influence projection** as the first
  proven layer, measured against the kernel. A stronger bisimulation check
  (mode B) is deferred to gnusto-266.5.3.
- The old `explorer.py` and `deferred/` stay untouched until the new stack
  reaches parity, then get retired (hard cutover).
