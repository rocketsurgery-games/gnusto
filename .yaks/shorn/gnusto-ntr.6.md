---
id: gnusto-ntr.6
title: Add top-level (def) and improve (defn)
type: task
priority: 2
created: '2026-01-13T22:48:24.118734-05:00'
updated: '2026-02-08T19:07:11.032997Z'
labels:
- lang
---

Added two language improvements:

1. **Top-level (def name value)**: Defines immutable constants accessible throughout the world.
   - Added `constants` dict to GrueWorld
   - Constants are evaluated lazily on first access
   - Example: `(def floor-names '("basement" "first floor" ...))`

2. **Improved (defn) to support docstrings and multiple body expressions**:
   - Clojure-style: `(defn name "docstring" (params) body)`
   - Scheme-style: `(defn name (params) "docstring" body)`
   - Multiple body expressions wrapped in implicit (do ...): `(defn name (params) expr1 expr2)`
