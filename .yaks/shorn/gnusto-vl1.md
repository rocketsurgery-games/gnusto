---
id: gnusto-vl1
title: Add action-verb and action-direction accessors for :before-action
type: task
priority: 1
created: '2026-01-14T21:26:30.162076-05:00'
updated: '2026-02-08T19:07:10.967152Z'
depends_on:
- gnusto-16a
---

The yuggoth.grue @platform-room uses (action-verb ?action) and (action-direction ?action) in its :before-action handler, but these functions don't exist. Either add these accessor functions, or redesign :before-action to pass verb/target as separate params and update yuggoth.grue. Note: This is blocked by frotzlm-16a.
