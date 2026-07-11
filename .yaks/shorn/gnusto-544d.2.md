---
id: gnusto-544d.2
title: Rewrite translate-zil as a current .agents/skills skill
type: task
priority: 2
created: '2026-07-11T22:53:41Z'
updated: '2026-07-11T23:01:34Z'
labels:
- tooling
- docs
- lurkinghorror
---

Rewrite ZIL->Grue translation guidance aligned to the CURRENT language: engine-authoritative output vocabulary (narrate/say/focus/reveal/emphasize/splash/sfx -- emit the real text, NOT 'capture the why'); the ZIL-faithful event-queue contract (positive=one-shot self-re-queue chain, -1/None=indefinite; cite CLOCKER); the 0-truthy gotcha (use <ZERO?>/<G?> mapping, beware (and ?floor ...)); (blocked ...) for refusals; :examine->focus, room/object :describe stay structural; remove converted ZIL comments; add grue tests as you go; file bugs in converted code as P1.

---
▸ 2026-07-11T23:01:34Z
Done in 2803f4a: .agents/skills/translate-zil/SKILL.md rewritten for current language -- engine-authoritative output vocabulary (emit real text via narrate/say/focus/reveal/emphasize/splash/sfx, NOT 'the why'), CLOCKER-faithful queue contract, 0-truthy ZIL gotcha, blocked/redirect/default, remove-comments + tests + P1 workflow.
