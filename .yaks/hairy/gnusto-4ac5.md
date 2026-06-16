---
id: gnusto-4ac5
title: Graphic-novel panel stream UI
type: task
priority: 2
created: '2026-06-16T02:16:06Z'
updated: '2026-06-16T02:16:16Z'
---

Completely rethink the gnusto web UI around a graphic-novel PANEL STREAM, removing traditional pinned-panel chrome in favor of a comic presentation throughout.

Core moves (all agreed in design discussion):
- UN-PIN the room render. The establishing shot becomes a FROZEN, point-in-time panel in the stream, not a live header. This dissolves the 'compute the single correct current-state room image' problem.
- Separate concerns, not widgets: live ground-truth (where am I / what's here / affordances) vs frozen narrative history. Keep the distinction; render the live side in comic idiom, mostly SUMMONABLE on demand rather than persistently pinned.
- Lean CHROME-LESS: navigation cues embedded into panels (exit captions/hotspots at panel edges); inventory = summonable 'satchel' comic spread (reuses movable-object assets); map = summonable inked map page + optional minimal floating locator. Small floating affordances are OK when appropriate. The one persistent in-world element is the command input.
- Player commands become CAPTION PANELS in the stream (helps continuity + immersion).
- Continuity between rooms falls out for free: the panels that got you here are right above the new establishing panel. Delete special-cased transition plumbing; keep only a scene-break visual treatment.
- Bounded comic PAGES over the existing turn history (knowledge graph / journal), not infinite scroll: scroll within a bounded page, page-flip between pages, mount current +/- neighbors. Pages are a VIEW over the turn log, not a new store.

Geometry: WEBTOON-style vertical reflow is the responsive base 'spine'; print-style multi-panel tiers are a desktop-only progressive enhancement.

Semantic layer: expand the existing LLM block vocabulary (narrate/speak/think/ambient/reveal/focus/scene) so the LLM directs PRESENTATION INTENT — panel role, beat/emphasis, grouping into tiers, and deployment of available assets — while the ENGINE owns geometry, responsiveness, and degradation. Boundary: LLM = semantics + pacing + asset selection from a catalog; engine = pixels. 'No image' degrades to a typographic/caption panel, never to broken.

B can proceed against placeholder art; it only needs the keyed-asset + fallback contract from gnusto-eaec late. Auto-map (gnusto-8c77) becomes the backbone of the summonable map.
