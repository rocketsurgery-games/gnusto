---
id: gnusto-fa93.4
title: 'Engine: deterministic darkness/light model + persistent start-events'
type: task
priority: 2
created: '2026-07-12T17:10:53Z'
updated: '2026-07-12T17:21:22Z'
labels:
- runtime
---

---
▸ 2026-07-12T17:11:03Z
Design (agreed w/ user): (1) lit?/light-source?/accessible as pure defn in builtins.grue (keyword lookups return defaults, safe). (2) Perception seam: thin Python in get_visible_objects/get_room_description consults Grue (lit? room); when dark, suppress contents + emit a customizable dark message (world :dark-message, default 'It is pitch black.'; Zork overrides w/ grue warning). Suppression is core/general; text is game-specific. (3) Persistent start-events: world :start-events (evt...) queued indefinitely at init — general facility for always-on background events (clocks/hazards/NPC interactions), motivated by 'the grue always lurks'. (4) Grue danger itself = game-specific Grue event (grue-lurks), same hazard pattern as LH freezing: per-turn, resets when lit, counts dark turns, kills at :grue-grace (default 1). Deterministic (no RNG) for frotz. Note ZIL divergence: ZIL grue strikes on movement; we count turns (cleaner grace, same event pattern).

---
▸ 2026-07-12T17:21:21Z
Done. Engine: (1) lit?/light-source?/accessible pure-Grue in builtins.grue (opt-in darkness: room :lit defaults true; relit by carried/present lit :lightable). (2) is_room_lit thin Python seam -> Grue lit?; get_room_description returns world :dark-message and get_visible_objects(for_description) returns [] when player's room unlit (listing suppressed only; accessibility/take unchanged). (3) world :start-events queues events indefinitely at init. (4) world :dark-message field. Consumer/validation: Zork grue-hazard.grue (grue-lurks event, LH-freezing-shaped, deterministic death after :grue-grace; player :dark-turns/:grue-grace), world wires :dark-message + :start-events. Tests: TestDarkness+TestStartEvents (pytest), parser field test, 5 grue-hazard.test.grue. REPL-verified: dark attic shows pitch-black+grue warning and kills after grace; lit lamp relights attic + no death. Docs: docs/grue.md 'Light and Darkness' section + fixed stale grue defeat example; translate-zil skill hazard/darkness note. 833 pytest / 531 grue-test / lint clean.
