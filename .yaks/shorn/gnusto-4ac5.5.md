---
id: gnusto-4ac5.5
title: Expanded semantic block vocabulary (presentation intent)
type: feature
priority: 2
created: '2026-06-16T02:18:16Z'
updated: '2026-06-20T21:42:46Z'
---

Expand the LLM's content-block vocabulary so it can direct PRESENTATION INTENT, while the engine keeps ownership of geometry. Boundary: LLM = semantics + pacing + asset selection from a catalog; engine = pixels/responsiveness/degradation.

Layered onto existing blocks (narrate/speak/think/ambient/reveal/focus/scene):
- Panel ROLE: establishing | splash | inset | caption | tier-member (what kind of panel, not its pixels).
- BEAT / emphasis: aside | normal | emphasis | splash (pacing -> engine maps to panel size, comic decompression).
- GROUPING: bind blocks into a TIER (a row/sequence of small panels).
- ASSET DEPLOYMENT: a block references an available entity asset + a role (feature | inset | background). Feed the LLM the catalog of what is renderable so it chooses what to surface.
- New content kinds: SFX block (onomatopoeia lettering); possibly split narrator CAPTION from in-world NARRATE.
- Explicitly NOT a geometry DSL: no LLM-specified grids/spans/positions (token-costly, inconsistent, fights responsive layout).

Touches gnusto/agent.py (block schema + guidelines), gnusto/render.py (block types), gnusto/llm.py, and the webui renderer. Update agent docs.

---
▸ 2026-06-20T14:53:17Z
CROSS-REF (page-break / scene-break intent) — see gnusto-4ac5.4 design exploration. The expanded vocabulary MAY include a scene/page-break intent (e.g. a 'scene' role or beat=splash) that lets the LLM PROMOTE a soft page boundary to a hard scene break for emergent pacing the author did not annotate. Constraint (important): the LLM must only promote within the engine's candidate set or add emphasis — it must NOT be the sole owner of pagination, or pages stop being deterministically re-derivable from the persisted turn log (revisiting history could re-paginate) and we pay tokens every turn. This is the OPTIONAL/LATER tier of the layered authority chain; deterministic engine + Grue (success ...) hints come first.

---
▸ 2026-06-20T21:42:46Z
FIRST SLICE done (beat + sfx). Added presentation-intent foundation: (1) a BEAT pacing field (aside|normal|emphasis) on any LLM block \u2014 the LLM directs pacing, the engine maps it to presentation (emphasis = comic decompression: more air + accent border; aside = tighter/indented/dimmer); (2) an SFX onomatopoeia block (new content kind). Wired end-to-end: render.py (Beat type, beat field on blocks, Sfx dataclass + union), web.py block_to_dict (beat + sfx), llm.py (ContentBlockData type+beat, AGENT_RESPONSE_SCHEMA enum+beat property, parser validates beat to aside/emphasis, content_block_data_to_render), agent.py guidelines (sfx + beat, 'engine owns pixels' boundary), types.ts (SfxBlock + Beat + RenderableBlock.beat), BlockRenderer (route sfx + beat-* class), SfxBlock.svelte (mock-ported), test_blocks.py. Verified: pytest 745, svelte-check clean (touched files), build OK, no console errors.

REMAINING for .5 (keep shaving): panel ROLE taxonomy (establishing|splash|inset|caption|tier-member), TIER grouping (bind blocks into a row \u2014 lights up the .7 tier primitive), ASSET DEPLOYMENT (block references an entity asset + role feature|inset|background; feed the LLM the renderable catalog), splash role, possibly split narrator CAPTION from NARRATE. Each unblocks more of .6 degradation.

---
▸ 2026-06-20T22:08:20Z
SLICE 2 done (caption + splash + asset-deploy field). Design decision: rather than a generic `role` enum that fights our typed-block model, panel ROLES map onto block TYPES (establishing=room_enter, caption, splash, sfx) + an asset-DEPLOY field on image blocks. (1) CAPTION block — narrator out-of-world voice (parchment box), split from in-world NARRATE. (2) SPLASH block — full-bleed dramatic panel; features entity art when resolvable, else degrades to a TYPOGRAPHIC splash (pre-stages .6). (3) DEPLOY field (feature|inset|background) on reveal/focus to direct how the asset surfaces — LLM picks which+how, engine owns pixels. Wired end-to-end: render.py (Caption/Splash/Deploy + deploy on Reveal/Focus + union), llm.py (type enum, schema enum+deploy prop, parser validates deploy, converter), web.py block_to_dict, agent.py guidelines, types.ts (Caption/Splash/Deploy), BlockRenderer route, CaptionBlock.svelte + SplashBlock.svelte (mock-ported, real tokens not mock --font-caption). Verified: pytest 751 (+6), svelte-check clean on touched files, vite build OK.

REMAINING for .5 (keep shaving): TIER grouping (bind consecutive blocks into a desktop row — lights up .7 tier primitive); feed the LLM the RENDERABLE CATALOG (which visible entities actually have art) so asset deployment is grounded. Then shear .5.

---
▸ 2026-06-20T22:20:00Z
SLICE 3a done (renderable catalog). _build_messages now appends a "[Renderable assets — ... entity=<id>: @hacker (the hacker), ...]" line listing visible OBJECTS/CHARACTERS that actually resolve to art (room excluded; it's auto-established). New GameSession._renderable_catalog uses build_scene_context; defensive (empty on error). Grounds asset deployment so the LLM features real art, not guesses. Only added in full-agent mode (not parsing_only). Tests: tests/gnusto/test_agent_catalog.py (3). REMAINING: tier grouping, then shear.

---
▸ 2026-06-20T22:35:00Z
SLICE 3b done (tier grouping) — and SHORN. Added a `group` tag on the SMALL-panel blocks (reveal/focus/caption/sfx — tiers are rows of small panels in comic grammar; flow text is not tiered). Consecutive blocks sharing a non-empty group fold into one comic TIER: a desktop-only grid row (>=900px), stacked on mobile — engine owns the geometry, LLM only tags membership. Wired: render.py (Group + group field on the 4), llm.py (ContentBlockData.group, schema group prop, parser drops empty, converter), web.py block_to_dict, agent.py guidelines, types.ts (RenderableBlock.group), NarrativeStream (fold flat stream -> items[block|tier] in a $derived, render .tier wrapper + CSS). Tests: TestTierGroup (3). Verified: pytest 757, svelte-check clean on touched files, build OK.

.5 SHORN. Delivered the presentation-intent vocabulary: beat (pacing) + sfx (slice 1); caption (narrator, split from narrate) + splash (full-bleed, degrades typographic) + deploy field (slice 2); renderable catalog to the LLM (3a); tier grouping (3b). Boundary held throughout: LLM = semantics/pacing/asset-selection; engine = pixels/geometry/degradation. Splash's typographic fallback pre-stages .6; tiers light up the .7 primitive. Spawned ideas (see gnusto-ntr note): presentation-intent fields (beat/group/deploy) are accreting per-dataclass boilerplate — consider a shared PresentationIntent mixin; and a consolidated block-vocabulary reference doc.
