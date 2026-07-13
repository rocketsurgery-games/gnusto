---
id: gnusto-otr.12
title: frotz reach returns NO after exploring only ~16 states (winnability oracle
  broken?)
type: task
priority: 2
created: '2026-07-13T20:58:12Z'
updated: '2026-07-13T20:58:22Z'
labels:
- tooling
---

---
▸ 2026-07-13T20:58:22Z
Flagged by the play-grue sub-agent during Zork validation: 'frotz reach --to ...' reportedly returns 'Reachable: NO' after exploring only ~16 states for EVERYTHING tried, including states reachable by hand (@painting@trophy-case, @coffin@player, @skull@trophy-case). If accurate, the reachability oracle is effectively useless on Zork-scale games (likely the explorer isn't expanding the action frontier / fingerprinting collapses states, or the state spec parsing fails). Not blocking (map connectivity + tests + REPL cover winnability empirically). To investigate: reproduce 'frotz reach --to "@painting@trophy-case" games/zork1', check explorer.py frontier expansion + state.py fingerprinting + the --to spec parse. Deprioritized behind the playthrough/transcript.
