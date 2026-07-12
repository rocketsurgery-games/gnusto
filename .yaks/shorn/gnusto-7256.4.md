---
id: gnusto-7256.4
title: 'P4: de-drift renderers — declare vocabulary once, exhaustive TUI + web dispatch'
type: task
priority: 2
created: '2026-07-07T21:51:39Z'
updated: '2026-07-12T00:10:36Z'
labels:
- render
depends_on:
- gnusto-7256.1
---

Declare the block vocabulary in ONE place and derive from it: dict serialization (block_to_dict), the LLM structured-output schema, and exhaustive dispatch on BOTH renderers so a missing type is a caught error not a silent drop. TUI gains Caption/Splash/Sfx (currently omitted). Reconcile web-only treatments (EstablishingBlock/CommandBlock/EntityInset) against the canonical vocabulary. Subsumes the old ntr notes: presentation-intent mixin + consolidated block-vocab reference.

---
▸ 2026-07-08T03:34:06Z
Core done. (A) MODE FLIP: engine-authoritative text is now the DEFAULT for all models (from_game_file parsing_only None->True); LLM prose generation is opt-in via --llm-narration (hard cutover from --parse-only). Live TUI default now shows engine-authored text verbatim, no LLM prose. (B) RENDERER DE-DRIFT: TUI render_block gained Caption/Splash/Sfx branches (were silently dropped) + a text fallback else; web block_to_dict already exhaustive. Added drift-guard tests (test_tui_render): enumerate NarrativeBlock.__subclasses__ and assert every type has a factory + is handled by BOTH the TUI (non-empty output) and web block_to_dict (real type, not 'unknown'). docs/gnusto.md updated. 768 python + 477 grue pass. REMAINING/optional: deeper 'declare vocabulary once' (single registry deriving block_to_dict + LLM schema + Svelte dispatch) and reconciling web-only Svelte treatments (Establishing/Command/EntityInset) — pending user call on how far to push before testing discussion.

---
▸ 2026-07-08T04:02:48Z
Debug-formatter de-drift (user-reported): _format_compact_debug is a third result formatter that branched on the two result types (grue.repl.ActionDone for actions vs grue.runtime.ActionResult for events) and the EVENT branch omitted output + reason -> triggered-event narration (e.g. compulsion pages) rendered to the player but was missing from debug. Also both branches only printed narrate/say, dropping focus/reveal/emphasize/splash/sfx. Fix: factored output + effects printing into _debug_output_lines/_debug_effects_lines used by ALL branches (uniform, drift-proof), show output+reason for events, and label event results '[triggered event]' so their effects aren't causeless. Tests added. 770 python + 477 grue pass. Root cause is the two parallel result types + isinstance branching; noted for possible future unification.

---
▸ 2026-07-12T00:10:36Z
Finishing per user call. Core delivered + committed (9aa2481, c92bce6): engine-authoritative text is the default (parsing_only None->True; --llm-narration opt-in); TUI/web renderers de-drifted (Caption/Splash/Sfx + fallback; drift-guard test over NarrativeBlock.__subclasses__); debug formatter unified across result types. Deferred 'declare vocabulary once' registry + Svelte-side reconciliation promoted to root todo gnusto-26e7.
