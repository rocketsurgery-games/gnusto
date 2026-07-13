---
id: gnusto-0bf7.10
title: TUI renders the room you died in after the game-over banner
type: task
priority: 3
created: '2026-07-13T15:24:04Z'
updated: '2026-07-13T15:24:45Z'
labels:
- harness
---

---
▸ 2026-07-13T15:24:45Z
FIXED. TUI run loop now skips the post-command room re-render when self.session._end_state() is set, so the ending isn't followed by a stray render of the room you died in. Verified via harness (gas-room death: BOOM -> banner, no trailing room block). 816 pytest green.
