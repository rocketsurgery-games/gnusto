---
id: gnusto-0bf7.11
title: 'render_block_to_text crashes on RoomEnter: treats EntityInfo/ExitDetail as
  strings'
type: task
priority: 2
created: '2026-07-13T15:30:00Z'
updated: '2026-07-13T15:32:26Z'
labels:
- bug
---

---
▸ 2026-07-13T15:32:26Z
FIXED. render_block_to_text RoomEnter branch now reads e.destination / o.name / i.name instead of joining EntityInfo/ExitDetail as strings (and uses Exits:/You see:/Carrying: labels). Regression test test_render_blocks_to_text_projects_room_enter in tests/gnusto/test_tui_render.py. Surfaced while building the transcript generator; this path is live via agent.py _handle_slash_command (/look, /load).
