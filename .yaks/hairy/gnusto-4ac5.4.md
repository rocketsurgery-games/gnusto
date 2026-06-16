---
id: gnusto-4ac5.4
title: Bounded comic pages + paged navigation
type: feature
priority: 2
created: '2026-06-16T02:18:06Z'
updated: '2026-06-16T02:18:06Z'
depends_on:
- gnusto-4ac5.1
---

Solve infinite-scroll: bound the stream into navigable comic PAGES that are a VIEW over the existing turn history (no new store).

- Page = a bounded set of panels: target a panel budget per page, but SNAP breaks to natural boundaries (room change first, then turn boundary). An establishing panel always starts a page; overflow within a long room-stay spills to continuation pages.
- Navigation: paged, not infinite scroll. Default = latest page ('now'); page BACKWARD through history; page FORWARD to return to now. (Your 'N before/after' = previous/next page.)
- Back the pages with the persisted turn history (knowledge graph / journal, gnusto-dae1) — pagination is rendering logic, not a parallel data model.
- Perf: mount only current page +/- neighbors; frozen panels render identically on every revisit.
- Open question to settle during impl: does the current room accrete panels into one LIVE page until a scene break commits it (leaning yes), vs every turn committing a page?

Depends on gnusto-4ac5.1.
