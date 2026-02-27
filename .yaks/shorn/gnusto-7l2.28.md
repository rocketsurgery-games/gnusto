---
id: gnusto-7l2.28
title: Clean up stale comment in elevator.grue
type: task
priority: 2
created: '2026-01-14T14:11:46.489867-05:00'
updated: '2026-02-08T19:07:11.027529Z'
labels:
- lh
---

elevator.grue line 237-238 has a stale comment from before we fixed lexical environments:

```scheme
; Generic "floor buttons" object for examining all at once
; Note: Uses functional accumulation since set! doesn't work on let-bound locals
; (substitution replaces ?glowing with its value, making (set! VALUE ...) invalid)
```

This comment is now incorrect - we have proper lexical environments.
The code style (chained cons) could also be simplified with keep/for now.
