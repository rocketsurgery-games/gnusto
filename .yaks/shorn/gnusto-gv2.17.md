---
id: gnusto-gv2.17
title: Audit LH behaviors for missing held? checks
type: task
priority: 2
created: '2026-01-23T11:51:36.424246-05:00'
updated: '2026-02-08T19:07:10.998677Z'
---

Same issue we fixed in testgame guard - behaviors may check (= ?obj @foo) without explicit (held? @foo), preventing back-prop from finding preconditions.
