---
id: gnusto-otr.15
title: 'Explorer defect C: snapshot/restore runtime state (replace O(depth) path replay)'
type: task
priority: 2
created: '2026-07-14T20:52:07Z'
updated: '2026-07-14T20:52:20Z'
labels:
- tooling
---

---
▸ 2026-07-14T20:52:20Z
Defect C from the explorer diagnosis (see gnusto-otr.12). explore() restores each state by REPLAYING its whole path from scratch, once per action trial (num_actions+1 replays per node, each O(path length)) -> O(states x branching x depth). Measured ~0.19s/state at depth 30, ballooning at depth 80; a 200-state cap didn't finish in 400s. Intractable for the many-ref sound queries B needs. Fix: snapshot/restore the runtime's mutable state (object locations, properties, event queues) per node instead of replaying -- O(1) restore per action trial. Consider grue.save or a targeted state snapshot rather than a full deepcopy. Independent of A/B (pure performance).
