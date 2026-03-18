---
id: gnusto-6ba8.3
title: Improve knowledge graph query coverage
type: task
priority: 2
created: '2026-03-02T02:33:21Z'
updated: '2026-03-02T02:35:15Z'
commit: 4c4631b
---

Two gaps in KG queries: (1) history() only searches events, not observations — so history(@entity) returns empty even when recall(@entity) has rich data from Focus/Reveal blocks. (2) Events from Focus/Reveal blocks aren't tagged with entity IDs, so entity-filtered history misses them. Fix both: tag events with entities from narrative blocks, and have history() fall back to recall data when events are empty.
