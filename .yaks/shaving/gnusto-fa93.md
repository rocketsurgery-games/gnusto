---
id: gnusto-fa93
title: Convert Zork I to Grue
type: task
priority: 2
created: '2026-07-12T16:00:25Z'
updated: '2026-07-12T16:00:42Z'
labels:
- conversion
---

---
▸ 2026-07-12T16:00:39Z
Plan: convert Zork I (games/zork1) to Grue, mirroring the LH conversion style, driven by the translate-zil skill. Vertical slices, each a clean root .grue + .test.grue, frotz-lint clean, both suites green. Slices (rough): (1) white-house exterior + mailbox/leaflet; (2) house interior kitchen/living-room/attic + window + trap door + lamp/sword; (3) above-ground forest ring + grating; (4) cellar/underground + light/grue darkness; (5) troll/thief combat; (6) reservoir/dam; (7) treasures + scoring (350pt) + endgame/barrow. Cross-cutting: light/darkness+grue, LOCAL-GLOBALS scenery (walls/forest/house/water), combat, score. Also: keep a running NOTES doc of what went well/poorly + skill/tooling improvements; update & implement gnusto-otr design tools as they prove useful for both translation and new-game design.
