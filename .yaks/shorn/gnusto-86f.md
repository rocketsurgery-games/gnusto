---
id: gnusto-86f
title: Update ZIL converter for new naming conventions
type: task
priority: 2
created: '2026-01-11T11:59:31.107577-05:00'
updated: '2026-02-08T19:07:11.053823Z'
depends_on:
- gnusto-fnh
- gnusto-5ib
---

Update the ZIL-to-GRUE converter to emit new conventions:

1. **Entity prefix**: Convert ZIL object/room names to `@` prefixed lowercase
   - `TERMINAL-ROOM` -> `@terminal-room`
   - `CHAIR` -> `@chair`
   - `PLAYER` -> `@player`

2. **Binding prefix**: Use `?` prefix for all contextual bindings
   - `self` -> `?self`
   - Ensure `?actor`, `?with`, etc. are used consistently

3. **Flags remain ALL-CAPS** (they're constants, not entity refs)
   - `TAKEBIT`, `LOCKED`, `OPENBIT` stay as-is

Location: src/grue/converter.py

Depends on frotzlm-fnh (naming conventions) and frotzlm-5ib (binding conventions) being finalized.
