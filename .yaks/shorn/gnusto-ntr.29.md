---
id: gnusto-ntr.29
title: 'TUI room render crashes: joins ExitDetail/EntityInfo as strings'
type: bug
priority: 1
created: '2026-07-04T17:42:03Z'
updated: '2026-07-04T17:44:16Z'
labels:
- runtime
- tui
- bug
---

SimpleTUI.render_block (tui.py) still joins block.exits/objects/inventory as plain strings, but RoomEnter now carries list[ExitDetail] (exits) and list[EntityInfo] (objects/inventory) after the Epic B structured-model switch. Result: TypeError: sequence item 0: expected str instance, ExitDetail found, on the very first room render (before any LLM call). The web frontend renders these structs correctly; the TUI path was left stale. Fix: join e.direction for exits, o.name for objects/inventory.

---
▸ 2026-07-04T17:44:15Z
Fixed. SimpleTUI.render_block joined structured RoomEnter fields as strings; now projects e.direction (exits) and o.name (objects/inventory). Also fixed the sibling latent crash in agent.render_game_state debug branch (state.exits.items() -> iterate ExitInfo.direction/destination_name; state.exits is list[ExitInfo], not a dict). Both are Epic-B structured-model regressions in consumers the web frontend already handled. Verified against lurkinghorror (first-room render + debug render). Added tests/gnusto/test_tui_render.py (2 cases). Suite: 746 passed, 6 skipped.
