---
id: gnusto-abm
title: Review runtime-baked flag semantics
type: task
priority: 3
created: '2026-01-17T23:59:21.707216-05:00'
updated: '2026-02-08T19:07:11.078292Z'
---

Future improvement: Consider whether hardcoded runtime behaviors should be declarative.

Currently the runtime has baked-in semantics for:
- :open/:transparent/:surface → container visibility rules
- :vehicle → movement semantics
- :ndesc → room description filtering
- :invisible → visibility checks

Could these be declarative behaviors attached to objects instead of runtime hardcoding?
E.g., object "types" or "traits" that bring behaviors with them.

This is speculative - only pursue if there's a compelling need.
