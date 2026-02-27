---
id: gnusto-8o7
title: Benchmark reduced cfg_range_end
type: task
priority: 2
created: '2026-01-07T23:46:41.235673232-05:00'
updated: '2026-02-08T19:07:11.063125Z'
depends_on:
- gnusto-luk
---

Test reducing cfg_range_end from 1.0 to 0.7-0.8. Per paper, this can reduce inference time with negligible quality impact by skipping CFG in later timesteps.
