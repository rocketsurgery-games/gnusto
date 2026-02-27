---
id: gnusto-2fv
title: Convert existing .grue files to @lowercase naming
type: task
priority: 2
created: '2026-01-11T12:08:58.13239-05:00'
updated: '2026-02-08T19:07:11.053576Z'
---

Manually update existing .grue files to use the new @lowercase naming convention:

Files to update:
- games/examples/outside-door.grue
- games/examples/outside-door.test.grue
- games/lurkinghorror/terminal-room.grue
- games/lurkinghorror/terminal-room.test.grue
- src/grue/builtins.grue

Conversion rules:
- Object/room names: `TERMINAL-ROOM` -> `@terminal-room`
- PLAYER: `PLAYER` -> `@player`
- Flags stay ALL-CAPS: `TAKEBIT`, `LOCKED`, `OPENBIT` unchanged
- Verbs/predicates stay lowercase: `has-flag`, `move!`, `open` unchanged

This is separate from frotzlm-86f (converter update) to preserve manually-translated behaviors.

Note: Tests may need updating to match new entity names.
