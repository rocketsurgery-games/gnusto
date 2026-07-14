---
id: gnusto-0bf7.12
title: 'Parse-only: redundant ''open (already-open) container'' before ''put'' short-circuits
  the deposit'
type: task
priority: 3
created: '2026-07-14T01:40:51Z'
updated: '2026-07-14T01:40:51Z'
labels:
- bug
---

---
▸ 2026-07-14T01:40:51Z
Observed repeatedly during the full Zork playthrough. 'put the X in the trophy case' intermittently comes back 'It's already open' and does NOT deposit: the parse-only agent plans [open container, put X], the open returns already-open (blocked), and the batch short-circuits on that block before the put runs. Workarounds that held: phrase as 'put X INTO Y' (rarely triggers the redundant open), and re-issue the put (the retry lands). Real fix idea: the short-circuit-on-block guard shouldn't abort the turn on a harmless 'already open/closed/done' precondition block when more actions remain; or the agent shouldn't emit a redundant open for an already-open container. Low priority (recoverable), but it's a reliability paper-cut for container deposits.
