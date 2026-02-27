---
id: gnusto-bfm
title: Implement S-expression world parser for new DSL format
type: task
priority: 1
created: '2026-01-09T18:00:31.59058-05:00'
updated: '2026-02-08T19:07:10.977827Z'
---

Parse GRUE (.grue) world format into WorldDefinition structures. Uses pure S-expression format (see docs/grue.md). Key features: (1) Clojure-style keyword args (:key value), (2) room/object/behaviors forms, (3) Case-based behavior matching. Start with examples/outside-door.grue as test case. Implementation goes in grue/parser.py.
