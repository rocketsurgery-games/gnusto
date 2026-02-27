---
id: gnusto-6ca
title: Effect-path precondition extraction
type: task
priority: 1
created: '2026-01-22T13:05:27.590395-05:00'
updated: '2026-02-08T19:07:10.956732Z'
---

## Problem
Current precondition extraction only finds conditions that lead to \`(blocked ...)\`.
But for complex functions like \`plug-power-line\`, the effect we care about (queuing the event) happens in a specific branch that isn't guarded by blocks.

## Example: plug-power-line
```
(cond
  ((not (and (held? @gloves) ...)) \`((success ...)))  ; Branch 1: bad but not blocked
  ((not (:wearable @boots)) (blocked ...))           ; Branch 2: blocked (death)
  ((:rmung @output-cable) '((success ...)))          ; Branch 3: different outcome
  ((not (queued? frob-appears)) \`((queue ...)))      ; Branch 4: THE EFFECT WE WANT
  (true '((success ...))))                           ; Branch 5: fallthrough
```

To reach Branch 4 (which has the effect), we need:
- Branch 1 condition to be FALSE → gloves held and wearable
- Branch 2 condition to be FALSE → boots wearable
- Branch 3 condition to be FALSE → output-cable not rmung
- Branch 4 condition to be TRUE → frob-appears not queued

## Proposed Solution
Instead of only looking for blockers, we need "effect-path analysis":
1. Find which branch produces the effect we care about
2. Extract all conditions that must be true/false to reach that branch
3. This is essentially symbolic execution / path condition collection

## Complexity
This requires knowing WHICH effect we're tracing for. Currently we find all preconditions for a behavior generically, but for this we need:
- "What conditions lead to \`(queue frob-appears)\` specifically?"
- Different effects may have different preconditions in the same behavior

## Alternative
Could track "negative paths" instead - conditions that lead away from the effect:
- Any \`blocked\` → must avoid
- Any branch before our effect → must fail that branch's test
