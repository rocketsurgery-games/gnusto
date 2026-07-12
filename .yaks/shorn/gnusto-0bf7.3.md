---
id: gnusto-0bf7.3
title: 'Thread event name into debug output ([event: <name>])'
type: task
priority: 2
created: '2026-07-11T14:37:38Z'
updated: '2026-07-12T00:27:12Z'
labels:
- harness
- debug
---

Triggered events render as '[triggered event]' / '[EVENT: event]' with no name in debug mode. Diagnosing the elevator soft-lock required reading source to tell which of three events was firing. Thread the event name from runtime.process_events (it iterates self.state.queues keys) through the ActionResult so the compact debug formatter can show '[event: elevator-door-opens]'. Same gap flagged in the gnusto-7256.4 handoff; this bug is a concrete argument for closing it.
