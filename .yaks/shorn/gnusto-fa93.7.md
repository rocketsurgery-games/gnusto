---
id: gnusto-fa93.7
title: 'Zork I slice 5: the maze + the thief (deterministic)'
type: task
priority: 2
created: '2026-07-12T17:57:36Z'
updated: '2026-07-12T18:04:21Z'
labels:
- conversion
---

---
▸ 2026-07-12T18:04:21Z
Done (maze + cyclops; thief split to next slice). Added maze.grue (MAZE-1..15 + DEAD-END-1..4 + GRATING-ROOM verbatim topology incl. one-way MAZE-DIODES; skeleton loot bag-of-coins/skeleton-key/rusty-knife + skeleton scenery; @grate deferred; CYCLOPS-ROOM + cyclops [unkillable; :odysseus routs->subdued+magic, feed lunch+water->subdued only; NPC as :via barrier]; @cyclops-wall; STRANGE-PASSAGE; TREASURE-ROOM shell) + maze.test.grue (17 tests). Wired MAGIC-FLAG: house-interior wooden-door gains :magic, :through checks it, living-room west now -> strange-passage. Gotcha: top-level (def X str)+:ldesc ,X fails (unquote only in quasiquote) -> inlined literals. 95 Zork tests, lint clean. REPL-verified cyclops flee + living-room shortcut. Deferred: thief/treasure loot (fa93.8), rusty-knife+skeleton curses, grating open, dynamic living-room desc. Tooling: maze strongly motivates frotz map dump.
