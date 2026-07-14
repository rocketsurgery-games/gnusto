---
id: gnusto-otr.13
title: 'Effect-model completeness: anchor frotz to EffectInterpreter vocab + model
  put; add drift guard'
type: task
priority: 2
created: '2026-07-14T20:20:32Z'
updated: '2026-07-14T20:26:05Z'
labels:
- tooling
---

---
▸ 2026-07-14T20:26:05Z
Done (defect A + full effect-model audit). Anchored frotz.effects to the runtime's closed vocabulary EffectInterpreter.MUTATIONS. Added previously-missing walker handlers: inc, dec (read+modify numeric prop), set-in (modifies top-level prop of the path), expose (modifies :known=true). Modeled the engine default 'put' in _collect_takeable_effects: a takeable object's location can become any container/surface (the defect-A fix; deposit goals now have a real achiever instead of being marked constant). Added backward.py runtime:put precondition (object held); destination-open gate deferred. Drift guard: HANDLED_EFFECT_MUTATIONS constant + tests/frotz/test_effects_completeness.py asserts it == EffectInterpreter.MUTATIONS exactly, so a new runtime effect can't land without an analyzer handler. Docs note added to AGENTS.md + docs/frotz.md. Verified: @painting@trophy-case backward tree now non-empty (achiever runtime:put, precond painting held). Suites green: 820 pytest, 213 grue-test zork1, frotz lint clean.
