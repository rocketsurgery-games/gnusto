---
id: gnusto-b4m
title: Add quote and keyword-as-function to Grue
type: task
priority: 2
created: '2026-01-12T17:51:08.883069-05:00'
updated: '2026-02-08T19:07:11.03987Z'
---

Add two fundamental Lisp features to Grue:

## 1. Quote syntax
- `'expr` or `(quote expr)` returns expr unevaluated as data
- `'(foo bar)` → the list (foo bar), not a function call
- `'@hacker` → the symbol @hacker

## 2. Keywords as functions (Clojure-style)
- `(:key obj)` looks up :key on obj
- Works for objects: `(:fdesc @pc)` → "A really whiz-bang pc..."
- Works for quoted maps: `(:foo '(:foo "bar"))` → "bar"
- Optional default: `(:missing obj "default")` → "default"

This enables clean access to object attributes without special syntax.

References:
- https://clojure.org/guides/learn/hashed_colls
- https://blog.mrhaki.com/2020/06/clojure-goodness-keyword-as-function.html
