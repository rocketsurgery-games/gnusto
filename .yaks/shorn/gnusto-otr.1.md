---
id: gnusto-otr.1
title: Implement reach tool
type: task
priority: 1
created: '2026-01-25T10:58:31.619472-05:00'
updated: '2026-02-08T19:07:10.954242Z'
---

Implement the `reach` reachability query tool.

## Usage
```bash
grue-tool reach --to "(= (:location @axe) @player)"
grue-tool reach --from "(= (:location @player) @terminal-room)" --to "(= (:location @axe) @player)"
grue-tool reach --to "@axe@player"  # shorthand
```

## Behavior
- `--from`: Starting state constraints (default: initial game state)
- `--to`: Target state constraints (required)
- Returns: Yes/No + shortest action sequence if reachable

## Output Format
```
Reachable: YES
Steps: 12

Path:
  1. go north
  2. take key
  3. unlock door with key
  ...
```

Or:
```
Reachable: NO (explored 5000 states)
Closest approach: 3 constraints satisfied of 4
  Missing: (= (:location @axe) @player)
```

## Implementation
1. Parse Grue constraint syntax into Constraint objects
2. Use existing explorer with target state as goal
3. Track closest approach if unreachable
4. Return action path from exploration graph
