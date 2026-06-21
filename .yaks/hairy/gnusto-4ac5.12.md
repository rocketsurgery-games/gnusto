---
id: gnusto-4ac5.12
title: Back comic pages by the persisted turn log (not the in-memory stream)
type: feature
priority: 3
created: '2026-06-21T00:10:00Z'
updated: '2026-06-21T00:10:00Z'
depends_on:
- gnusto-dae1
---

Follow-on from gnusto-4ac5.4 (bounded comic pages). The lean .4 slice paginates
the IN-MEMORY block stream (App.svelte `blocks` array). The design intent is for
pages to be a VIEW over the PERSISTED turn log (knowledge graph / journal,
gnusto-dae1) so history survives reloads and very long sessions don't hold the
whole stream in memory.

Scope:
- Swap the pagination SOURCE from the in-memory array to the persisted log; the
  pagination LOGIC (lib/pagination.ts: room-change hard break + budget/turn-snap
  soft break) stays the same — it already operates on an ordered block list.
- Mount only current page +/- neighbor pages (the perf optimization that only
  matters once log-backed; in-memory renders one page cheaply today).
- Frozen panels must render identically on every revisit (deterministic,
  non-destructive view — already the invariant).

Depends on gnusto-dae1 (persisted turn history).
