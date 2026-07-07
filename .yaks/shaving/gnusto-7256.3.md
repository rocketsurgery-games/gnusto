---
id: gnusto-7256.3
title: 'P3: migrate Lurking Horror to the block vocabulary (canonical conversion)'
type: task
priority: 1
created: '2026-07-07T21:51:39Z'
updated: '2026-07-07T23:11:27Z'
labels:
- lurkinghorror
- lang
depends_on:
- gnusto-7256.2
---

Migrate LH grue to the P2 vocabulary as the canonical Infocom-conversion reference: :message (x471) -> (narrate ...)/(say @who ...); :describe :context((description)) (x123) -> (describe ...) for rooms/objects (object examine -> focus); :context((hint)) (x4) -> (say @hacker ...); :transition / compulsion pages -> (emphasize ...)/(splash ...); drop :page/:stage from output (keep as state). Remove now-vestigial context-text folding from the P1 path once migrated. Document conventions in docs/grue.md as the reference.

---
▸ 2026-07-07T22:22:36Z
Slice 1 (terminal-room + pc) done. Added (output? TEXT) test predicate (asserts emitted narration/dialogue contains TEXT). Migrated terminal-room.grue: hacker-helps stages -> narrate; food-hint -> (say @hacker ...); compulsion pages 1-3 -> narrate, page 4 -> emphasize + (splash "You faint..."); dropped :stage/:page/:nightmare-wake. Migrated pc.grue: object :examine -> (focus @obj ...), all other success text -> narrate, dropped metadata context flags (power/booting/was-powered/auto-unplug/screen-contents/possession-starting); blocked handlers left as-is per rule. Updated terminal-room.test.grue: (context? stage/page N) -> (output? snippet). All 477 grue + 765 python pass; live parse-only PC flow renders focus/narrate correctly. Remaining: ~39 game files still on (success :message ...).

---
▸ 2026-07-07T22:51:52Z
Slice 2 (parallel sub-agents): migrated lair.grue (61 sites: 19 focus/42 narrate), cs-basement.grue (22: 11 focus/11 narrate), steam-tunnels.grue (41: 17 focus/24 narrate) + steam-tunnels.test.grue (1 context?message->output?). Rules confirmed by agents: object :examine->focus, other success text->narrate, blocked & room/object :describe(:context((description))) untouched, :render kept (drives art). All 477 grue pass. DEFERRED: (a) alchemy.grue migration — user has uncommitted WIP (pentagram line-wrapping) staged there, so I backed the agent's migration out to avoid contaminating user work; redo alchemy after user's WIP lands. (b) Stylistic consistency pass at end of P3: event/one-time :context((description))->narrate (lair left some as context; steam-tunnels/terminal-room converted), :context((ambient))->narrate (steam-tunnels, 3 sites; currently never rendered), death/victory climax descriptions -> narrate/emphasize.

---
▸ 2026-07-07T23:11:27Z
Slice 3 (parallel sub-agents, wave 2): migrated brown-building, great-dome, elevator, cs-building, maintenance-man, urchins, globals, objects, chair, kitchen, yuggoth, aero-building, hacker (+ cs-2nd/infinite-corridor had nothing to migrate). Applied refined rules: object :examine->focus; event/one-time :context((description))/((ambient))->narrate; room+object :describe stay structural; NPC dialogue->say; :render kept. Also migrated the STDLIB defaults in src/grue/builtins.grue (take/drop/open/close/put/examine success text -> narrate) so default responses flow through the output stream consistently; this fixed the 3 globals default-examine test failures. Updated globals.test.grue (24 context?message->output?), aero-building.test.grue (1), steam-tunnels earlier, and tests/test_walkthrough.py (2 examine/search assertions -> output). 477 grue + 765 python pass. STILL DEFERRED: alchemy.grue (user WIP). Remaining consistency polish tracked for end-of-P3.
