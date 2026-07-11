---
id: gnusto-3306
title: Test & debug tooling for timed/event-driven mechanics
type: task
priority: 2
created: '2026-07-11T22:52:54Z'
updated: '2026-07-11T22:52:54Z'
labels:
- testing
- runtime
---

Herd for test/debug improvements motivated by the elevator soft-lock (gnusto-f95a.1) slipping past ~30 single-turn unit tests. The gap: tests asserted single-turn post-conditions from hand-built setups; nothing rode multiple turns or ran an event long enough to expose 'fires forever', and no static check flagged the missing dequeue/re-queue.
