---
id: gnusto-1e9a
title: 'gnusto: no save/restore or seed, so LLM playthroughs can''t resume (blocks
  deep walkthrough iteration)'
type: task
priority: 3
created: '2026-07-12T01:36:26Z'
updated: '2026-07-12T02:36:05Z'
labels:
- harness
---

---
▸ 2026-07-12T02:30:44Z
CORRECTION: save/restore DOES exist (grue/save.py) and IS wired into the gnusto CLI/TUI (/save, /load, /saves via commands.py) and web.py. Verified round-trip: /save then /load in a fresh session restores state ((:powered @pc) => True). Real remaining work: (1) wire save/load/saves into grue-repl for deterministic scripted checkpointing; (2) add save/restore round-trip test coverage.
