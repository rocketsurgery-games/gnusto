---
id: gnusto-otr.15
title: 'Explorer defect C: snapshot/restore runtime state (replace O(depth) path replay)'
status: hairy
type: task
priority: 2
created: '2026-07-14T20:52:07Z'
updated: '2026-09-28T16:35:42Z'
parent: gnusto-otr
labels:
- tooling
---

---
▸ 2026-07-14T20:52:20Z
Defect C from the explorer diagnosis (see gnusto-otr.12). explore() restores each state by REPLAYING its whole path from scratch, once per action trial (num_actions+1 replays per node, each O(path length)) -> O(states x branching x depth). Measured ~0.19s/state at depth 30, ballooning at depth 80; a 200-state cap didn't finish in 400s. Intractable for the many-ref sound queries B needs. Fix: snapshot/restore the runtime's mutable state (object locations, properties, event queues) per node instead of replaying -- O(1) restore per action trial. Consider grue.save or a targeted state snapshot rather than a full deepcopy. Independent of A/B (pure performance).

---
▸ 2026-09-28T16:35:42Z [Joel Webber]
SUPERSESSION NOTE (cross-ref gnusto-266.5). This defect is O(depth) path-replay in the OLD explorer.py. It is ALREADY solved in the kernel restart: frotz.kernel.step snapshots via GameState.copy() instead of replaying. Per docs/design/state-graph-kernel.md, explorer.py + deferred/ are to be retired by hard cutover once the kernel + abstraction stack reaches parity. So fixing this in the old explorer is likely moot -- when the forward tools re-root on the kernel stack, close or slaughter this rather than implement it against explorer.py. Recorded for planning; not changing state or deps without user sign-off.
