---
id: gnusto-0l8
title: Design standard binding for give/trade item in NPC behaviors
type: task
priority: 3
created: '2026-01-11T19:17:23.612536-05:00'
updated: '2026-02-08T19:07:11.075765Z'
---

The hacker behaviors in terminal-room.grue use ?object to refer to the item being given/traded, but this is not a standard binding.

Current situation:
- Behaviors are on @hacker, so ?self = @hacker
- Behaviors check (= ?object @carton) etc for the item
- But ?object is not defined in the standard binding model

The problem is that for "give X to Y":
- Direct object (behavior target): Y (@hacker)
- Indirect object (item): X (@carton)
- We need a standard binding for X

Options:
1. Add ?item binding for give/put/show/trade verbs
2. Use ?with ("give carton with hacker" is weird though)
3. Move behaviors to item objects with special dispatch
4. Use ?indirect as standard name

This blocks proper testing of the give/trade puzzle in terminal-room.test.grue.

See also: docs/grue.md binding documentation
