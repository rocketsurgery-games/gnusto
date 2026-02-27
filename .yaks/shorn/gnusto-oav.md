---
id: gnusto-oav
title: Update runtime flag checks to use properties
type: task
priority: 2
created: '2026-01-17T23:59:20.927935-05:00'
updated: '2026-02-08T19:07:11.011175Z'
depends_on:
- gnusto-m95
---

Convert runtime.py hardcoded flag checks to property access:

- NDESCBIT → :ndesc or :hidden-from-listing
- INVISIBLE → :invisible
- OPENBIT → :open
- TRANSBIT → :transparent
- SURFACEBIT → :surface
- VEHBIT → :vehicle
- ONBIT → :lit

All checks should use `.get(prop, default)` pattern.
