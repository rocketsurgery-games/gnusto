---
id: gnusto-0bf7.7
title: '''look'' tool missing from structured-output schema enum -> collapses to ''wait'''
type: task
priority: 1
created: '2026-07-13T03:30:48Z'
updated: '2026-07-13T03:32:30Z'
labels:
- bug
---

---
▸ 2026-07-13T03:30:57Z
Found during Zork deposit-loop playthrough. 'look'/'look around'/'look' all deterministically map to (wait) -> 'Time passes.'.

Root cause: ActionRequest.tool (llm.py) and PARSING_ONLY_PROMPT both include a 'look' tool, and the whole agent path supports it (_is_look_action, look branch in _execute_action, parse-only room-block emit). BUT AGENT_RESPONSE_SCHEMA.actions.items.tool.enum omits 'look' (['do_action','move','wait','recall','map','history','search']). Structured output constrains the decoder to the enum, so the model physically cannot emit 'look' and collapses it to the nearest pass-a-turn option, 'wait'. This is exactly the 'chooses wrong/no action' class from the top of this thread.

Fix: add 'look' to the enum. GAME_TOOLS (function-calling) is legacy/unused, so no change needed there. Verify look re-describes the room via the LLM harness.

---
▸ 2026-07-13T03:32:30Z
FIXED. Added 'look' to AGENT_RESPONSE_SCHEMA tool enum (+ clarified the enum description to steer away from 'wait' for looking). Regression tests in tests/gnusto/test_llm_schema.py: test_tool_enum_matches_action_request_literal (enum must equal ActionRequest.tool Literal, so neither can drift) + test_look_is_emittable. Verified via harness: 'look'/'look around' now re-describe the current room instead of 'Time passes.'. 813 pytest + 688 grue-test green.
