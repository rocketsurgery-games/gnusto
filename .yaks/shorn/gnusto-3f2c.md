---
id: gnusto-3f2c
title: 'Parse-only: model fabricates argument values and batches dependent multi-step
  actions'
type: task
priority: 3
created: '2026-07-12T01:27:04Z'
updated: '2026-07-12T01:30:51Z'
labels:
- harness
---

---
▸ 2026-07-12T01:27:11Z
Found while playing the walkthrough via the LLM harness. On input 'login with username xyzzy' the model emitted BOTH (do @pc :login xyzzy) AND (do @pc :password xyzzy) in one turn -- batching a dependent action (password validity depends on login result) AND fabricating a password value the player never gave. The game correctly rejected it, but the login mini-game then cascaded into confusion. Two prompt gaps: (1) no explicit 'never invent argument values (passwords/codes/names) not provided by the player' rule; (2) rule 5 (don't batch dependent actions) not strong enough. Fix in PARSING_ONLY_PROMPT.
