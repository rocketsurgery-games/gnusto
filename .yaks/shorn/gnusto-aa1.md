---
id: gnusto-aa1
title: Migrate game code from :flags to :properties
type: task
priority: 2
created: '2026-01-17T23:59:21.101-05:00'
updated: '2026-02-08T19:07:11.010852Z'
depends_on:
- gnusto-m95
---

Convert all game files from :flags syntax to boolean properties.

Before: `:flags (TAKEBIT FOODBIT OPENABLE)`
After: `:properties (:takeable true :food true :openable true)`

This is mechanical but touches many files. Run full test suite after.
