---
id: gnusto-c0d3
title: Research alternative smaller language models for language handling
type: task
priority: 4
created: '2026-03-18T00:55:29Z'
updated: '2026-06-21T20:55:30Z'
---

Find a local alternative we can use for handling language parsing, comprehension, and generation. The smaller the better, and we should be willing to fine-tune or otherwise specialize the model for the IF domain in general, and possibly to each individual game.

We should look for models that can realistically run on a consumer GPU with room to spare. And that can produce a reasonable token/s rate for quick responses. This likely means a small, specialized model.

## Progress

**Infrastructure (done):**
- MLX integration via `mlx-lm`, `--model local` CLI flag
- litellm → local OpenAI-compatible server pipeline works end-to-end
- `/no_think` injection + `<think>` tag stripping for Qwen3
- `json_object` mode for local models (MLX doesn't support `json_schema`)
- `GRUE_LLM_API_BASE` env var, `api_base` in LLMConfig
- `mlx` optional dependency group in pyproject.toml
- Docs updated in gnusto.md

**Findings from first test (Qwen3-4B-4bit):**
- Produces valid JSON matching AgentResponse schema
- Does NOT reliably follow the agent protocol (narrates without executing actions)
- Hallucinates game state instead of grounding in actual state
- Chinese token leakage at 4-bit quantization (Alibaba training data)
- Conclusion: 4B base model needs fine-tuning OR a simpler task scope

**Next:** Try 8B, then focus on input-parsing-only mode (c0d3.1).
