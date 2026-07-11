---
id: gnusto-3306.2
title: Event-lifecycle test assertions + document the (until ...) multi-turn idiom
type: feature
priority: 2
created: '2026-07-11T22:53:26Z'
updated: '2026-07-11T22:53:26Z'
labels:
- testing
---

Make multi-turn/event behavior easy to assert. (1) Encourage/scaffold the (until PRED (wait)) DSL loop for timed mechanics (used in elevator.test.grue 'full ride'). (2) A lifecycle assertion pattern: after a one-shot fires, (not-queued? X) -- the direct regression that would have caught the leak. Consider a small helper like (advance N) (wait N turns) and/or (assert-fires-once EVENT). Document in the grue-testing skill (gnusto-544d) and docs/frotz.md/grue.md as appropriate.
