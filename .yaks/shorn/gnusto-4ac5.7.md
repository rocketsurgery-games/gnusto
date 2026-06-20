---
id: gnusto-4ac5.7
title: Webtoon-responsive panel geometry (vertical spine)
type: feature
priority: 2
created: '2026-06-16T02:18:34Z'
updated: '2026-06-20T20:50:16Z'
depends_on:
- gnusto-4ac5.1
---

Establish the responsive layout 'spine' for the whole panel system.

- WEBTOON-style vertical reflow is the responsive BASE geometry: panels stack vertically and reflow cleanly across viewports (mobile-first). This is the reliability-defining call vs fixed multi-column print pages.
- Print-style multi-panel TIERS (rows) are a desktop-only PROGRESSIVE ENHANCEMENT layered on the vertical spine.
- Reconcile with bounded pages (gnusto-4ac5.4): scroll within a bounded page, page-flip between pages.
- Define the panel/gutter/lettering CSS primitives that the renderer and the per-game theme (gnusto-4ac5.9) build on.

Foundational layout work alongside gnusto-4ac5.1.

---
▸ 2026-06-20T20:12:40Z
Spike (gnusto-4ac5.11) validated the spine: bounded centered column; mobile-first vertical stack; tier = display:contents -> grid@900px (desktop row / mobile stack, zero DOM dup); per-role width tokens needed (inset-in-spine vs inset-in-tier). NOT YET ported to the live UI — the real stream still uses the legacy .stream + right-sidebar layout on the light theme. Port the spine primitives (panel/gutter/lettering CSS, tier wrapper, bounded column) when reskinning; coordinates with 4ac5.9 theme. The .1 establishing panel already uses the cinematic 5:4 full-bleed crop + shadow-frame (no double-border) decided in the spike.

---
▸ 2026-06-20T20:50:16Z
SHORN (core). Ported the webtoon SPINE to the live UI: NarrativeStream wraps blocks in a bounded centered .spine column (--spine-max 760px) within the area left of the sidebar; mobile-first full-width reflow; reduced the bottom reserve to 55vh for live-page accretion. Added the TIER primitive to global.css (display:contents -> grid@900px) as the foundational row mechanism — activated once .5 emits block groupings. Verified live: establishing panel + prose + command caption + LLM focus all read in a tight centered column on the dark theme. DEFERRED to .5/.9: SFX lettering primitive + per-context inset width tokens (no consumers yet).
