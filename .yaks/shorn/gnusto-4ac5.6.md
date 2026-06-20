---
id: gnusto-4ac5.6
title: Graceful panel degradation + typographic fallback
type: feature
priority: 3
created: '2026-06-16T02:18:27Z'
updated: '2026-06-16T02:18:27Z'
depends_on:
- gnusto-4ac5.5
---

Guarantee panels never break when imagery is missing.

- Any panel that wants an image but has no pre-generated asset degrades to a text/caption panel.
- A SPLASH with no asset degrades to a TYPOGRAPHIC splash (full-bleed dramatic lettering) — itself a legit comic device, not a failure state.
- Insets/focus with no asset degrade to caption insets.
- Wire to the keyed-asset contract from gnusto-eaec.2/.4: missing key -> fallback treatment, never a broken image.

Relates to the expanded vocabulary (gnusto-4ac5.5) and the keyed-asset pipeline (gnusto-eaec). Can be built/tested with placeholders.

---
▸ 2026-06-20T22:55:00Z
SHORN. Graceful degradation completed; the "wants art but has none" path never breaks.
- NEW EntityInset.svelte: the framed 'specimen plate' for deploy=inset (object/character single-subject art on a light plate). DEGRADES to a CAPTION INSET (italic placeholder card, same footprint) when the asset key resolves to no file OR the URL 404s (onerror -> failed state). This is the mock's .inset--noart, now live.
- Focus + Reveal now HONOR deploy=inset, routing through EntityInset (default/feature modes keep the avatar/overhang layout). So the .5 deploy field renders, and its no-art case is safe.
- Splash no-art -> typographic splash (delivered in .5 slice 2) and Establishing no-art -> typographic locandum (delivered in .1) round out the set; every <img> in the stream now has an onerror guard.
- KEYED-ASSET CONTRACT (eaec.2/.4): pinned with tests — render._resolve_image_url returns None when resolve_asset_key yields no key OR the keyed file is absent on disk, returns /assets/<key>.<ext> when present. None is the single 'degrade' signal the UI keys off (resolveEntityImage -> null -> fallback). tests/gnusto/test_asset_contract.py (3).
Verified: pytest 760, svelte-check clean on touched files (pre-existing ObjectDetailOverlay error remains), vite build OK.
DEFERRED (noted, not blocking): deploy=background rendering (image behind text) currently falls through to the default treatment — low priority, no degradation risk. A DOM/visual test harness for the fallbacks would need the dev server to emit deploy=inset blocks (it renders only the initial room w/o LLM); covered by unit contract + svelte-check + build for now.
