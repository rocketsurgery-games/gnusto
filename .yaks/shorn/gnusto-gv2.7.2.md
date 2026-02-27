---
id: gnusto-gv2.7.2
title: Standardize state dict key format
type: task
priority: 3
created: '2026-01-24T10:44:14.035001-05:00'
updated: '2026-02-08T19:07:11.069405Z'
---

State dict keys use strings like '@obj:location' but StateRef classes have different string representations. Standardize on one format for consistency between goal predicates and DOT generation.
