---
id: gnusto-7l2
title: Convert The Lurking Horror to Grue
type: task
priority: 2
created: '2026-01-12T17:00:42.826467-05:00'
updated: '2026-02-08T19:07:11.051679Z'
labels:
- lh
---

Complete conversion of The Lurking Horror from ZIL to Grue DSL.

## Source Files (~18k lines ZIL)
- cs.zil (5,600 lines) - CS building, tunnels, elevator, alchemy, dome
- frob.zil (1,700 lines) - Underground tunnels, lair maze, urchins, repeater puzzle
- green.zil (580 lines) - Brown building, courtyard, great court, roof
- hacker.zil (940 lines) - Hacker NPC, kitchen, food/keys
- pc.zil (530 lines) - Terminal, PC, program objects
- yuggoth.zil (350 lines) - Nightmare sequence
- globals.zil - Global objects (player body parts, walls, etc.)
- verbs.zil - Verb handlers
- misc.zil - Miscellaneous routines
- syntax.zil, parser.zil - Parser (not needed for Grue)

## Already Converted (partial)
- terminal-room.grue - Starting room with hacker interaction
- hacker.grue - Hacker NPC, keys, Chinese food
- pc.grue - Computer/terminal objects
- chair.grue - Chair object
- objects.grue - Misc objects

## Major Areas
1. Computer Science Building (cs.zil upper)
2. Steam Tunnels & Underground (cs.zil lower, frob.zil)
3. Brown Building & Great Dome (green.zil)
4. Alchemy Department & Lab (cs.zil)
5. Lair & Endgame (frob.zil)
6. Nightmare Sequence (yuggoth.zil)
7. Global Objects & NPCs
