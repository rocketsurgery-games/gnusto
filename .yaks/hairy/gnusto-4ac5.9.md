---
id: gnusto-4ac5.9
title: Per-game visual theme (palette, fonts, chrome)
type: feature
priority: 3
created: '2026-06-16T02:17:22Z'
updated: '2026-06-20T01:08:30Z'
---

Abstract presentation style per-game without contorting CSS into Grue. Part of the panel-stream UI work (Epic B).

- Per-game THEME lives as game-dir assets: a small theme.css (CSS variables: palette, fonts, panel/gutter chrome, SFX lettering) plus an optional game.json manifest tying briefs/style to the theme.
- Rule of thumb (from CLAUDE.md): push CONTENT/briefs into Grue (world :visual-style); keep PRESENTATION theme in CSS — don't backflip to re-encode CSS in Grue.
- Wire the gnusto web UI to load the active game's theme so colors/fonts/UI imagery are game-specific.
- Ship a Lurking Horror theme (dark graphic-novel-horror) as the first instance.

PALETTE SINGLE SOURCE: the game palette is already declared once in Grue as (world :visual-style :palette) where it drives image generation. The UI theme must DERIVE its CSS color vars from that single declared identity rather than re-stating the colors, so the generated art and the chrome can't drift apart.

Consumed by the panel/gutter/SFX styling (gnusto-4ac5.3, .7). Parallel foundation: no hard dep, but the first panel work (gnusto-4ac5.1) pulls it in.
