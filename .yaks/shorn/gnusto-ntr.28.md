---
id: gnusto-ntr.28
title: 'Agent correctness: restore Sonnet default, enrich parse-only, curb fabrication'
type: task
priority: 1
created: '2026-07-03T23:46:13Z'
updated: '2026-07-03T23:55:53Z'
labels:
- runtime
- agent
---

Two-month drift traced to commit c6a885c switching the default model Sonnet 4 -> Haiku 4.5 (temporary, to conserve Claude Max limits). Weak model on the agentic loop => wrong/no actions, ignores blocked/unknown results, confabulates outcomes. Panel-stream prompt bloat (4ac5.5 + ntr.27) amplified it.

Near-term correctness pass (Option A, decided with user):
1. Restore default model to anthropic/claude-sonnet-4-20250514 in LLMConfig; keep Haiku reachable via a 'haiku' alias (+ 'sonnet') in MODEL_ALIASES.
2. Enrich parsing-only _blocks_from_results: derive presentation from engine result structure (examine-family verbs on a renderable target -> Focus(entity=...) to surface art; say -> Speak; narrate/reason/blocked/error -> Narrate). Engine owns ALL text; model never authors prose in this mode.
3. Keep parsing-only OFF by default for strong external models; add a --parse-only opt-in flag plumbed through __main__.
4. Add an anti-fabrication section to the full-agent SYSTEM_PROMPT: emit the game's own text faithfully, never invent outcomes, stop + needs_player_input on blocked/error, summarize multi-step engine output rather than embellishing.

---
▸ 2026-07-03T23:55:43Z
Done. Restored default model to claude-sonnet-4-20250514 in LLMConfig (was haiku via c6a885c, a temporary rate-limit measure). Added 'sonnet'/'haiku' aliases to MODEL_ALIASES. Added anti-fabrication 'Faithfulness' section to full-agent SYSTEM_PROMPT (relay engine outcomes, stop on blocked/error, don't invent). Enriched parse-only _blocks_from_results: examine-family verb on an entity with resolvable art -> single Focus panel (deploy=feature); say -> Speak; blocked/error/narrate/reason -> Narrate; engine owns ALL text. Added --parse-only flag plumbed __main__ -> run_tui/SimpleTUI and run_server/create_app/websocket (off by default for strong models; auto-on for local). New tests/gnusto/test_parse_only_blocks.py (9 cases). Full suite: 744 passed, 6 skipped. Docs: docs/gnusto.md model aliases + full-agent-vs-parse-only section. Diagnostics seen are pre-existing pyright strictness (same profile as test_agent_catalog + untouched content_block_data_to_render/OAuth patch), not from this change. Follow-up idea (not filed): Option B two-pass 'arrange verbatim' presentation if rule-based panels feel flat.
