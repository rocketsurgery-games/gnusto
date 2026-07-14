# Reachability quotient: collapsing "positioning" state

## The problem

Frotz's forward explorer suffers a state explosion (yak `gnusto-otr.14`, "defect
B") and its backward analyzer dead-ends on movement (a `requires` query bottoms
out at `@player:location = @living-room [UNACHIEVABLE]`, because the effect model
has no `runtime:go` modifier for player location).

Both symptoms have one root cause: **player location is tracked as a concrete
value** (one of ~110 rooms). The player wandering the map generates a huge number
of states that are *puzzle-identical* — same inventory, same flags, same
irreversible progress — differing only in where the avatar is standing. Tracking
that concretely is the explosion; the backward analyzer's failure to model it is
the dead-end.

The fix is not "track more state" (that makes the explosion worse). It is to
**quotient it away**: recognize that free movement is a reversible, side-effect-
local operator and collapse the states it relates.

## The general principle (why movement isn't special)

A Grue game is a labeled transition system (LTS): states `S`, actions, and a
transition relation. The winnability question is reachability of a goal region in
`S`. Movement is just a *subset* of the transitions with two properties that make
it collapsible:

1. **Reversibility.** `go(A→B)` has an inverse `go(B→A)`. Reversible transitions
   generate an *equivalence relation* on states; quotienting by it is sound for
   reachability (you can always undo, so which representative you're at doesn't
   change what's ultimately reachable). This is a **bisimulation quotient**
   (Milner; Park 1981): the collapsed states are bisimilar.

2. **Independence / commutativity.** Moving doesn't affect (and isn't affected
   by) most other state, so it commutes with other actions. Exploring one
   interleaving represents all of them — this is **partial-order reduction**
   (Godefroid 1994 persistent sets; Valmari 1990 stubborn sets; Peled 1993 ample
   sets; Baier & Katoen, *Principles of Model Checking*, 2008).

Your intuition is correct: *the same collapse applies to any operator that is
reversible and independent*, not just player movement — object placement among
reachable containers, opening/closing a re-closable door, an NPC pacing a beat.
So the design target is a **reversible-closure quotient** with movement as the
first and simplest instance.

### The two-level decomposition

Partition the operators:

- **Reversible + local** ("positioning"): movement, take/drop, open/close, …
  These generate the equivalence. Collapse each equivalence class to one
  representative — or, equivalently, track only the *closure* (the set of
  positioning-configurations freely reachable) rather than a point.
- **Irreversible** ("progress"): kill the troll, burn the boat, cross a one-way
  chasm, consume an item, flip a one-shot flag. These are the *real* edges of the
  quotient graph.

Winnability then lives on the (dramatically smaller) **progress graph**: nodes
are assignments of irreversible state; an irreversible edge is enabled iff its
precondition is satisfiable within some positioning-configuration reachable in the
current class. This is hierarchical/abstraction-refinement reachability (cf.
CEGAR, Clarke et al.).

## Soundness conditions (investigate before trusting)

The quotient is sound **only** where these hold. When in doubt, classify an
operator as *irreversible* — over-approximating "reversible" is unsound (it can
merge states that aren't actually interchangeable and hide a real dead-end);
under-approximating merely forfeits some collapse.

1. **Reversibility is partial and state-dependent.** `go` is not globally
   reversible: the chasm and the trap-door-slam are one-way. Collapse only
   **strongly-connected components** of the (currently-passable) movement graph;
   one-way exits stay real edges *between* regions. (Take/drop is reversible only
   if you can return to the drop spot — reversibility itself depends on movement
   reachability, hence on gate state.)

2. **No per-move side effects.** Collapsing assumes moving changes only position.
   An exit whose `:on-enter` mutates world state, or that triggers an event, is
   not free and must stay a real edge.

3. **Hazards / darkness.** A dark room is traversable-but-lethal without a carried
   light. Reachability therefore carries a **light bit** (a lit `:lightable` in
   inventory acts as a gate); otherwise the closure would "reach" rooms that in
   fact kill you.

4. **Gate-dependence.** The region structure is a function of the irreversible
   ("gate") state: killing the troll or opening the grating *merges* regions. The
   quotient must be **parameterized by the gate vector** and recomputed when a
   gate flips. Treating regions as static is the classic way this goes silently
   unsound.

5. **Independence can fail.** Zork has a **carrying capacity** — you cannot hold
   everything — so "take X" is not always independent of "take Y". Inventory-
   limited take/drop is *not* freely collapsible; only movement (and unconstrained
   positioning) is, for now.

## What we build first: the gated room-graph reachability core

`src/frotz/reachability.py` implements the movement instance, as a shared
primitive with three consumers:

| Consumer | Query | Direction |
|----------|-------|-----------|
| `requires` / `depgraph` | required (dominating) barriers between start and a target room | backward |
| `map` connectivity | rooms reachable from here under current gates | forward |
| explorer region abstraction (`otr.14`) | SCC quotient of the movement graph | fingerprint |

Core operations (all over the room graph built from `room.exits`, edges carrying
an optional `:via` barrier; message-only `:blocked` exits and dangling `:to` are
excluded):

- **`reachable_rooms(start, is_open)`** — forward BFS; an edge is traversable when
  its gate predicate says so. Over-approximate (unknown gate ⇒ passable) for
  sound *deadend* use: a room absent from the set is provably unreachable.
- **`required_barriers(start, target)`** — the barriers that lie on *every* path
  (remove a barrier's edges ⇒ is `target` still reachable? if not, it is
  required). A required barrier is a genuine necessary precondition; this is the
  sound backward answer, and it's purely topological (independent of gate truth).
- **`sccs(is_open)`** — Tarjan SCCs over currently-passable reversible edges: the
  region quotient used to abstract player location in the explorer.

Backward integration: `BackwardAnalyzer._expand_node` special-cases a
player-location constraint `= R` — if `R` is unreachable in the room graph it is
genuinely constant; otherwise it yields a `runtime:go` achiever whose
preconditions are the *passability constraints of the required barriers* (e.g.
`@troll:dead = True`), extracted from each barrier's `:through` behavior. Those
recurse through the normal analyzer, so navigation and puzzle steps interleave
correctly (reach R ⇒ pass the troll ⇒ kill it ⇒ hold the sword ⇒ reach the sword
room ⇒ …).

## Known gaps / follow-ups

- **Darkness as a dependency.** The core carries a light bit for the *forward*
  query, but the backward integration does not yet emit "player has a light
  source" as a dependency of reaching a dark room (it's an existential over light
  objects). Tracked for a refinement pass.
- **Barrier passability disjunctions.** We conjoin a barrier's "must be true"
  conditions (matching `_extract_go_preconditions`); a barrier with genuinely
  alternative pass conditions is over-constrained (conservative for `requires`).
- **Generalizing beyond movement.** Object-placement / door / NPC quotients reuse
  the same machinery but need per-operator reversibility + independence checks
  (condition 5). The effect model (now complete — `frotz.effects`) gives the
  read/write footprints to decide independence statically; see `gnusto-zbg`.

## References

- Godefroid, P. (1994). *Partial-Order Methods for the Verification of Concurrent
  Systems* (persistent sets).
- Valmari, A. (1990). *Stubborn sets for reduced state space generation.*
- Peled, D. (1993). *All from One, One for All: Model Checking Using
  Representatives* (ample sets).
- Milner, R. (1989); Park, D. (1981) — bisimulation.
- Baier, C. & Katoen, J-P. (2008). *Principles of Model Checking.*
- Clarke, E. et al. — CEGAR / abstraction refinement.
- Mawhorter & Smith (2021). *Softlock Detection for Super Metroid with CTL.*
