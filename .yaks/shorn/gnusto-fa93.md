---
id: gnusto-fa93
title: Convert Zork I to Grue
type: task
priority: 2
created: '2026-07-12T16:00:25Z'
updated: '2026-07-14T02:18:38Z'
labels:
- conversion
---

---
▸ 2026-07-12T16:00:39Z
Plan: convert Zork I (games/zork1) to Grue, mirroring the LH conversion style, driven by the translate-zil skill. Vertical slices, each a clean root .grue + .test.grue, frotz-lint clean, both suites green. Slices (rough): (1) white-house exterior + mailbox/leaflet; (2) house interior kitchen/living-room/attic + window + trap door + lamp/sword; (3) above-ground forest ring + grating; (4) cellar/underground + light/grue darkness; (5) troll/thief combat; (6) reservoir/dam; (7) treasures + scoring (350pt) + endgame/barrow. Cross-cutting: light/darkness+grue, LOCAL-GLOBALS scenery (walls/forest/house/water), combat, score. Also: keep a running NOTES doc of what went well/poorly + skill/tooling improvements; update & implement gnusto-otr design tools as they prove useful for both translation and new-game design.

---
▸ 2026-07-14T02:18:38Z
CONVERSION COMPLETE. Zork I fully converted to Grue and verified winnable end-to-end through the LLM harness in natural language (all 19 treasures -> Stone Barrow victory). 15 build slices (.1-.18) + full playthrough validation (.19) shorn. Deterministic throughout for frotz-soundness. The one deferred design leftover (richer analyzable thief) is hoisted to gnusto-6b4f (randomness in conversions). Marking shorn.
