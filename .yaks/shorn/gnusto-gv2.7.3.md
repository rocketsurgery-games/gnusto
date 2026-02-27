---
id: gnusto-gv2.7.3
title: Investigate plug prep defeat states
type: bug
priority: 3
created: '2026-01-24T10:44:14.254245-05:00'
updated: '2026-02-08T19:07:11.067941Z'
---

The plug prep subproblem has 2 defeat states (s46, s47) where high-voltage is in input-socket while input-cable is also there. These may indicate a game logic bug where the socket can accept two cables simultaneously, or an exploration issue.
