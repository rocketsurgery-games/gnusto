---
id: gnusto-pln6
title: Unified LLM narration and object resolution
type: bug
priority: 2
created: '2026-01-25T19:02:30.25583-05:00'
updated: '2026-02-08T14:08:45.043121-05:00'
---

## Problem

The current agent flow has two issues:

1. **Input**: LLM can't resolve natural language object references (e.g., "ask hacker about his keyring" → `@keyring`)
2. **Output**: Raw Grue responses are streamed directly (e.g., `@hacker: "This is a master key." revealed master key`) rather than being narrated by the LLM

## Design: Unified LLM Narration

### Current Flow
```
User input → LLM decides action(s) → Tool calls → Raw results streamed → Final LLM summary
```

### Proposed Flow
```
User input → LLM decides action → Tool call → LLM narrates result → (repeat or stop) → Done
```

### Key Changes

**1. Per-step narration** (not just final summary)
- After each tool result, LLM produces a narrative fragment
- Preserve authored dialogue verbatim, frame exposition thoughtfully
- Results accumulate in history for context

**2. Early stopping**
- LLM can choose to stop a planned sequence if something unexpected happens
- Return control to player with "what would you like to do?" framing

**3. Better object resolution** (original issue)
- Include object ID↔description mapping prominently in context
- LLM can reference objects naturally in its narration

**4. Image awareness**
- Pass available images with metadata (what they depict, when relevant)
- LLM can request image display as part of narration
- Simple filter structure for state-dependent image selection

### Implementation Chunks

1. Refactor tool result handling - Stop streaming raw results, accumulate for LLM
2. Per-step narration prompt - Ask LLM to narrate each result, with quote-preservation guidance
3. Early stopping mechanism - Let LLM signal "stop sequence, need player input"
4. Image catalog - Simple structure listing available images with descriptions
5. Image selection in narration - LLM can include image references in output
