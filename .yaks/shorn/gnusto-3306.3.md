---
id: gnusto-3306.3
title: 'REPL/TUI hook: inspect live event queue + advance N turns'
type: feature
priority: 3
created: '2026-07-11T22:53:30Z'
updated: '2026-07-11T23:45:04Z'
labels:
- testing
- harness
- repl
---

Semi-automated manual probing. Diagnosing the elevator required reading source to see queue state. Add a REPL builtin/command to dump the live event queue with countdowns (e.g. (queues) or a /queue command) and to advance N turns without a player action (e.g. (wait N)). Complements gnusto-0bf7.3 (event names in debug). Makes grue-repl-driven regression probing fast.

---
▸ 2026-07-11T23:45:04Z
Done (473235b). REPL: (queues) dumps the live event queue with countdowns; (wait N)/(advance N) advances N turns running the event loop each turn (WaitResult carries turns). Docstrings + grue-testing skill updated. NOTE: the REPL still labels fired events '[EVENT: event]' (hardcoded event_name) -- that's gnusto-0bf7.3 (event names in debug), left for that yak.
