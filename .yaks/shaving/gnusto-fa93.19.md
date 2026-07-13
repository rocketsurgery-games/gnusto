---
id: gnusto-fa93.19
title: 'Zork I: full LLM-harness playthrough validation'
type: task
priority: 2
created: '2026-07-13T02:52:34Z'
updated: '2026-07-13T04:59:04Z'
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

---
▸ 2026-07-13T03:33:24Z
Deposit-loop playthrough (LLM harness): start -> Gallery painting (troll avoided via Cellar->S->East-of-Chasm->E->Gallery) -> drop sword -> chimney carry-limit climb to Kitchen -> Living Room -> open trophy case -> deposit painting ('Done.'). All correct. Surfaced a P1: 'look' collapsed to 'wait' because the 'look' tool was missing from AGENT_RESPONSE_SCHEMA's enum -- FIXED in gnusto-0bf7.7. Note (by design): deterministic conversion dropped the 350-pt score, so depositing gives no score feedback (endgame gate is all-treasures-deposited?).

---
▸ 2026-07-13T03:39:47Z
Precondition-chaining probe (kitchen): agent correctly opened containers, but 'eat the lunch'/'drink the water' both mapped to 'take' -- no eat/drink verb existed. FIXED as gnusto-036d (default eat/drink in builtins.grue). Re-verified via harness: eat/drink now dispatch. Session tally of playthrough findings: gnusto-0bf7.5 (direction synonyms, fixed), gnusto-0bf7.7 (look->wait enum, fixed), gnusto-036d (eat/drink defaults, fixed), gnusto-0bf7.6 (parse-only narrative summarization leak, filed/deferred pending user).

---
▸ 2026-07-13T04:26:58Z
Egg region (climb tree, take egg, destructive self-open breaks canary, wind broken canary blocked): all clean, no bugs. Multi-action 'take the canary and wind it' decomposed correctly.

Grue-death run (attic, no lamp): grue mechanic works (dark tick -> pitch-black warning -> strike at grace exhaustion). Surfaced two issues: gnusto-0bf7.8 ('unknown' reason sentinel leaked into death output -- FIXED) and gnusto-0bf7.9 (P1: death/victory not terminal in the harness -- runtime sets :dead but the loop plays on as a corpse; filed, awaiting design call).

---
▸ 2026-07-13T04:59:04Z
Maze + cyclops run (LLM harness): kill troll (2 blows -> W passage opens) -> navigate the dark maze through 8 identical 'twisty little passages' rooms via explicit directions (W,S,E,up,SW,E,S,SE) -> Cyclops Room -> examine cyclops -> 'say Odysseus to the cyclops' correctly mapped to (do @cyclops :odysseus) -> he flees and knocks down the east wall. NO BUGS. Confirms: full combat completion, robust navigation through indistinguishable dark rooms, direction synonyms in play (go southwest->sw, southeast->se), maze loot surfacing, and NL->named-verb mapping for the magic word.
