---
id: gnusto-ntr.16
title: Distinguish let vs let* semantics
type: task
priority: 3
created: '2026-01-14T10:02:50.238563-05:00'
updated: '2026-02-08T19:07:11.075191Z'
labels:
- lang
---

Current \`let\` has sequential binding semantics (like Scheme's \`let*\`).

**Current behavior:**
```scheme
(let ((x 1) (y (+ x 1))) y)  ; Works, returns 2
```

**Scheme/Clojure distinction:**
- \`let\`: All binding values evaluated in outer scope, then all bound simultaneously
- \`let*\` / Clojure \`let\`: Sequential binding, each visible to subsequent bindings

**Example of difference:**
```scheme
(let ((x 1))
  (let ((x 10) (y x))  ; In let: y=1 (outer x). In let*: y=10 (new x)
    y))
```

**Options:**
1. Keep current sequential semantics (Clojure-style), rename or document
2. Implement true parallel \`let\` and add \`let*\` for sequential
3. Just document current behavior

Since we lean Clojure, option 1 is reasonable. But should document this explicitly.

Lower priority - current behavior is useful and matches Clojure.
