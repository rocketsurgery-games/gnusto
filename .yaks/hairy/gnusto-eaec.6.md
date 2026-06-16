---
id: gnusto-eaec.6
title: Per-game visual theme (palette, fonts, chrome)
type: feature
priority: 3
created: '2026-06-16T02:17:22Z'
updated: '2026-06-16T02:17:22Z'
---

Begin abstracting presentation style per-game without contorting CSS into Grue.

- Per-game THEME lives as game-dir assets: a small theme.css (CSS variables: palette, fonts, panel/gutter chrome, SFX lettering) plus an optional game.json manifest tying briefs/style to the theme.
- Rule of thumb (from CLAUDE.md): push CONTENT/briefs into Grue (world :visual-style); keep PRESENTATION theme in CSS — don't backflip to re-encode CSS in Grue.
- Wire the gnusto web UI to load the active game's theme so colors/fonts/UI imagery are game-specific.
- Ship a Lurking Horror theme (dark graphic-novel-horror) as the first instance.

Coordinates with Epic B (panel/gutter/SFX styling consume these variables). Largely independent of eaec.2-4; can proceed in parallel.
