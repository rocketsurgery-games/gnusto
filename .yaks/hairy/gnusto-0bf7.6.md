---
id: gnusto-0bf7.6
title: Parse-only mode leaks narrative summarization + 'I'll continue narrating' priming
  into agent context
type: task
priority: 2
created: '2026-07-13T03:21:50Z'
updated: '2026-07-13T03:22:03Z'
labels:
- harness
---

---
▸ 2026-07-13T03:22:03Z
Found during Zork playthrough validation (gnusto-fa93.19), debug mode. When the action buffer exceeds ~25 actions, GameSession._maybe_summarize() drops the oldest turns and compresses them into an LLM-generated NARRATIVE (SUMMARIZE_PROMPT: 'Summarize these game turns into a brief narrative paragraph'), stored in self.summaries. _build_messages injects that as a '[Story so far:]' user turn FOLLOWED BY a canned assistant line: '(Acknowledged - I'll continue narrating from here.)'.

Problem: the system prompt and the renderable-asset catalog are correctly gated by self.parsing_only, but the summarization + story-so-far block are NOT. So in parse-only / engine-authoritative mode (the mode explicitly chosen for Infocom conversions to STOP the model fabricating):
  1. We still spend an extra LLM call generating fabricated prose for agent memory (can drift from ground truth), and
  2. We prime the agent with 'I'll continue narrating from here' -- the opposite of parse-only intent. Plausible contributor to the 'skips text / makes shit up' drift over long sessions that kicked off this whole line of work.

It is NOT player-facing (summaries feed agent context only; the text is shown solely under --debug). So this is a context-model refinement, not a crash.

Options to discuss with user before implementing:
  A. In parse-only mode, build the 'story so far' deterministically/extractively from TurnRecord.to_summary() (faithful engine outputs) instead of an LLM narrative call -- cheaper and drift-free. There is already a non-LLM fallback ('; '.join(...)) to model on.
  B. Gate/replace the '(Acknowledged - I'll continue narrating from here.)' priming line in parse-only mode (e.g. 'Acknowledged - I'll continue selecting actions.').
  C. Keep LLM summary for rich-narration mode only.
Prefer A+B. Raised to user; do not implement until they weigh in on the memory model.
