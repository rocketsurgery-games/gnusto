---
id: gnusto-d6d6
title: 'Transcript generator: human-readable NL-in/engine-out playthrough export'
type: task
priority: 3
created: '2026-07-13T15:32:52Z'
updated: '2026-07-13T15:33:15Z'
labels:
- tooling
---

---
▸ 2026-07-13T15:33:02Z
scripts/make_transcript.py drives the real parse-only harness (NL in -> engine-authored text out) over a scripted walkthrough and emits a clean, human-readable transcript (> command, then the game's output; no debug tool calls, no LLM prose). Mirrors the front-ends: shows the destination room on change, stops at death/victory. Verified end-to-end on Zork I ('recover your first treasure' arc: mailbox -> house -> gear up -> descend -> Gallery painting -> chimney home -> bank it in the trophy case). Surfaced+fixed gnusto-0bf7.11 (render_block_to_text RoomEnter crash) along the way. Sample output not committed (LLM-nondeterministic); can add one as a reference artifact if wanted.
