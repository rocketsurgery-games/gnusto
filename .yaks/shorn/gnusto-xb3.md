---
id: gnusto-xb3
title: Nest container contents in agent state context
type: task
priority: 2
created: '2026-01-19T12:22:17.096724-05:00'
updated: '2026-02-08T19:07:11.007156Z'
---

The agent state serialization currently presents visible objects as a flat list, losing containment relationships. The agent doesn't know that @menu-box is "in" @pc.

## Current behavior
```
**Visible objects:**
- @pc: pc [actions: examine, read, ...]
- @menu-box: menu box [actions: click, read]
```

## Desired behavior
Walk the visible object tree and nest contents under their containers:
```
**Visible objects:**
- @pc: pc [actions: examine, read, ...]
  - @menu-box: menu box [actions: click, read]
- @chair: chair [actions: sit, take]
```

## Implementation
1. In frotz/state.py, modify get_game_state() to build a tree rather than flat list
2. Change ObjectInfo or add a children field for nested objects
3. Update to_context_string() to render nested objects with indentation
4. Only nest objects that are in open/transparent containers or on surfaces

## Why this matters
- Agent can reason about containment for planning ("take key from box")
- Matches ZIL semantics where examining containers shows contents
- Enables natural language like "the menu box on the PC screen"
