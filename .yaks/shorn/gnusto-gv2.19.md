---
id: gnusto-gv2.19
title: Track gating state (e.g., floor-waxer position) for reachability
type: task
priority: 2
created: '2026-01-24T00:36:16.260925-05:00'
updated: '2026-02-08T19:07:10.997349Z'
---

State abstraction collapses reachable/unreachable states when we don't track objects that gate navigation. Example: floor-waxer position determines corridor accessibility, but isn't directly victory-relevant. Need mechanism to identify and include such gating state in exploration fingerprints.
