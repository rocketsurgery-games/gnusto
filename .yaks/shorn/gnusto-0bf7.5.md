---
id: gnusto-0bf7.5
title: 'Movement (go) rejects direction synonyms: ''northeast'' != stored ''ne'''
type: task
priority: 1
created: '2026-07-13T03:16:13Z'
updated: '2026-07-13T03:20:28Z'
labels:
- bug
---

---
▸ 2026-07-13T03:16:21Z
Found during Zork playthrough validation (gnusto-fa93.19). Exits store canonical tokens (north/south/east/west + ne/nw/se/sw + up/down/in/out), but _get_exit_from_room matches with exact string ==, so the agent's natural '(go northeast)' hit no-exit at NS Passage (which lists an 'ne' exit to Deep Canyon). Agent then got lost and never reached the dam.

IF convention (and Zork itself) accepts direction synonyms. Fix: engine-level normalize_direction() mapping synonyms -> canonical token (n->north, northeast->ne, u->up, inside/enter->in, ...), applied at the go choke point in _do_single (before the room :before-action check so handlers see the canonical token) and idempotently at the top of _do_go for direct callers. Normalize both sides when matching so games authored with either form work.

---
▸ 2026-07-13T03:20:28Z
FIXED. Added normalize_direction() in runtime.py (canonical map for n/s/e/w, ne/nw/se/sw, up/down, in/out + synonyms like northeast/inside/enter/exit). Applied at the go choke point in _do_single (before the room :before-action check) and in _get_exit_from_room (normalizing both sides, so it also covers get_exit/exit?/exit-to/exit-via). Regression test test_go_accepts_direction_synonyms in tests/grue/test_grue_runtime.py. Re-ran the Zork dam playthrough end-to-end: (go northeast) now reaches Deep Canyon->Dam, and the full button/wrench/bolt drain completes. 811 pytest + 688 grue-test green.
