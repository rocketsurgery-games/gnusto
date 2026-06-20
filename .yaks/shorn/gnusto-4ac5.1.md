---
id: gnusto-4ac5.1
title: Panel stream + frozen establishing panels (un-pin room render)
type: feature
priority: 2
created: '2026-06-16T02:17:30Z'
updated: '2026-06-20T20:12:31Z'
---

Convert the pinned room header into a frozen, point-in-time ESTABLISHING PANEL that enters the narrative stream like any other panel.

- Remove the persistent pinned room image/header from the web UI (gnusto/web.py + webui).
- Room entry emits an establishing panel (stage image + room name + description) into the stream; it does NOT track live state afterwards. Re-entering a room emits a fresh establishing panel (no scroll-back/reconciliation).
- This is the foundational refactor the rest of Epic B builds on. Other B children depend on this.
- Can proceed against placeholder art; consumes the keyed-asset + fallback contract from gnusto-eaec.2/.4 once available.

---
▸ 2026-06-20T20:12:31Z
SHORN. Un-pinned the room render into a frozen establishing panel in the stream, verified end-to-end against games/lurkinghorror (server smoke test: intro prose above, establishing panel with stage art + location label + description, no pinned header, sidebar live affordances intact).

Backend (web.py): deleted _build_preamble + _SENTENCE_END/_PREAMBLE_MAX + the re import + streamed_blocks accumulation; on room change just emit the room_enter block (frozen establishing) instead of a header-swap-with-preamble. (This also completes the DELETE half of 4ac5.3's transition machinery on the backend.)
Frontend: new EstablishingBlock.svelte (full-bleed 5:4 stage + location label + description, with a typographic no-art fallback baked in); BlockRenderer routes room_enter -> EstablishingBlock; App.svelte appends room_enter as a frozen block AND updates currentRoom for the sidebar, and the ENTIRE transition machinery is gone (pendingRoom/pendingBlocks/transitionPhase/_archive + commitRoomTransition/startRoomTransition/onFadeOut/onFadeIn/handleTransitionEnd/handleAnimationEnd); turn_complete just enables input; removed .game-content fade classes + room-fade-in keyframe from global.css; deleted RoomHeader.svelte; dropped the dead preamble field from types.ts.
Verified: svelte-check clean on touched files (one PRE-EXISTING unrelated error in ObjectDetailOverlay.svelte), vite build OK, pytest 734 passed/6 skipped.

NOTE: lands on the existing LIGHT theme; the establishing panel uses mock-derived dark chrome for its label but the page is not yet reskinned — that's 4ac5.9. The .3 delete-half is effectively done here; .3 now only needs the scene-break VISUAL treatment.
