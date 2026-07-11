---
id: gnusto-0bf7.1
title: Never emit a fully empty turn (idle wait shows nothing)
type: bug
priority: 2
created: '2026-07-11T14:37:31Z'
updated: '2026-07-11T14:37:31Z'
labels:
- harness
---

When an action/turn produces no output effects, the player sees a completely blank response and the LLM has nothing to react to. Observed during the elevator soft-lock: every stuck (wait) rendered zero player-facing text, making 'stuck' indistinguishable from 'nothing has happened yet' and letting the soft-lock hide. A turn that resolves with no narrative should still emit a minimal beat (e.g. 'Time passes.') so both player and model get a signal. Check the parse-only default path in agent.py where engine text is flattened to blocks.
