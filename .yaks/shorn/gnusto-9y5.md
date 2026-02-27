---
id: gnusto-9y5
title: Deprecate and remove flag operations
type: task
priority: 3
created: '2026-01-17T23:59:21.496042-05:00'
updated: '2026-02-08T19:07:11.073546Z'
depends_on:
- gnusto-aa1
- gnusto-oav
---

After migration is complete, remove transitional fallbacks:

- Remove has-flag predicate (use property access)
- Remove set-flag effect (use set)
- Remove clear-flag effect (use set to false)
- Remove :flags syntax from parser
- Clean up any remaining flag-related code

This is the final cleanup task - only do after all game code is migrated.
