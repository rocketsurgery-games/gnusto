---
id: gnusto-7256
title: 'Engine-authoritative output: one game-authored block stream'
type: task
priority: 1
created: '2026-07-07T21:51:19Z'
updated: '2026-07-12T00:10:36Z'
labels:
- runtime
- render
- lang
---

Reframe the block vocabulary (narrate/say/describe/focus/reveal/emphasize/splash/sfx) as the semantic contract between what-happened and how-it's-shown, authored primarily by the GAME (grue effects) and optionally the LLM (:generate, later), interpreted by each renderer as presentation. Today the vocabulary is defined in 4 drifting places (render dataclasses, tui isinstance chain [silently missing Caption/Splash/Sfx], web block_to_dict, svelte components) and game text is scattered across output effects + terminator context (:message x471, :describe->:context((description)) x123, :hint x4, :transition, :page/:stage) rendered by two drifting formatters (_format_action_result vs _blocks_from_results, the latter with an 'if not blocks' fallback that drops text). Goal: one ordered block stream, one construction path, exhaustive renderers, engine text authoritative; Lurking Horror migrated as the canonical Infocom-conversion reference. Decisions locked with user: vocabulary set as above; room-describe stays structural (establishing panel) while object-describe/examine -> Focus; keep effects simple (no inline :beat/:deploy/:group yet); new epic (not under the shorn gnusto-ntr).

---
▸ 2026-07-12T00:10:36Z
Epic complete. P1-P3 (unified block construction, output-effect vocabulary, full LH migration) + P4 (renderer de-drift, engine-authoritative default) all shorn. P5 (:generate) promoted to root gnusto-9f40; deferred vocab-registry/Svelte reconciliation to root gnusto-26e7; event description->narrate straggler tracked as gnusto-b1f2. Engine is now the author of record; the LLM parses input and does not write prose by default.
