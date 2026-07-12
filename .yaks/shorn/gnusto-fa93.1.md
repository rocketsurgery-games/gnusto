---
id: gnusto-fa93.1
title: 'Zork I slice 1: white-house exterior + mailbox/leaflet'
type: task
priority: 2
created: '2026-07-12T16:00:28Z'
updated: '2026-07-12T16:06:06Z'
labels:
- conversion
---

---
▸ 2026-07-12T16:05:58Z
Done. Added games/zork1/zork1.grue (world/player/victory-placeholder), white-house.grue (West/North/South/Behind House + mailbox/leaflet + scenery: white-house/board/forest/boarded-window/front-door), white-house.test.grue (22 tests). frotz lint clean; 22/22 grue-test pass; REPL smoke-tested opening (open mailbox, read leaflet, ring navigation). Outward exits (forest/path/clearing/kitchen) are faithful dangling refs to be filled by later slices. Notes started in games/zork1/CONVERSION-NOTES.md. Surfaced a language-design question (message-only exits) to raise before the forest slice.
