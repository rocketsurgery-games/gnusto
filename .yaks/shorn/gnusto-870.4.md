---
id: gnusto-870.4
title: Update docs/grue.md to remove flag references
type: task
priority: 3
created: '2026-01-18T15:47:50.010087-05:00'
updated: '2026-02-08T19:07:11.07302Z'
---

The grue.md documentation has extensive references to the old flag system:
- has-flag, has-flag?, no-flag?
- set-flag!, clear-flag!
- :flags property on rooms/objects
- room-has-flag?
- UPPERCASE flag names (LOCKED, OPENBIT, etc.)

Update all examples to use property syntax:
- (:locked @door) instead of (has-flag @door LOCKED)
- (set @door :locked true) instead of (set-flag @door LOCKED)
- :properties (:locked true :openable true) instead of :flags (LOCKED OPENABLE)

Also remove the deprecated set! documentation.
