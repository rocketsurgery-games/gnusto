---
id: gnusto-5818
title: 'hazard abstraction: (defhazard ...) for grue/freezing/flood-style events'
type: task
priority: 3
created: '2026-07-12T19:37:52Z'
updated: '2026-07-12T19:48:06Z'
labels:
- lang
depends_on:
- gnusto-2q9
---

---
▸ 2026-07-12T19:38:05Z
Cross-game recurring pattern (NOT Zork-specific): an environmental HAZARD event = each turn, reset a counter when safe / tick while unsafe / deterministic death past a grace. Instances: LH freezing (unsafe=outside), Zork grue-lurks (unsafe=dark), Zork dam-flood (unsafe=in flooding room). Three hand-rolled copies -> abstract it.

Design analysis (which yak it needs):
- HOF helper route (defn hazard-step taking the unsafe? predicate as a fn value) = gnusto-zbg territory: passing the predicate as a function argument defeats frotz effect/backward analysis (the 'unknown effects' problem). Buys ergonomics, loses analyzability.
- MACRO route (defhazard expanding to (event ... :on-turn (cond ...)) + counter property + queue) = gnusto-2q9 (macro system). Expansion is pre-analysis, so frotz just sees literal events -> full static analyzability preserved. Also gives 2q9 a much richer motivating use case than -> / ->> threading.

Conclusion: prefer the MACRO route (depends on gnusto-2q9) precisely because it keeps analysis sound; the HOF route would force zbg's conservative fallback. Belongs in the shared layer (builtins/language), surfaced to games as one declarative line. Reduces per-hazard boilerplate to: (defhazard NAME :unsafe? PRED :counter :KW :grace N :rise "..." :death "...").

---
▸ 2026-07-12T19:47:28Z
Design consolidated in docs/design/defhazard.md: the hazard pattern + 3 instances, proposed (defhazard ...) surface + load-time expansion target, and the 6 concrete requirements it places on the macro system (top-level definitional expansion feeding runtime AND analyzers; multi-form output; quasiquote/unquote/splice templates; keyword-arg defmacro; gensym/hygiene; library-macro load order) + sequencing + open questions. Implementation deferred until after the Zork conversion; gated on gnusto-2q9.
