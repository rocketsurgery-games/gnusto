---
id: gnusto-4ac5.9
title: Per-game visual theme (palette, fonts, chrome)
type: feature
priority: 3
created: '2026-06-16T02:17:22Z'
updated: '2026-06-20T20:45:13Z'
---

Abstract presentation style per-game without contorting CSS into Grue. Part of the panel-stream UI work (Epic B).

- Per-game THEME lives as game-dir assets: a small theme.css (CSS variables: palette, fonts, panel/gutter chrome, SFX lettering) plus an optional game.json manifest tying briefs/style to the theme.
- Rule of thumb (from CLAUDE.md): push CONTENT/briefs into Grue (world :visual-style); keep PRESENTATION theme in CSS — don't backflip to re-encode CSS in Grue.
- Wire the gnusto web UI to load the active game's theme so colors/fonts/UI imagery are game-specific.
- Ship a Lurking Horror theme (dark graphic-novel-horror) as the first instance.

PALETTE SINGLE SOURCE: the game palette is already declared once in Grue as (world :visual-style :palette) where it drives image generation. The UI theme must DERIVE its CSS color vars from that single declared identity rather than re-stating the colors, so the generated art and the chrome can't drift apart.

Consumed by the panel/gutter/SFX styling (gnusto-4ac5.3, .7). Parallel foundation: no hard dep, but the first panel work (gnusto-4ac5.1) pulls it in.

---
▸ 2026-06-20T20:27:05Z
Reskinned the LIVE UI to the dark graphic-novel-horror theme via the token layer. Rewrote tokens.css: introduced a --game-* VISUAL IDENTITY layer (bg/panel/ink/line/accent/accent-glow/warm/paper/text) carrying the LH palette, with all semantic tokens derived from it; flipping these retinted nearly the whole app at once (blocks, sidebar, input all consume tokens). Spot-fixes: atmospheric radial page bg (global.css); EstablishingBlock now uses --game-* (single-source hygiene); Focus/Reveal image placeholders #eee -> --panel-fill; sidebar hovers for dark; input bar now reads as a dock (top hairline + shadow, green-glow prompt). Verified: svelte-check clean on touched files (pre-existing unrelated ObjectDetailOverlay error remains), vite build OK, live server screenshot against lurkinghorror matches the mock.

STILL OPEN on .9 (keep shaving):
1. PALETTE SINGLE SOURCE from Grue — the --game-* defaults currently hardcode the LH palette in CSS. To truly derive from the single Grue declaration needs structured swatches on (world :visual-style), which is a LANGUAGE SCHEMA change -> raised with the user for discussion (CLAUDE.md rule) before implementing. Plan: backend reads world.visual_style swatches, injects as --game-* CSS vars; CSS keeps fonts/chrome/layout.
2. PER-GAME theme.css loading (game-dir asset) so non-LH games override --game-* + fonts. Currently LH theme ships as the global default ('first instance').

---
▸ 2026-06-20T20:45:13Z
Palette SINGLE SOURCE now wired (via ntr.23 :swatches): Grue (world :visual-style :swatches) -> backend 'theme' message -> --game-* CSS vars; same hexes anchored into art briefs. tokens.css ships dark-theme defaults that swatches override. LH instance themed. REMAINING (minor, keep shaving): per-game FONTS/lettering + an optional game-dir theme.css for non-colour chrome (SFX lettering font for .5/.9). Colour identity + dark reskin = done.

---
▸ 2026-06-20T23:10:00Z
SHORN. Per-game THEME.CSS loader landed — the last .9 mechanism. Backend: GET /game/theme.css serves <game_dir>/theme.css (text/css) when present, else an empty 200 (so the frontend <link> never 404s); registered before the catch-all static mount. Frontend: App.svelte onMount appends <link rel=stylesheet href="/game/theme.css"> to <head> AFTER the bundled styles, so equal-specificity game overrides win — while COLOURS stay single-sourced from Grue via the inline --game-* vars (inline styles beat any stylesheet), so theme.css supplies only what swatches don't (fonts/SFX lettering, panel chrome, @font-face). Tests: test_web.py absent->empty-200 + present->served (2). Verified: pytest 762, svelte-check clean on touched files, build OK.

.9 SHORN. Delivered: dark graphic-novel-horror reskin via a --game-* identity layer; palette SINGLE-SOURCE from Grue (world :visual-style :swatches -> theme msg -> inline --game-* vars, same hexes anchor the art briefs); and the per-game theme.css loader for non-colour chrome/fonts. DEFERRED (art/design choice, not infra): shipping an actual custom LETTERING FONT file for LH — the loader + --font-letter hook are ready; just drop a @font-face into games/lurkinghorror/theme.css when a face is chosen. Could be a tiny follow-up yak if desired.
