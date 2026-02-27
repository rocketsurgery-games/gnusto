---
id: gnusto-gv2.10
title: Track target values in effect analysis
type: task
priority: 3
created: '2026-01-21T18:05:11.70098-05:00'
updated: '2026-02-08T19:07:11.071131Z'
---

Effect analysis currently only tracks WHAT state a behavior modifies, not WHAT VALUE it sets. This causes incorrect achievers:

Example: @cell-door:lock sets locked=True, but it's listed as an achiever for locked=False because we only know it modifies 'locked'.

Fix: Track (set ref value) patterns to distinguish:
- Behaviors that set ref=True vs ref=False
- Behaviors that set ref to a specific value vs a variable

This would eliminate spurious achievers and make the constraint hierarchy more precise.

Low priority - doesn't break anomaly detection, just adds noise to achiever lists.
