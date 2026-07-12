---
id: gnusto-be0a
title: 'Truthiness: adopt LISP/Clojure-faithful nil/false-only falsy (drop Python
  0/''''/[]-falsy)'
type: task
priority: 2
created: '2026-07-11T22:53:09Z'
updated: '2026-07-12T00:01:23Z'
labels:
- lang
- runtime
---

INVESTIGATION (done): Grue's truthiness is Python host-language leakage -- conditionals do plain 'if self.eval(x)' / 'if not ...' in expr.py (_eval_if/_eval_cond/_eval_when/_eval_and/_eval_or/_eval_not), so 0, 0.0, '', [], {} are all falsy. This is NOT a LISP-family trait and NOT JVM: Scheme (#f only), Common Lisp (nil only), Clojure (nil/false only), and MDL/ZIL (the FALSE object <> only) all treat 0 as TRUTHY. Evidence in the LH ZIL: it uses explicit <ZERO?> (131x), <G?> (110x), <L?> (36x) for every numeric test precisely because 0 is truthy and cannot be tested via raw truthiness; the false literal is <> (e.g. ("AUX" (FORG <>))). CONSEQUENCE: 0-falsy makes ZIL conversion HARDER and buggier -- it directly caused the basement (floor 0) narration bug (gnusto-f95a.3) via (and ?floor ...). RECOMMENDATION: introduce a single grue_truthy() helper and make only nil/false falsy (Clojure-faithful), which is both more idiomatic and safer for ZIL conversion. RISK/BLAST RADIUS to assess before changing: Grue code that currently relies on ''/[]/{}/0 being falsy (e.g. (if some-list ...), (when (rest xs) ...), (if (:counter x) ...)); audit + migrate call sites (likely use (nil?), (empty?), (seq), explicit numeric compares). Needs user go-ahead; this is a semantics change with wide reach.

---
▸ 2026-07-12T00:01:23Z
Done (145995d). Added is_truthy() (only None/False falsy) and routed all truthiness decisions through it: expr.py control flow (and/or/not/if/when/cond/condp/cond->/cond->>, some/every?/filter/remove), runtime victory/defeat, eval_predicate, test DSL assert/until/expectation. Audit found NO code relying on 0/''/[] falsy (all flags boolean; counters use condp=; :username uses false sentinel; ?msg non-empty-or-nil), so change only fixes behavior. Docs/AGENTS/translate-zil updated. Spawned gnusto-294d (and/or should return the deciding value, not a bool). 774 pytest + 479 grue-test pass.
