---
id: gnusto-6ba8
title: Player knowledge graph
type: feature
priority: 2
created: '2026-03-01T18:00:59Z'
updated: '2026-03-02T02:34:51Z'
commit: 1ae7fff
---

A graph-based model of accumulated player knowledge. Foundation for history/journal (gnusto-dae1), auto-mapping (gnusto-8c77), entity recall, and agent context tools.

Three core structures: KNode (entities encountered), KEdge (observed relationships), KEvent (chronological event log). Query interface exposed as agent tools: recall, map, history, search. Populated via observe_turn() hook in process_input(). Represents player knowledge not ground truth — staleness is a feature. Serializes with save/load.
