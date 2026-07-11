---
id: gnusto-3306.1
title: 'Static lint: finite-countdown event that neither re-queues nor self-dequeues'
type: feature
priority: 2
created: '2026-07-11T22:53:22Z'
updated: '2026-07-11T23:29:17Z'
labels:
- testing
- lang
---

Highest-value check: statically flag any (event X) that can be (queue X N) with finite N but whose :on-turn body has a reachable fire path that neither (queue X ...) re-queues nor (dequeue X) self-dequeues. Under the one-shot contract (gnusto-aab0) that's almost always a bug (event fires once when the author expected a per-turn chain -- exactly the compulsion bug) OR harmless. Would have caught both the elevator and compulsion before runtime. Could live in the grue linter / load-time checks. Pair with a positive note when an event uses None/-1 (indefinite) so authors see intent.

---
▸ 2026-07-11T23:29:17Z
Done (ba31666). grue.lint.lint_world + 'frotz lint' command flag dropped event chains: (condp = (:prop @ent)) counter machines that mutate that prop, are queued only finitely, and never self-requeue. Calibrated on all LH events -> flags exactly pre-fix compulsion, 0 false positives. pytest keeps LH lint-clean (CI regression gate). Docs (frotz.md) + translate-zil/grue-testing skills updated. NOTE: v1 targets the condp-counter idiom; a cond-based counter machine would slip -- broaden later if needed.
