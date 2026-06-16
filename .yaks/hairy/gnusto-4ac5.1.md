---
id: gnusto-4ac5.1
title: Panel stream + frozen establishing panels (un-pin room render)
type: feature
priority: 2
created: '2026-06-16T02:17:30Z'
updated: '2026-06-16T02:17:30Z'
---

Convert the pinned room header into a frozen, point-in-time ESTABLISHING PANEL that enters the narrative stream like any other panel.

- Remove the persistent pinned room image/header from the web UI (gnusto/web.py + webui).
- Room entry emits an establishing panel (stage image + room name + description) into the stream; it does NOT track live state afterwards. Re-entering a room emits a fresh establishing panel (no scroll-back/reconciliation).
- This is the foundational refactor the rest of Epic B builds on. Other B children depend on this.
- Can proceed against placeholder art; consumes the keyed-asset + fallback contract from gnusto-eaec.2/.4 once available.
