---
id: gnusto-ntr
title: Language & runtime design tweaks
type: task
priority: 2
created: '2026-01-12T19:22:54.33576-05:00'
updated: '2026-06-20T14:53:30Z'
labels:
- lang
---

Design improvements to the Grue language and runtime before continuing LH conversion.

---
▸ 2026-06-20T14:53:30Z
LANGUAGE/RUNTIME note from Epic B page-break design (see gnusto-4ac5.4). Two potential Grue additions surfaced — capturing here, not yet committed:
1. SCENE-BREAK HINTS on (success ...): extend the existing terminator-kwarg channel (_parse_terminator_kwargs -> context['render'], same path as :render :tag) with :scene / :beat markers AND a SUPPRESS form so authored set-pieces (e.g. the alchemy ritual cutscene) can force a scene/page break, and contiguous-space moves can suppress the default room-change break. Keeps scene authority with the game author, deterministic + persisted in the effect stream.
2. DECLARED ROOM REGIONS/ZONES: group rooms into a zone so intra-zone movement does NOT trigger a scene break (contiguous space), with zero per-turn authoring and no LLM. Dovetails with the earlier 'room-global axes' note (rooms reading off-room state). A purely-programmatic alternative to LLM pacing for the common case.
Both feed gnusto-4ac5.4 (bounded comic pages). Promote to child yaks when we move from exploration to implementation.
