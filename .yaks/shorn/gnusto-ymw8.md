---
id: gnusto-ymw8
title: Implement progressive history summarization
type: task
priority: 2
created: '2026-02-08T16:50:46.535111-05:00'
updated: '2026-02-08T18:14:41.211966-05:00'
---

Implement the tiered history + progressive summarization design for agent context management.

## Design (see docs/gnusto.md)

Three-tier structure:
- **Recent** (N turns): Full detail in conversation history
- **Pending** (0-N turns): Full turns waiting to be batched
- **Summaries**: Narrative blocks from LLM summarization

When pending buffer fills:
1. Call LLM to summarize the N turns into narrative
2. Preserve: room context, objects found, NPC interactions, key events
3. Prepend to summaries list, clear buffer

## Implementation

- [ ] Add `summaries: list[str]` to GameSession
- [ ] Change "medium" tier to pending buffer semantics
- [ ] Add summarization LLM call when buffer fills
- [ ] Update `_build_messages` to include summaries
- [ ] Update save/load to persist summaries
- [ ] Tune parameters (batch size, summary prompt)

## Consolidates
- gnusto-c5b (LLM-generated narrative) - agent interprets faithfully, stitches coherently
- gnusto-8eu (Note-taking) - knowledge embedded in summaries
- gnusto-bgb (LLM latitude) - conservative approach works for now
