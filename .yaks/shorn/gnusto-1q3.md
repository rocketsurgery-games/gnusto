---
id: gnusto-1q3
title: Define movement (go) as Grue default behavior
type: task
priority: 2
created: '2026-01-11T01:19:06.619378-05:00'
updated: '2026-02-08T19:07:11.058767Z'
---

Move the _do_go() movement logic from Python into defaults.grue.

## Challenges
- Need new predicates: `exit?`, `exit`, `exit-via` to query room exits
- Need action dispatch from within behavior (the :via door case)
- _do_go() has complex logic for dispatching to door's 'through' behavior

## Example Grue syntax (hypothetical)
```lisp
(default go
  (case (not (exit? ?actor ?direction))
    :outcome blocked :reason no-exit)
  (case (exit-via? ?actor ?direction)
    :outcome default
    :action (do :verb through :object (exit-via ?actor ?direction)))
  (case true
    :outcome success
    :effects ((move! ?actor (exit ?actor ?direction))
              (inc! moves))))
```

## Depends on
- frotzlm-eji (now completed for take/drop)
