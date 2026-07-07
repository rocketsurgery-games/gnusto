---
id: gnusto-7256.3
title: 'P3: migrate Lurking Horror to the block vocabulary (canonical conversion)'
type: task
priority: 1
created: '2026-07-07T21:51:39Z'
updated: '2026-07-07T22:51:52Z'
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
