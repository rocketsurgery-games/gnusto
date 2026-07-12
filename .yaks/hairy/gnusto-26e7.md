---
id: gnusto-26e7
title: 'Declare block vocabulary once: single registry -> block_to_dict + LLM schema
  + Svelte dispatch'
type: task
priority: 3
created: '2026-07-12T00:10:23Z'
updated: '2026-07-12T00:10:23Z'
labels:
- render
---

Deferred tail of gnusto-7256.4 (P4). The renderers are de-drifted and exhaustive (TUI + web block_to_dict, drift-guard tests), and engine-authoritative text is the default. NOT done (deferred by user call to finish .4): (1) a single source-of-truth block-vocabulary registry that derives block_to_dict, the LLM structured-output schema (llm.py AGENT_RESPONSE_SCHEMA), and a Svelte manifest, so a new block type can't be added in one place and silently dropped elsewhere; (2) reconcile web-only Svelte treatments (EstablishingBlock/CommandBlock/EntityInset) + the Svelte BlockRenderer against the canonical vocabulary (the Python drift-guard does NOT cover the Svelte side -- a missing component silently drops on web). Pick up when the renderer surface next changes.
