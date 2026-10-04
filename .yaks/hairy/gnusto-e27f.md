---
id: gnusto-e27f
title: 'frotz kernel/differential CLI: print a game''s concrete answer key'
type: task
priority: 3
created: '2026-09-14T03:44:01Z'
updated: '2026-09-14T03:44:01Z'
parent: gnusto-266.5
labels:
- tooling
---

Follow-up noted but never filed when the differential harness landed (gnusto-266.5.2): there is no way to run the kernel or the harness from the command line. frotz reach/analyze still call the old explorer.py (defects B and C live), and kernel.py + differential.py are reachable only from tests.

WANT: a subcommand -- frotz kernel GAME -- that runs the concrete BFS and prints the answer key: reached-state count, the hit_limit honesty flag, and the True/False/unknown label for every static_atoms probe. So a game's ground truth can be eyeballed on demand and diffed against whatever the production tools claim. Second mode: frotz differential GAME, comparing the production analysis against the oracle and printing unsound vs merely-imprecise disagreements.

Small, but it is what turns the oracle from a test fixture into a debugging instrument. Note the honest limits: the kernel finishes instantly on Mini and hits the cap on Zork, so the CLI must present hit_limit prominently rather than implying a complete answer.
