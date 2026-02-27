---
id: gnusto-870
title: Remove legacy flags and globals
type: task
priority: 2
created: '2026-01-18T15:47:17.264291-05:00'
updated: '2026-02-08T19:07:11.009232Z'
---

Aggressive cleanup of legacy flag and global systems that are no longer used or intended to be used.

## Background
We unified flags and properties - flags are now just boolean properties accessed via `:prop` syntax.
Globals like score/moves should be @player properties, not a separate globals dict.

## Scope
1. Remove legacy flag API from runtime.py and expr.py
2. Remove set-flag/clear-flag effects (game uses `(set @obj :prop value)`)
3. Migrate score/moves from globals to @player properties
4. Fix `lit` global usage (should be room property)
5. Update documentation (docs/grue.md has extensive outdated flag references)
6. Update tests to use property syntax

## Files affected
- src/grue/runtime.py - flag functions, globals init
- src/grue/expr.py - WorldState protocol, effect handlers
- src/grue/test/harness.py - globals support
- src/grue/test/dsl.py - has-flag?/no-flag? predicates (already work with properties)
- docs/grue.md - extensive flag documentation
- games/lurkinghorror/globals.grue - `lit` global usage
- tests/test_expr.py - set-flag/clear-flag tests
