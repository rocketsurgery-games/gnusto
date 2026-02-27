---
id: gnusto-6w5.9
title: Support function calls in effect lists that return effects
type: task
priority: 2
created: '2026-01-17T10:04:28.697351-05:00'
updated: '2026-02-08T19:07:11.020868Z'
---

Allow functions to be called from effect lists that themselves return effect lists.

**Problem:** `(success :effects ((heat-microwave-contents)))` calls a function that does mutations. Can't migrate because effect list is data.

**Options:**
1. Have EffectInterpreter recognize function calls and merge returned effects
2. Inline the function logic into effect lists (explosion of code)
3. Support a `(call fn-name args...)` effect that invokes at interpretation time

**Affected:**
- kitchen.grue: heat-microwave-contents
- elevator.grue: pick-elevator-direction, clear-all-buttons-at!
