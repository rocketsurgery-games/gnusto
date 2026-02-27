---
id: gnusto-c2c
title: Clean up player display to hide implementation details
type: task
priority: 2
created: '2026-01-19T12:47:22.976795-05:00'
updated: '2026-02-08T19:07:11.006912Z'
---

Separate agent context (technical) from player display (natural). Currently render_game_state() shows implementation details like object IDs (@pc), action lists, and exit directions.

## Current display (leaks implementation)
```
Visible Objects
Object          Actions
@pc             examine, login <value>, ...

Exits
Direction       Destination
south           @cs-2nd
```

## Desired display (natural)
```
┌─────────────────────────────────────────────────────────────────┐
│ Terminal Room                                                    │
│                                                                  │
│ A really whiz-bang pc is right inside the door.                 │
│ There's a battered old chair here.                              │
└─────────────────────────────────────────────────────────────────┘

Nearby: Computer Science Building (2nd Floor)

Inventory: empty
```

## Implementation
1. Modify render_game_state() in frotz/agent.py
2. For objects: show fdesc/ldesc instead of ID + actions
3. For exits: show unique adjacent room descriptions, dedupe directional synonyms
4. Technical details (IDs, actions, directions) only shown in debug mode
5. Keep GameState structure unchanged - agent still needs technical context

## Goal
Game playable from player perspective without exposing "secrets" or implementation details when --debug is off.
