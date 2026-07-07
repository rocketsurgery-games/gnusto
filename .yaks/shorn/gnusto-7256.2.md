---
id: gnusto-7256.2
title: 'P2: grue output-effect vocabulary (narrate/say/describe/focus/reveal/emphasize/splash/sfx)'
type: task
priority: 1
created: '2026-07-07T21:51:39Z'
updated: '2026-07-07T22:06:31Z'
labels:
- runtime
- lang
depends_on:
- gnusto-7256.1
---

Widen the engine output stream from (narrate|say, entity, text) to carry the full block vocabulary + entity refs, and add the grue effects that produce them: (narrate ...), (say @who ... [:manner]), (describe ...), (focus @obj ...), (reveal @obj ...), (emphasize ...), (splash @obj ...), (sfx ...). Map each to its ContentBlock in the P1 construction path. Keep effects simple (no inline :beat/:deploy/:group yet). Document in docs/grue.md.

---
▸ 2026-07-07T22:06:31Z
Done. Widened EffectInterpreter.OUTPUT_EFFECTS + _collect_output to the full vocabulary: narrate/say (existing) + focus/reveal (entity+text), emphasize/sfx (text-only), splash (optional entity). Output stream stays (type, entity, text). agent _blocks_from_results emit_output maps each type -> its render block (Focus/Reveal/Splash/Sfx/Narrate[beat=emphasis]); narrate still Focus-enriched for examines (retired in P3). repl _print_output prints the stream generically. Kept effects simple per decision (no inline :beat/:deploy/:group). Documented the vocabulary table in docs/grue.md. Additive: no existing game/behavior affected. NOTE: the autoformatter reflowed expr.py/repl.py broadly (whitespace) alongside the functional change. Tests: TestEffectInterpreterOutput (8) + agent output->block mapping. Suite: 765 passed, 6 skipped.
