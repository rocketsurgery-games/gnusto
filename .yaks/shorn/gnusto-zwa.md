---
id: gnusto-zwa
title: Function inlining in effect analyzer
type: task
priority: 1
created: '2026-01-22T13:01:23.349326-05:00'
updated: '2026-02-08T19:07:10.957274Z'
---

## Problem
Effect analyzer doesn't follow function calls (defn). When a behavior calls a helper function, effects inside that function aren't associated with the behavior.

## Example
In LH, `@high-voltage:plug` calls `(plug-power-line)`:
- `plug-power-line` contains `(queue frob-appears -1)`
- But effect analysis shows `@high-voltage:plug` modifies nothing

## Fix
In `_walk_expr`, detect function calls and inline the function body:

```python
# Function call detection: (function-name args...)
if name in self.world.functions:
    fn = self.world.functions[name]
    self._walk_expr(fn.body)
    for item in items[1:]:
        self._walk_expr(item)
    return
```

## Acceptance Criteria
- [ ] Effect analysis for `@high-voltage:plug` shows it modifies `queue:frob-appears`
- [ ] Backward analysis can trace from `@frob:count` through the event to the plug behavior
