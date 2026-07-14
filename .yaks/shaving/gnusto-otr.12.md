---
id: gnusto-otr.12
title: frotz reach returns NO after exploring only ~16 states (winnability oracle
  broken?)
type: task
priority: 2
created: '2026-07-13T20:58:12Z'
updated: '2026-07-14T04:04:05Z'
labels:
- tooling
---

---
▸ 2026-07-13T20:58:22Z
Flagged by the play-grue sub-agent during Zork validation: 'frotz reach --to ...' reportedly returns 'Reachable: NO' after exploring only ~16 states for EVERYTHING tried, including states reachable by hand (@painting@trophy-case, @coffin@player, @skull@trophy-case). If accurate, the reachability oracle is effectively useless on Zork-scale games (likely the explorer isn't expanding the action frontier / fingerprinting collapses states, or the state spec parsing fails). Not blocking (map connectivity + tests + REPL cover winnability empirically). To investigate: reproduce 'frotz reach --to "@painting@trophy-case" games/zork1', check explorer.py frontier expansion + state.py fingerprinting + the --to spec parse. Deprioritized behind the playthrough/transcript.

---
▸ 2026-07-14T04:04:05Z
Diagnosed (probes, now deleted). Three distinct defects, each confirmed empirically on Zork reach --to @painting@trophy-case:

A. EFFECT MODEL OMITS container put. effects._collect_takeable_effects models take (-> @player) and drop (-> room) but NOT put-into-container/surface. So no modifier sets @painting:location = @trophy-case; BackwardAnalyzer.build_tree marks the goal is_constant with zero achievers -> empty dependency tree. This is the PRIMARY blocker for a rigorous static dependency chart (requires/depgraph), and it is a static fix (no forward search).

B. FORWARD FINGERPRINTING UNSOUND unless tracked refs are the full transitive precondition closure of the target. Mechanism is otherwise sound: default reach tracks only target+@player, so e.g. opening the kitchen window yields a fingerprint-identical state that is discarded as already-visited, and the player can never get inside -> 16 states, false NO. Adding @kitchen-window:open unlocked the interior (19 rooms); adding lamp/sword/troll/trap-door refs is needed for underground. So the fix is to auto-track the target closure (depends on A so the closure is discoverable).

C. FORWARD RESTORE IS O(depth) REPLAY. explore() replays the whole path from scratch for every action trial (num_actions+1 replays per node, each O(path length)). Measured ~0.19s/state at depth 30, ballooning at depth 80; cap=200 did not finish in 400s. Intractable for the many-ref sound queries B needs. Fix: snapshot/restore runtime state per node instead of replay.

BOUNDS: the rigorous DESIGN-TOOL answers the user wants (dependency chart) live on the STATIC backward path, blocked mainly by A (contained). Sound forward reach additionally needs B+C; C is a real perf refactor. Recommend fixing A first (unblocks rigorous depgraph/requires), then decide whether to invest in B+C for forward reach.
