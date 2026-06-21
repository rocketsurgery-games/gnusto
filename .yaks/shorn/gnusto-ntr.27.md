---
id: gnusto-ntr.27
title: Factor shared presentation-intent fields out of the block dataclasses
type: task
priority: 3
created: '2026-06-20T23:52:00Z'
updated: '2026-06-20T23:52:00Z'
---

The LLM presentation-intent fields (`beat`, `group`, `deploy`) accreted as
per-dataclass boilerplate across the render blocks during gnusto-4ac5.5: each
new intent meant ~9 dataclass edits + ~9 `block_to_dict` branches + parser /
converter / types.ts churn. Factor the shared shape out so the model is easier
to follow and adding the next intent field is a single edit.

Plan:
- A `NarrativeBlock` base dataclass carrying the universal intent fields
  (`beat`, `group`) as keyword-only, inherited by the 9 LLM-emitted narrative
  blocks. (`deploy` stays on the entity-bearing blocks reveal/focus.)
- DRY `web.block_to_dict` with an `_intent(block)` helper spread into the
  narrative branches.
- DRY `llm.content_block_data_to_render` with a shared `intent` kwargs dict.
- Keep the JSON contract stable (each narrative block dict still carries its
  `beat`/`group`); `group` widens from the 4 small-panel blocks to all
  narrative blocks (uniform; tiers are still guided to small panels).

---
▸ 2026-06-21T00:05:00Z
SHORN. Introduced a NarrativeBlock base dataclass carrying the shared presentation-intent fields (beat, group) as keyword-only (so concrete blocks keep positional content fields without default-ordering conflicts); the 9 LLM-emitted narrative blocks now inherit it (deploy stays on reveal/focus). DRY'd web.block_to_dict via an _intent(block) helper spread into each branch, and llm.content_block_data_to_render via a shared `intent` kwargs dict. JSON contract stable; group WIDENED from the 4 small-panel blocks to all narrative blocks (uniform — tiers still guided to small panels in the prompt). Adding the next universal intent field is now ~1 edit (base) + the helper already spreads it. System blocks (RoomEnter/Image/…) are correctly NOT NarrativeBlock. Tests: TestNarrativeBlockBase (3). Verified: pytest 765, svelte-check clean on touched files, build OK.
