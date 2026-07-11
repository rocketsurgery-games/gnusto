---
id: gnusto-0bf7.4
title: 'Drop ''description: None'' noise in compact debug formatter'
type: task
priority: 3
created: '2026-07-11T14:37:39Z'
updated: '2026-07-11T14:37:39Z'
labels:
- harness
- debug
---

Events with no output text render a literal 'description: None' line in the compact debug formatter (_format_compact_debug / _debug_output_lines in agent.py). Cosmetic but noisy. Suppress None/empty output fields instead of printing them.
