---
id: gnusto-16a
title: Movement (go) skips room :before-action check
type: bug
priority: 1
created: '2026-01-14T21:26:23.7097-05:00'
updated: '2026-02-08T19:07:10.967742Z'
---

The runtime do() method handles 'go' verbs specially (lines 659-666) and returns early without calling _check_room_before_action(). This means rooms cannot intercept movement using :before-action behaviors. Required for yuggoth.grue @platform-room to block player movement.
