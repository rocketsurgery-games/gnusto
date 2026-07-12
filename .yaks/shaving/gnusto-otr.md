---
id: gnusto-otr
title: IF Design Tools
type: task
priority: 4
created: '2026-01-25T10:51:31.341008-05:00'
updated: '2026-07-12T19:12:32Z'
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
