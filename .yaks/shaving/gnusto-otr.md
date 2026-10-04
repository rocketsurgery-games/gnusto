---
id: gnusto-otr
title: IF Design Tools
type: task
priority: 4
created: '2026-01-25T10:51:31.341008-05:00'
updated: '2026-09-14T03:44:31Z'
needs: human
---

CLI tools for interactive fiction designers to validate game designs, detect soft-locks,
and understand puzzle complexity. Tools operate on partial state specifications using Grue syntax.

## Tier 1 - Core Debugging

### reach - Reachability Query
```bash
grue-tool reach --to "(= (:location @axe) @player)"
grue-tool reach --from "(= (:location @player) @computer-room)" --to "(= (:location @axe) @player)"
```
- Answers: "Can state S1 be reached from S0?"
- Returns: Yes/No + shortest path (action sequence)
- Default --from is initial game state

### requires - Precondition Analysis
```bash
grue-tool requires "(= (:location @axe) @player)"
grue-tool requires "(not (= (:location @maintenance-man) @floor-waxer))"
```
- Answers: "What must be true to achieve this?"
- Returns: Backward constraint tree showing dependencies
- Shows alternative paths, bottlenecks

### blockers - Progress Blocker Detection
```bash
grue-tool blockers --goal "(>= (:count @frob) 2)"
grue-tool blockers --from state.json --goal victory
```
- Answers: "What's preventing progress from here?"
- Returns: Unsatisfied preconditions, missing items, locked paths

## Tier 2 - Soft-Lock Prevention

### deadends - Unwinnable State Detection
```bash
grue-tool deadends --check "(= (:location @axe) @abyss)"
grue-tool deadends --from state.json
```
- Answers: "Is this state unwinnable?"
- Returns: Yes/No + which victory conditions become unreachable

### critical - Required Object Detection
```bash
grue-tool critical --goal victory
grue-tool critical --goal "(= (:location @player) @lair)"
```
- Answers: "Which objects are required (no alternatives)?"
- Helps identify key items vs optional

## Tier 3 - Design Insight

### depgraph - Dependency Visualization
```bash
grue-tool depgraph --goal "(>= (:count @frob) 2)" -o deps.dot
grue-tool depgraph --object @axe
```
- Visualize constraint relationships
- Show critical path, parallel opportunities

### solutions - Alternative Path Finding
```bash
grue-tool solutions --goal victory --max 5
```
- Find multiple winning paths
- Show how they differ

### complexity - Puzzle Metrics
```bash
grue-tool complexity --goal "(= (:rmung @emergency-cabinet) true)"
```
- Metrics: depth (steps), breadth (alternatives), dependencies
- Compare complexity across puzzles

## Implementation Notes

State specifications use Grue syntax:
- Location: `(= (:location @obj) @room)` or shorthand `@obj@room`
- Property: `(= (:prop @obj) value)` or `@obj:prop=value`
- Negation: `(not ...)` or `!=`
- Comparisons: `(>= (:count @obj) n)`

All tools share common flags:
- `--game <dir>` - Game directory (default: current)
- `--verbose` - Show exploration stats
- `--max-states N` - Limit exploration
- `--timeout N` - Time limit in seconds

---
▸ 2026-09-14T03:44:31Z [claude]
SEQUENCING DECISION, surfaced while surveying the herd.

Shearing gnusto-otr.13 (effect-model completeness) silently unblocked five tool yaks whose only dependency was it: gnusto-otr.2 (requires), gnusto-otr.3 (blockers), gnusto-otr.5 (critical), gnusto-otr.6 (depgraph), gnusto-otr.8 (complexity). All five are still hairy at P2/P3 and now surface in 'yaks next', but nothing has been done with them.

All five live on the STATIC BACKWARD path (backward.py), which is a different code path from the forward explorer.py that the kernel restart (gnusto-266.5) supersedes. The design doc commits only to retiring explorer.py and deferred/ -- it says nothing about backward.py. So it is genuinely ambiguous whether these five are:

(1) DURABLE work worth doing now. The backward analyzer is the rigorous static path; it is unblocked; and per the gnusto-otr.12 diagnosis, 'the rigorous design-tool answers the user wants (dependency chart) live on the STATIC BACKWARD path, blocked mainly by A' -- and A is now fixed.

(2) LEGACY the kernel stack should eventually absorb, in which case building five more tools on it is sunk cost.

Why it matters now: option (1) is the only winnability work that is not blocked on the directional-exit question in gnusto-otr.14. If you want a second front while that question sits, this is the queue.

MY READ: (1), but scoped. The backward analyzer answers 'what must be true to achieve X', which the forward kernel does not and structurally will not -- so the two are complementary, not redundant. I would not build all five. I would do gnusto-otr.2 (requires) properly, end to end, and let it prove out whether the backward path holds up before committing to the other four.

Caveat worth your attention: requires slice-1 already shipped in cli.py but was deliberately NOT wired to the reachability core, so today it answers without room-graph knowledge. Finishing it well probably does depend on gnusto-otr.14 after all -- in which case the honest answer may be that the backward tools are less unblocked than the dependency graph claims.
