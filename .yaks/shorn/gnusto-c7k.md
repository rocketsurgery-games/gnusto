---
id: gnusto-c7k
title: 'Frotz Phase 1: Effect analysis pass'
type: task
priority: 2
created: '2026-01-20T18:45:07.79403-05:00'
updated: '2026-02-08T19:07:11.004298Z'
depends_on:
- gnusto-44o
---

Scan all world definitions and build:

1. **modifies**: `property → set[behavior]` - which behaviors can modify each property
2. **reads**: `property → set[behavior]` - which behaviors depend on each property
3. **constants**: `set[property]` - properties that never change

This is the "def" side of def-use analysis. For each property in the game, we want to know:
- Can it ever change? (if not, it's a constant)
- What behaviors can change it? (the modifiers)
- What behaviors read it? (for relevance analysis later)

Implementation:
- Walk all objects, rooms, events, defaults
- For each behavior body, find all `(set ...)`, `(move ...)`, `(queue ...)` effects
- For each condition, find all property reads `(:prop @obj)`, `(loc @obj)`, etc.
- Build the maps

Output: Data structures that can answer "what can modify @door:locked?" and "what reads @player:score?"

See docs/frotz-design.md for context.
