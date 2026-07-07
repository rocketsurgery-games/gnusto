---
id: gnusto-3g0
title: Improve decomposer static analysis for action arguments
type: task
priority: 4
created: '2026-01-24T17:21:43.975164-05:00'
updated: '2026-06-21T21:02:51Z'
---

The decomposer misses preconditions when behaviors check action arguments like (= ?tool @axe). Need to:
1. Filter achievers more precisely - don't match None values when we have specific targets
2. Track action argument constraints - when (= ?arg @foo) appears, infer held? @foo
3. Deeper conditional analysis - extract actual required values from cond branches
