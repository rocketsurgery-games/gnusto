---
id: gnusto-gv2.11
title: Handle circular prerequisites in constraint hierarchy
type: task
priority: 3
created: '2026-01-21T18:05:19.461516-05:00'
updated: '2026-02-08T19:07:11.070857Z'
---

Circular prerequisites appear in the constraint hierarchy:

Example: cell-door_open has prerequisite groups including [cell-door_open] (from :close behavior's blocking condition). This is technically correct - you can't close a door that's already closed - but creates a self-loop.

Issues this could cause:
- Infinite loops in tree traversal (mitigated by visited sets)
- Confusing constraint descriptions
- Incorrect satisfiability analysis

Options:
A) Filter out self-referential prerequisites during hierarchy building
B) Detect and mark circular constraints specially
C) Improve blocking condition analysis to distinguish 'already done' from 'prerequisite'

Low priority - current code handles cycles via visited sets, but the data model is semantically confusing.
