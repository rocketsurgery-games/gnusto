---
id: gnusto-4ac5.10
title: Remove dead refs/renders image-serving plumbing (eaec leftover)
type: task
priority: 2
created: '2026-06-20T14:53:57Z'
updated: '2026-06-20T14:55:43Z'
---

Prep cleanup for Epic B. The static-asset flattening in gnusto-eaec.4 made assets flat in games/<game>/assets/ (no refs/ vs renders/ split) and the UI now loads art via the /assets/ StaticFiles mount (resolve_asset_key -> /assets/<key>). But web.py still defines a dead /renders/{path} endpoint (serve_rendered_image) that probes assets/renders, assets/renders/cache, and assets/refs — directories that no longer exist. Verified: no frontend or backend reference to /renders/ except the endpoint's own definition; no renders/ or refs/ dirs remain under games/. Action: delete the endpoint. Pure dead-code removal, no behavior change.

---
▸ 2026-06-20T14:55:43Z
SHORN. Removed the dead /renders/{path} endpoint (serve_rendered_image) from web.py — it probed assets/renders, assets/renders/cache, and assets/refs, none of which exist post-eaec.4 flattening, and nothing referenced it (UI loads art via the /assets/ StaticFiles mount). Verified: no remaining renders/refs references in src; FileResponse still used by serve_index; web module imports clean; full suite 734 passed, 6 skipped. Note: ruff-on-save reformatted web.py (known harmless diff noise) alongside the deletion.
