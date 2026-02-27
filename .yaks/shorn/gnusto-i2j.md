---
id: gnusto-i2j
title: Behaviors as functions with explicit parameters
type: feature
priority: 1
created: '2026-01-11T23:30:57.559834-05:00'
updated: '2026-02-08T19:07:10.973815Z'
---

## Summary

Redesign behaviors from magic-bound expressions to explicit functions with positional parameters. This enables cleaner handling of multi-argument verbs like "give X to Y".

## Current Design

```scheme
; Behaviors are expressions with magic bindings
(behaviors
  (:give
    (cond
      ((not (held? ?object)) ...)  ; ?object magically bound - but wrong for give!
```

Dispatch: `(do :verb give :object @hacker :with @food)`

Problem: `?object` binds to the dispatch target, not the item being given.

## New Design

```scheme
; Behaviors are functions with explicit params
(behaviors
  (:give (fn (?item)
    ; ?self = @hacker (auto-bound to behavior owner)
    ; ?actor = @player (auto-bound to action performer)
    ; ?item = positional arg from (do) call
    (cond
      ((not (held-by? ?item ?actor)) ...)
```

Dispatch: `(do @hacker :give @food)`

## Auto-bound Symbols

- `?self` - The object whose behavior is being invoked (dispatch target)
- `?actor` - Who is performing the action (initially always `@player`)

## Verb Signature Consistency

All implementations of a verb must have the same parameter signature:
- `:give` → `(?item)`
- `:put` → `(?surface)` or `(?surface ?position)` with optional trailing
- `:ask` → `(?topic)`
- `:unlock` → `(?key)`
- `:examine` → `()`

## Introspection

LLM adaptation layer needs to query available behaviors:

```scheme
(behaviors @hacker)
; → ((:give (?item) "Give something to the hacker")
;    (:ask (?topic) "Ask the hacker about something"))
```

## Error Handling

If target has no behavior for the verb, return error. LLM should not call behaviors that don't exist (it introspects first).

## Migration

Hard cutover - update all existing behaviors and (do) call sites.
