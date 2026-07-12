---
id: gnusto-9db5
title: 'Parse-only: bare directional command over-expands into multi-room navigation'
type: task
priority: 3
created: '2026-07-12T01:36:26Z'
updated: '2026-07-12T01:37:27Z'
labels:
- harness
---

---
▸ 2026-07-12T01:36:32Z
Observed: a single 'go south' input expanded into south->down->north->east->south (5 moves) ending at the wrong room; then all subsequent room-specific commands failed not-here. Same class as 0bf7.2 (bare wait over-expands). Fix: a bare directional command is a SINGLE move; only chain moves when the player names a destination (go to the kitchen) or says to continue until somewhere.
