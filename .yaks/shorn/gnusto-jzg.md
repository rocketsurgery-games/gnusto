---
id: gnusto-jzg
title: Generalize (fn) as a first-class lambda construct
type: feature
priority: 2
created: '2026-01-12T10:29:38.377281-05:00'
updated: '2026-02-08T19:07:11.052139Z'
---

## Problem

Currently `(fn)` in Grue is bespoke to the behavior system:
- `parse_behaviors()` expects `(fn (params) (cond ...))`
- The body MUST be a `(cond ...)` expression
- `fn` is not usable elsewhere in the language

This is confusing for users who expect `(fn)` to be a general lambda construct
in what is obviously a Lisp-family language.

## Solution

Make `(fn)` a first-class construct:
1. `(fn (params) body)` returns a callable/closure
2. Body can be any expression (not just cond)
3. Behaviors use `fn` but are evaluated normally
4. `fn` is usable anywhere (events, inline, etc.)

## Requirements

- General `fn` parsing and representation
- Closures capture lexical scope
- ExprEvaluator handles fn application
- Behaviors continue to work (now via fn evaluation)
- Remove hardcoded `cond` requirement from parse_behaviors

## Future consideration (not this PR)

Ensure fn/behaviors remain introspectable at runtime for the LLM adaptation
layer (enumerate object behaviors, their parameters, etc.). Track this as
part of the LLM adapter work.
