---
id: gnusto-266.3
title: 'Phase 3: Value domain inference'
type: task
priority: 1
created: '2026-01-23T17:55:51.278871-05:00'
updated: '2026-02-08T19:07:10.955516Z'
depends_on:
- gnusto-266.2
---

Implement automatic inference of minimal value domains from reduced expressions.

1. Write domain analysis:
   - For each StatePath, collect all values that can be written to it
   - Scan effect lists for (move ...) and (set ...) with literal values
   - For variable writes, use conservative approximation from builtin specs

2. Read pattern analysis:
   - For each StatePath, analyze how it's used in comparisons
   - (= (loc @obj) @player) → equality check against @player
   - (= (loc @obj) ?from) → equality check against runtime param domain
   - (:prop @obj) in boolean context → truthiness check

3. Minimal domain computation:
   - If path only compared to @player, domain is {held, not-held} (2 values)
   - If compared to finite literal set, domain is that set
   - If compared to runtime param, intersect with param's domain spec
   - Otherwise, full write domain

4. ValueDomain and AbstractionConfig classes:
   - ValueDomain tracks possible values and abstraction function
   - AbstractionConfig bundles tracked paths + their domains
   - Derived automatically from analysis, not manually specified

Deliverables:
- src/frotz/domains.py with ValueDomain, DomainAnalyzer
- Integration with effect analysis
- Test on floor-waxer case: should infer 5-value domain for loc(@floor-waxer)
