---
id: gnusto-266.5.2
title: '''Differential-test harness + tiny-game corpus (kernel vs abstraction layer),'
type: task
priority: 2
created: '2026-07-31T03:45:49Z'
updated: '2026-08-28T04:53:32Z'
parent: gnusto-266.5
depends_on:
- gnusto-266.5.1
labels:
- tooling
---

---
▸ 2026-08-28T04:53:32Z
Done. Built the differential-test harness (src/frotz/differential.py) + tiny-game corpus (tests/frotz/corpus.py) + tests (tests/frotz/test_differential.py). Comparison mode A = multi-goal reachability: static_atoms(world) derives a finite probe set (object locations over rooms/player/containers/limbo + boolean-property assignments) containing both reachable and unreachable targets; kernel_answers runs one BFS and labels each atom True/False/None(unknown if hit_limit) by membership in the union of reached fingerprints. differential(name, world, ref, cand) compares two analyses and classifies each disagreement: ref=True/cand=False is UNSOUND (false NO, the fatal kind), ref=False/cand=True is imprecise-but-sound (over-approx allowed). Corpus = 8 games seeded to stress each planned layer: mini/sealed (movement+gate, solvable vs permanently-locked), combo (value-arg), twoarg (multi-arg), counter (numeric domain -> 4.2), oneway/oneway_ok (irreversible descent -> 4.3; softlock is a real unwinnable state the oracle detects), independent (order-independent takes -> POR). Each carries hand-verified anchors so a kernel regression fails too. Tests: kernel matches anchors; self-differential agrees on every atom of every game; harness proven to flag a false NO as unsound and an over-approx as imprecise. Full frotz suite 152 passed. Updated docs section 6. Note: a fixture bug (return exit on wrong room) initially made oneway_ok look unreachable -- the kernel correctly caught it, nice validation. Follow-up idea (not filed): a frotz kernel/differential CLI to eyeball a game's answer key on demand.
