---
id: gnusto-f95a.1
title: 'Elevator soft-locks: floor events never dequeue'
type: bug
priority: 1
created: '2026-07-11T14:37:24Z'
updated: '2026-07-11T14:58:58Z'
labels:
- lurkinghorror
- elevator
---

REPRO (deterministic, no LLM; grue-repl games/lurkinghorror/): from @terminal-room -> (go south) -> (do @down-button :push) -> (wait) x4 [elevator arrives floor 2, doors open] -> (go south) [board] -> (do @basement-button :push) -> (wait)... The car NEVER moves; each turn silently re-queues elevator-moves + elevator-door-closes with no state change. You can still (go out), but the elevator is functionally useless for changing floors -> basement is unreachable via elevator.

ROOT CAUSE: runtime.process_events (src/grue/runtime.py ~L579-592) does NOT remove an event from the queue when it fires; countdown=1 therefore means 'fire every turn' unless the body (dequeue)s itself. The three elevator events in games/lurkinghorror/elevator.grue -- elevator-door-opens (L479), elevator-door-closes (L494), elevator-moves (L510) -- never dequeue. Fatal loop: elevator stops -> queue elevator-door-opens 1 -> it fires, opens doors, stays queued -> re-fires every turn -> takes 'doors already open' branch -> re-arms (queue elevator-door-closes 2) each turn -> close timer never counts down -> doors never close -> elevator-moves' first guard 'do not move while any door is open' spins forever.

WHY UNCAUGHT: elevator.test.grue only asserts single-step facts (push button => elevator-moves queued); no end-to-end ride, and nothing runs many turns with doors open. The shipped walkthrough reaches the basement via STAIRS (go down, go down), never the elevator.

FIX (local): add terminal (dequeue ...) to the three events when work is done -- door-opens after opening, door-closes after closing, elevator-moves when stopped with no pending calls. Add an end-to-end elevator-ride test to elevator.test.grue (board -> press floor -> doors close -> arrive -> disembark at the right room). NOTE: if gnusto-aab0 changes the queue contract to auto-dequeue one-shots, revisit -- the manual dequeues may become redundant. Not hard-blocked on that decision; fix locally first.

---
▸ 2026-07-11T14:58:54Z
DONE. Root cause was the queue contract (gnusto-aab0), not elevator.grue -- the ZIL-faithful one-shot-dequeue fix makes the elevator work end-to-end with NO change to elevator.grue: doors open at the called floor, auto-close after the 2-turn window, car descends 2->1->0 and stops at the basement, player disembarks into @cs-basement. Validated in grue-repl. Replaced the stale pytest test_can_call_elevator (which only passed BECAUSE the soft-lock held the doors open forever) with test_can_ride_elevator_to_basement (full call->board->ride->disembark, bounded loops). Added grue-native 'elevator full ride' test to elevator.test.grue using the (until ...) DSL loop for timing-robustness. Spawned f95a.3 (floor-0-falsy narration sub-bug).
