---
id: gnusto-4ac5.5
title: Expanded semantic block vocabulary (presentation intent)
type: feature
priority: 2
created: '2026-06-16T02:18:16Z'
updated: '2026-06-20T14:53:17Z'
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
