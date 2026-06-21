---
id: gnusto-a07e.1
title: Render :ref edges + cycle-rejecting lint
type: feature
priority: 2
created: '2026-06-21T20:29:38Z'
updated: '2026-06-21T20:29:38Z'
labels:
- render
---

Foundation. Let a render entry (room/object/event variant) declare reference edges to other asset keys (a frozen base, a character/locale plate, a portal seam, or another key). The render-manifest builder assembles the dependency graph; the same abstract-interpretation lint that guards the scene-variant explosion (grue.render) REJECTS cycles, naming the exact edge to repoint at a root.

- Surface in Grue: a :ref (and/or :base for edit-deltas) field on :render/:rdesc entries; keyword key = managed variant, string = verbatim key (mirror the existing :render keyword/string contract).
- Manifest entry gains deps: [key...]; build_render_manifest computes them.
- lint_render: detect cycles; auto-derivable DAGs (e.g. spanning tree of a visibility cluster) pass, back/cross edges must be explicit or degrade to prompt-only.
- frotz render reports the dep graph + any cycle errors (non-zero exit).

This is the cycle-breaking machinery everything else builds on.
