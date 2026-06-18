# Frotz: State-Space Analysis for Grue Games

Frotz is a static analysis toolkit for verifying winnability and detecting soft-locks
in Grue interactive fiction games. Named after the light spell from Enchanter, Frotz
"illuminates" the dark passages of game state space.

## Quick Start

```bash
# Check if a state is reachable
frotz reach --to "@key@player" games/testgame

# Full state space analysis with victory path
frotz analyze games/testgame --walkthrough

# Generate DOT graph
frotz reach --to "(= (:location @player) @lair)" games/lurkinghorror --dot reach.dot
```

## Goals

1. **Winnability verification**: Prove that victory is reachable from the initial state
2. **Soft-lock detection**: Find states where victory becomes unreachable
3. **Path extraction**: Generate winning paths for walkthroughs
4. **Design insight**: Understand puzzle dependencies and complexity

## Why Grue Makes This Tractable

Grue's design directly enables static analysis:

- **Pure effects model**: Behaviors return quoted effect lists, not imperative mutations
- **Explicit state**: All state lives in object properties and event queues
- **Deterministic transitions**: Same action in same state = same result
- **Finite action space**: Visible objects × defined verbs × valid arguments

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI (cli.py)                         │
│  frotz reach --to "..." | frotz analyze --walkthrough       │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                  State Space Explorer (explorer.py)         │
│  BFS/DFS with fingerprint-based deduplication               │
└───────────────────────────┬─────────────────────────────────┘
                            │ uses
┌───────────────────────────▼─────────────────────────────────┐
│         Constraint Back-Propagation (backward.py)           │
│  Victory → Achievers → Preconditions → State Refs           │
└───────────────────────────┬─────────────────────────────────┘
                            │ uses
┌───────────────────────────▼─────────────────────────────────┐
│              Effect Analysis (effects.py)                   │
│  modifies, reads, constants for all behaviors               │
└─────────────────────────────────────────────────────────────┘
```

### Core Modules

| Module | Purpose |
|--------|---------|
| `effects.py` | Analyzes which behaviors read/write which state |
| `backward.py` | Builds constraint trees from victory conditions |
| `explorer.py` | BFS/DFS state exploration with fingerprinting |
| `state.py` | State representation and fingerprinting |
| `domains.py` | Value domain inference for abstraction |
| `cli.py` | Command-line interface |

### Deferred Modules

See `src/frotz/deferred/README.md` for modules set aside during core development:
- `relevance.py` - Forward relevance analysis (superseded by constraint refs)
- `clustering.py` - Hierarchical state clustering
- `decompose.py` - Constraint tree decomposition
- `subproblem.py` - Manual subproblem exploration

## Key Algorithms

### 1. Effect Analysis

Scans all behaviors to build:
- `modifies: StateRef → set[BehaviorRef]` - what can modify each state
- `reads: StateRef → set[BehaviorRef]` - what reads each state
- `constants: set[StateRef]` - state that never changes

This is standard def-use analysis adapted for Grue's effect system.

### 2. Constraint Back-Propagation

Works backwards from victory to build a constraint tree:

```
Victory: @power-cord:severed = true
└─ Achiever: @axe:cut-it
    └─ Preconditions:
        ├─ @axe:location = @player
        │   └─ Achiever: runtime:take
        └─ accessible(@power-cord)
```

The collected state refs form the **minimal fingerprint** for exploration.

See [design/constraint-backprop.md](design/constraint-backprop.md) for details.

### 3. State Space Exploration

BFS exploration with:
- **Fingerprinting**: States with identical tracked values are equivalent
- **Victory detection**: Check victory conditions on each state
- **Path tracking**: Parent pointers for reconstructing solution paths

### 4. Value Domain Inference

Analyzes expressions to determine minimal value domains:
- If a location is only checked `= @player`, abstract to {held, not-held}
- If checked against finite set, use that set
- Otherwise, full concrete values

See [design/abstract-interpretation.md](design/abstract-interpretation.md) for the theoretical framework.

## CLI Commands

### `frotz reach` - Reachability Query

Check if a target state is reachable:

```bash
# Shorthand syntax
frotz reach --to "@key@player" games/testgame

# Full Grue syntax
frotz reach --to "(= (:location @axe) @player)" games/lurkinghorror

# With DOT output
frotz reach --to "@key@player" games/testgame --dot reach.dot
```

### `frotz analyze` - Full Analysis

Explore full state space:

```bash
# Basic analysis
frotz analyze games/testgame

# Just show victory path
frotz analyze games/testgame --walkthrough

# Fast mode (guided search, may miss solutions)
frotz analyze games/testgame --fast

# Generate state graph
frotz analyze games/testgame --dot states.dot
```

### `frotz render` - Render Manifest + Explosion-Guard Lint

Enumerate every pre-generatable image key from the game's `:render` / `:rdesc`
specs, check on-disk coverage, and run the **explosion-guard lint** that keeps the
scene-variant cross-product bounded by construction:

```bash
# Coverage report + lint
frotz render games/lurkinghorror

# Also print the assembled generation brief for each key
frotz render games/lurkinghorror --briefs

# Emit the manifest + lint as JSON (for an artist or external tooling)
frotz render games/lurkinghorror --json

# Treat missing/orphan assets as failures too (CI gate)
frotz render games/lurkinghorror --strict
```

Each line marks whether the key resolves on disk (`ok` / `MISS`); the summary
reports resolved/missing/orphan counts (use `-v` to list them). The lint enforces
two invariants via abstract interpretation over the `:render` selector:

1. **Codomain ⊆ declared variants** — every variant token a selector can return
   must have a matching `:rdesc` brief.
2. **Locality** — a *room* render may not read foreign object state (the thing
   that makes the cross-product explode); an *object* render may read only its
   own state. Reads of `self` and queues are always allowed.

Exits non-zero on a lint error (or, with `--strict`, on missing/orphan assets).
The manifest builder and lint live in `grue.render`; this is the enumeration
step that feeds `filfre brief` / `filfre fill` (see [`docs/render.md`](render.md)
and [`docs/filfre.md`](filfre.md)).

## State Specification Syntax

Constraints use Grue syntax or shorthand:

| Format | Meaning |
|--------|---------|
| `@obj@room` | `(= (:location @obj) @room)` |
| `@obj@player` | Object held by player |
| `@obj:prop=value` | `(= (:prop @obj) value)` |
| `(= (:location @obj) @room)` | Full Grue syntax |
| `(not ...)` | Negation |
| `(>= (:count @obj) n)` | Numeric comparison |

## Theoretical Background

### The State Explosion Problem

Naive state space: `locations^objects × 2^flags × ...` = astronomically large.

Key insight: Most state is irrelevant for winnability. We reduce via:
1. **Victory-relevant slice**: Only track state that affects victory
2. **Fingerprinting**: Group equivalent states
3. **Domain abstraction**: Use minimal value domains

### References

- Mawhorter & Smith (2021). [Softlock Detection for Super Metroid with CTL](https://dl.acm.org/doi/fullHtml/10.1145/3472538.3472542)
- Gilbert, Ron. [Puzzle Dependency Charts](https://grumpygamer.com/puzzle_dependency_charts/)
- Cousot & Cousot. [Abstract Interpretation](https://www.di.ens.fr/~cousot/AI/IntroAbsInt.html)

## Future Work

See the IF Design Tools epic (gnusto-otr) for planned tools:
- `requires` - Precondition analysis
- `blockers` - Progress blocker detection
- `deadends` - Unwinnable state detection
- `critical` - Required object detection
- `depgraph` - Dependency visualization
- `solutions` - Alternative path finding
- `complexity` - Puzzle metrics
