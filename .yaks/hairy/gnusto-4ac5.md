---
id: gnusto-4ac5
title: Graphic-novel panel stream UI
type: task
priority: 2
created: '2026-06-16T02:16:06Z'
updated: '2026-07-11T14:28:34Z'
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

---
▸ 2026-06-20T23:45:00Z
EPIC B HERD STATUS. Shorn this pass: .4 (bounded comic pages — lean client-side pagination over the in-memory stream), .5 (full presentation-intent vocabulary: beat/sfx + caption/splash + asset-deploy field + renderable catalog + tier grouping), .6 (graceful degradation: EntityInset specimen-plate + caption-inset/typographic fallbacks + keyed-asset contract), .9 (per-game theme.css loader; dark reskin + palette single-source already done). With .1/.3/.7/.8/.10/.11 previously shorn, the ONLY remaining child is .2 (comic-idiom live state). Parent stays SHAVING because .2 is BLOCKED on the auto-map (gnusto-8c77 -> gnusto-6ba8) — a separate track outside this herd. See .2 for the satchel carve-out (independent of 8c77, can build on EntityInset). Ideas captured on gnusto-ntr (presentation-intent mixin; block-vocab reference doc). Deferred follow-ons noted on the shorn children: dae1-backed page history + Grue/LLM scene-break hints (.4), per-game lettering font asset (.9), deploy=background rendering (.6).

---
▸ 2026-06-21T01:45:00Z
EPIC STATUS UPDATE. The panel-stream UI MVP is delivered end-to-end. ALL original children shorn (.1 .2 .3 .4 .5 .6 .7 .8 .9 .10 .11). .2 (comic-idiom live state) landed this pass: click->prefill + deleted the action-menu experiment; summonable satchel; and the LIVE-ONLY "column vs frame" rail (room-name locator + ways-out exits + here objects), all live-verified. Also did ntr.27 (presentation-intent NarrativeBlock base — DRY cleanup). REMAINING under the epic = follow-ons/enhancements, not core: .2.1 map page (BLOCKED on auto-map 8c77), .2.2 spatial edge-exits (held for visual iteration), .12 dae1-backed page history, .13 scene-break authority (Grue/LLM), .14 per-game lettering font, .15 deploy=background. Parent stays SHAVING until those resolve. Suites green: pytest 765, grue-test 477, svelte-check 0/0, build OK.
