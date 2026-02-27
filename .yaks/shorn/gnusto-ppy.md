---
id: gnusto-ppy
title: GRUE World DSL design and implementation
type: task
priority: 1
created: '2026-01-08T22:08:01.121984-05:00'
updated: '2026-02-08T19:07:10.980952Z'
depends_on:
- gnusto-ma8
- gnusto-1hn
---

Design and implement GRUE (Game Runtime for Universal Experiences), a declarative DSL for IF world definitions.

## Goals
- Declarative world definition with rooms, objects, and behaviors
- S-expression syntax for easy parsing and manipulation
- Support for:
  - Room definitions with exits, descriptions, ldesc
  - Object definitions with location, flags, properties, behaviors
  - Behavior system with (through), (take), (examine), etc.
  - Expression language for preconditions and effects
- Enable formal verification and LLM integration points
- Extraction from ZIL source via converter

## Key Features
- `:via` on exits supports any object with `(through)` behavior
- INVISIBLE flag for synthesized barrier objects
- `[NEEDS-TRANSLATION]` markers for LLM implementation agent
- Comments preserve ZIL source for reference

## Completed
- DSL parser and validator (frotzlm-a71)
- DSL runtime executor (frotzlm-9mf)
- Expression language for preconditions/effects (frotzlm-dby)
- ZIL-to-GRUE converter (frotzlm-hd4)
- Exit extraction with :via barriers (frotzlm-f1j)
- LDESC/FDESC support (frotzlm-nkx, frotzlm-q2z)

## Remaining
- State space explorer for winnability (frotzlm-38y)
- LLM latitude system (frotzlm-bgb)
- File splitting for multi-file output (frotzlm-1o5)
