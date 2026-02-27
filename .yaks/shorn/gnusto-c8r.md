---
id: gnusto-c8r
title: Profile and optimize explorer performance
type: task
priority: 2
created: '2026-01-23T20:45:00.49509-05:00'
updated: '2026-02-08T19:07:10.997604Z'
---

Explorer runs at ~4 states/second on LH which limits scalability.

Observed: 611 states in 147s (~4.2 states/sec)

Profile to identify:
1. Runtime action enumeration overhead
2. State fingerprint computation cost
3. Deep copy vs. rollback overhead
4. Effect execution time

Possible optimizations:
- Cache action availability per object type
- Incremental fingerprint updates
- Rollback-based state instead of deep copy
- Batch effect execution
