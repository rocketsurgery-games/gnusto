---
id: gnusto-1w2
title: Structured output effects (narrate, say)
type: task
priority: 2
created: '2026-01-25T17:02:48.692152-05:00'
updated: '2026-02-08T19:07:10.992831Z'
labels:
- lang
---

Add structured output effects to enable richer UI rendering (speech bubbles, graphic novel style, etc.)

## Design

**Output effects (player-facing content):**
- `(narrate "text")` - general narrative, no entity required
- `(say @speaker "text")` - dialogue, speaker required

**Outcome markers (explanatory metadata):**
- `(success "reason")` - action succeeded, reason explains why (for LLM/debugging)
- `(blocked "reason")` - action blocked, reason explains why (for LLM/debugging)

**Not needed:**
- `(describe ...)` - descriptions stay as properties (:description, :fdesc, etc.)
- `(blocked :keyword)` - remove keyword reasons, use text instead (LLM interprets these)

## Example

```scheme
:ask (fn (?topic)
  (match ?topic
    (@master-key
      `((narrate "The hacker pulls out a keyring on a chain.")
        (say @hacker "I've collected a lot of keys over the years.")
        (say @hacker "This one's a master key.")
        (success "hacker shared master key info")))
    (_
      `((say @hacker "I don't know about that.")
        (blocked "hacker doesn't know about topic")))))
```

## Implementation

1. Add `narrate` and `say` as recognized effect types in the runtime
2. Change `(blocked :keyword)` to `(blocked "text")` throughout
3. Update effect processing to collect output effects
4. Update UI/REPL to render structured output appropriately
5. Update existing behaviors to use the new system
