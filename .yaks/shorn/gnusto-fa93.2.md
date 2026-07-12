---
id: gnusto-fa93.2
title: First-class blocked-exit message form (:blocked) on room exits
type: task
priority: 2
created: '2026-07-12T16:24:56Z'
updated: '2026-07-12T16:28:44Z'
labels:
- lang
---

---
▸ 2026-07-12T16:28:44Z
Done. Added first-class :blocked message-only exit form. forms.py: GrueExit.blocked, :to optional, :to/:blocked mutually exclusive. runtime.py: _get_exit_from_room returns (to,via,blocked); _do_go returns (blocked :message ...) for message exits; get_exits filters out non-traversable blocked exits. frotz/explorer.py skips blocked exits in action enumeration. Tests: parser (2) + runtime (1). Docs: docs/grue.md exits section; translate-zil SKILL (room example + pitfall bullet). Full suites green (502 grue-test, 826 pytest).
