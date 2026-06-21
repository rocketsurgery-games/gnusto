---
id: gnusto-4ac5.14
title: Ship a per-game lettering/SFX display font (Lurking Horror)
type: feature
priority: 3
created: '2026-06-21T00:10:00Z'
updated: '2026-06-21T00:10:00Z'
---

Follow-on from gnusto-4ac5.9. The per-game theme.css LOADER and the
`--font-letter` hook are in place (the backend serves <game_dir>/theme.css; the
frontend injects it after the bundled styles), but no actual display face is
shipped — SFX lettering + splash typography currently fall back to a system
stack ("Arial Black", Helvetica Neue, …).

Scope:
- Pick a license-clean horror/comic display face for Lurking Horror's SFX +
  splash lettering (and any caption display use).
- Drop an @font-face + `--font-letter` (and any other chrome vars) into
  games/lurkinghorror/theme.css; ship the font file under the game dir.
- Verify it loads via /game/theme.css and retints the SFX/splash lettering.

Pure art/design choice + asset; the infrastructure is done.
