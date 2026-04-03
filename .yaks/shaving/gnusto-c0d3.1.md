---
id: gnusto-c0d3.1
title: 'Input parsing: NL → structured actions (no generation)'
type: task
priority: 1
created: '2026-03-22T17:31:47Z'
updated: '2026-03-22T17:39:27Z'
---

Focus the local model solely on input interpretation: given game state + player text,
produce the correct action JSON. No narrative generation — let the game engine produce
all player-visible text.

This isolates the hardest small-model problem (following the agent protocol) from the
easier one (prose generation). It also lets us use grammar-constrained decoding (GBNF)
to guarantee structurally valid output — the model only needs to pick the right
action/target/verb from the visible options.

Approach:
- Strip narrative generation from the prompt entirely
- Provide visible objects, behaviors, and exits as a constrained vocabulary
- Use json_object or GBNF grammar to guarantee valid action JSON
- Game engine handles all text output (room descriptions, action results, etc.)
- Compare 4B vs 8B accuracy on a test set of NL→action pairs
