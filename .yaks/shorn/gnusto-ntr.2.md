---
id: gnusto-ntr.2
title: Add match, condp, cond->, cond->> forms
type: task
priority: 2
created: '2026-01-12T21:55:34.895908-05:00'
updated: '2026-02-08T19:07:11.034629Z'
labels:
- lang
---

Add pattern matching and conditional threading forms to reduce `cond` verbosity.

## Motivation

Behavior code often has verbose nested `cond` with repeated condition checks:
```lisp
(cond
  ((and (not (has-flag? ?self LOCKED)) (not (has-flag? ?self OPEN)))
   (success :effects ((set-flag! ?self OPEN))))
  ((has-flag? ?self LOCKED)
   (blocked :reason locked))
  (true
   (blocked :reason already-open)))
```

## Proposed Forms

### 1. `match` - Pattern matching on value tuples

```lisp
(match ((has-flag? ?self LOCKED) (has-flag? ?self OPEN))
  ((false false) (success :effects ((set-flag! ?self OPEN))))
  ((true _)      (blocked :reason locked))
  ((_ true)      (blocked :reason already-open)))
```

- First argument is a list of expressions to evaluate
- Each clause is `(pattern result)`
- Pattern is a list matching positionally
- `_` is wildcard (matches anything)
- Literal values must match exactly
- Symbols bind the matched value for use in result expr

### 2. `condp` - Compare with predicate

```lisp
(condp = (get-state ?self)
  :locked  (blocked :reason locked)
  :open    (blocked :reason already-open)
  :closed  (success :effects ...))

(condp > health
  0   (defeat :reason dead)
  10  (warn "low health")
  100 (success))
```

- `(condp pred expr clauses...)`
- Each clause is `test-val result`
- Evaluates `(pred test-val expr)` for each clause
- Returns result of first truthy test

### 3. `cond->` - Conditional threading

```lisp
(cond-> initial-state
  (has-flag? ?self WET)    (add-effect (clear-flag! ?self WET))
  (held? @towel)           (add-effect (set-flag! @player DRY))
  true                     (finalize))
```

- Threads value through forms when condition is truthy
- Each clause is `test expr`
- If test passes, threads current value as first arg to expr
- Useful for building up effects/state conditionally

### 4. `cond->>` - Conditional threading (last position)

```lisp
(cond->> (list)
  (has-flag? ?self LOCKED) (cons :locked)
  (has-flag? ?self OPEN)   (cons :open))
```

- Like `cond->` but threads as last argument
- Useful for list/collection building

## Implementation Notes

- All forms are expression-level, implemented in expr.py evaluator
- `match` needs pattern compilation (wildcards, bindings, literals)
- `condp` is straightforward - evaluate predicate with each test value
- Threading macros need to track threaded value through clauses

## Examples in Context

Before:
```lisp
:open (fn ()
  (cond
    ((has-flag? ?self LOCKED) (blocked :reason locked))
    ((has-flag? ?self OPEN) (blocked :reason already-open))
    (true (success :effects ((set-flag! ?self OPEN))))))
```

After:
```lisp
:open (fn ()
  (match ((has-flag? ?self LOCKED) (has-flag? ?self OPEN))
    ((true _)      (blocked :reason locked))
    ((_ true)      (blocked :reason already-open))
    ((false false) (success :effects ((set-flag! ?self OPEN))))))
```
