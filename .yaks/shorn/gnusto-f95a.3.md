---
id: gnusto-f95a.3
title: Elevator door narration suppressed at basement (floor 0 is falsy)
type: bug
priority: 3
created: '2026-07-11T14:58:01Z'
updated: '2026-07-12T00:01:23Z'
labels:
- lurkinghorror
- elevator
---

At the basement (floor 0), the elevator door open/close narration is missing. elevator-here? in elevator.grue does (and ?floor ...) where ?floor is the floor number; Grue treats 0 as FALSY (confirmed: (if 0 ...) takes the else branch), so at floor 0 elevator-here? returns falsy and the description is nil. Effect is cosmetic (doors still open/close correctly; only the 'doors slide open/closed' text is dropped at the basement). Fix: test the floor explicitly, e.g. (and (not (nil? ?floor)) ...) or compare against the room floor. NOTE: this is a symptom of a broader language question -- Grue treats 0 as falsy while Clojure treats 0 as truthy. Flagged to the user for a language-design decision (see gnusto-aab0 discussion).

---
▸ 2026-07-12T00:01:23Z
Fixed by gnusto-be0a (145995d): elevator-here? does (and ?floor ...); with 0 now truthy, the basement (floor 0) narration ('doors slide open/closed') appears. Verified via grue-repl ride to basement.
