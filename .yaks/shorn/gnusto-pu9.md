---
id: gnusto-pu9
title: Revisit agent context length management
type: task
priority: 3
created: '2026-01-19T14:15:34.175717-05:00'
updated: '2026-02-08T19:07:11.072307Z'
---

Manage agent context to prevent overflow while maintaining conversational coherence.

## Strategy

### 1. Ephemeral State (drop aggressively)
- Game state snapshots are only relevant for current turn
- Don't persist state in message history - inject fresh at each iteration
- History only keeps narrative/conversational content

### 2. Tiered Conversation Compaction
- **Recent (last ~5 turns)**: Full detail - player command, tool calls, results, narrative
- **Medium (5-20 turns ago)**: Summarized - "Player went to kitchen, took carton"
- **Old (20+ turns)**: High-level only - "Explored CS building, solved hacker puzzle"

Compaction can be lazy (when context tight) or proactive (after N turns).

### 3. Separate Knowledge Base (see follow-up task)
Agent maintains persistent notes about discovered rooms, objects, NPCs.
This lets conversation history be windowed aggressively while agent stays informed.

## Implementation Steps
1. Stop persisting game state in message history
2. Add token counting to detect when compaction needed
3. Implement tiered summarization of old turns
4. Add max message count as safety valve

## References
- Agentic loop: src/frotz/agent.py:process_input()
- Related: frotzlm-3up (original agentic loop)
