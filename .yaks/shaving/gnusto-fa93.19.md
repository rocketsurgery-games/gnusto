---
id: gnusto-fa93.19
title: 'Zork I: full LLM-harness playthrough validation'
type: task
priority: 2
created: '2026-07-13T02:52:34Z'
updated: '2026-07-13T03:22:27Z'
labels:
- conversion
---

---
▸ 2026-07-13T03:03:05Z
Playthrough validation surfaced two room-block rendering bugs, both fixed:
1. :nodesc scenery leaked into the 'You see:' listing. Root cause: get_game_state builds objects with for_description=False (so the LLM can still resolve 'examine the board'), but the display never re-filtered :nodesc. Fix: carry a nodesc flag through ObjectInfo -> EntityInfo and filter AFTER flattening in build_room_block, so a :nodesc container (kitchen table) is hidden while its real contents (sack, bottle) still show. state.visible_objects/to_context_string left unchanged (agent still needs nodesc objects for NL resolution).
2. Message-only blocked exits (ZIL string/SORRY exits, e.g. kitchen chimney 'Only Santa Claus climbs down chimneys.') were listed as navigable exits and produced a None destination name that crashed format_room_enter's join. Fix: skip exits with to is None in get_game_state. Verified at West-of-House and Kitchen; 810 pytest + 688 grue-test green.

---
▸ 2026-07-13T03:22:27Z
Dam-region playthrough (LLM harness, --debug): drove start -> house -> gear up -> cellar -> troll (deterministic combat) -> EW passage -> round room -> NS passage -> deep canyon -> Dam -> maintenance room -> yellow button + wrench -> turn bolt -> reservoir drained. Two findings:
  1. Direction synonyms: (go northeast) hit no-exit vs stored 'ne' at NS Passage; stranded the agent. FIXED in gnusto-0bf7.5 (normalize_direction), re-ran to full dam drain -- clean.
  2. Confirmed the :nodesc fix under real play: the yellow button/bolt/bubble are :nodesc so absent from 'You see:', yet the agent still resolved 'push the yellow button' from context. Good.
Also observed (not a bug, filed gnusto-0bf7.6): parse-only mode still runs LLM narrative summarization + injects an 'I'll continue narrating' priming line -- internal agent memory only, awaiting user input.
Playthrough validated through the dam puzzle; harness solid modulo the above.
