---
id: gnusto-d4ui.10
title: LLM-suggested actions
type: task
priority: 3
created: '2026-02-25T18:00:00Z'
updated: '2026-02-25T18:00:00Z'
---

Use an LLM to generate contextual action suggestions based on current game state,
giving players discoverable options beyond the behavior menu.

## Open questions

- **Trigger:** After each turn? On input focus? On idle?
- **Presentation:** Chips above the input bar? Dropdown? Inline ghost text?
- **Latency:** Suggestions need to feel instant. Sidecar call with a small/fast model?
  Pre-generate during the agent's turn? Cache per room state?
- **Scope:** Just verbs+targets from visible entities, or creative suggestions
  ("maybe try searching the desk")?
- **Relationship to behavior menus:** Complement (suggestions are broader/fuzzier,
  menus are precise)? Or eventually replace menus for a more fluid feel?

## Simple autocomplete (from d4ui.3)

State-driven typeahead for entity names, directions, and common verbs could be a
stepping stone or a separate lightweight feature. Decide whether to bundle it here
or keep it in d4ui.8 (input improvements).
