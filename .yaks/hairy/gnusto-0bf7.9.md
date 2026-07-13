---
id: gnusto-0bf7.9
title: 'Harness has no end-state handling: death and victory are not terminal'
type: task
priority: 1
created: '2026-07-13T04:26:29Z'
updated: '2026-07-13T04:26:42Z'
labels:
- bug
---

---
▸ 2026-07-13T04:26:42Z
Found via the grue-death playthrough. After the grue 'eats' the player, the game just keeps going: a second 'wait' re-fires the grue death, and 'look' still works -- you play on as a corpse. Neither GameSession.process_input nor the TUI run loop ever checks the end state.

The runtime DOES set it: _check_death_context sets @player :dead=true on any (death true) context (both _do_impl and _evaluate_event call it); victory is signalled via (success :context ((victory true))). But NOTHING consumes :dead / :won in the interactive harness -- there's no game-over, no resurrection, no score, no loop break. (Victory is only asserted via grue-test in the endgame; the handoff reached it through the test DSL, not the harness -- so this gap was never exercised.)

DESIGN QUESTION for user (why this is filed, not fixed):
  - Death: game-over-and-stop vs Zork-style resurrection (ZIL JIGS-UP: after death, scatter your items, drop you at a random above-ground room with a score penalty; after N deaths, permanent game over). Resurrection is a real feature with placement/score rules.
  - Victory: the win move should present the ending and stop the loop (currently the loop continues after '*** VICTORY! ***').
  - Also: once dead, further actions/events should be suppressed until resolved (the grue re-firing each turn is a symptom).
Proposed minimal first cut (pending your call): after each turn check @player :dead / :won; on death emit a game-over SystemMessage + stop accepting game commands (offer /reset); on victory emit the ending + stop. Layer Zork resurrection on top later if desired. Raised to user.
