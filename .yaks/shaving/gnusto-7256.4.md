---
id: gnusto-7256.4
title: 'P4: de-drift renderers — declare vocabulary once, exhaustive TUI + web dispatch'
type: task
priority: 2
created: '2026-07-07T21:51:39Z'
updated: '2026-07-08T03:34:06Z'
labels:
- render
depends_on:
- gnusto-7256.1
---

Declare the block vocabulary in ONE place and derive from it: dict serialization (block_to_dict), the LLM structured-output schema, and exhaustive dispatch on BOTH renderers so a missing type is a caught error not a silent drop. TUI gains Caption/Splash/Sfx (currently omitted). Reconcile web-only treatments (EstablishingBlock/CommandBlock/EntityInset) against the canonical vocabulary. Subsumes the old ntr notes: presentation-intent mixin + consolidated block-vocab reference.

---
▸ 2026-07-08T03:34:06Z
Core done. (A) MODE FLIP: engine-authoritative text is now the DEFAULT for all models (from_game_file parsing_only None->True); LLM prose generation is opt-in via --llm-narration (hard cutover from --parse-only). Live TUI default now shows engine-authored text verbatim, no LLM prose. (B) RENDERER DE-DRIFT: TUI render_block gained Caption/Splash/Sfx branches (were silently dropped) + a text fallback else; web block_to_dict already exhaustive. Added drift-guard tests (test_tui_render): enumerate NarrativeBlock.__subclasses__ and assert every type has a factory + is handled by BOTH the TUI (non-empty output) and web block_to_dict (real type, not 'unknown'). docs/gnusto.md updated. 768 python + 477 grue pass. REMAINING/optional: deeper 'declare vocabulary once' (single registry deriving block_to_dict + LLM schema + Svelte dispatch) and reconciling web-only Svelte treatments (Establishing/Command/EntityInset) — pending user call on how far to push before testing discussion.
