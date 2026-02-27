---
id: gnusto-870.5
title: Remove globals system after migration
type: task
priority: 3
created: '2026-01-18T15:47:55.696613-05:00'
updated: '2026-02-08T19:07:11.072742Z'
depends_on:
- gnusto-870.2
- gnusto-870.3
---

After score/moves are migrated to @player properties:
- Remove state.globals dict from GameState
- Remove get_global/set_global from WorldState protocol
- Remove set!/inc!/dec! effects that use globals (keep inc/dec but make them work on properties)
- Update or remove tests that use globals
- Clean up any remaining references in repl.py, harness.py, dsl.py
