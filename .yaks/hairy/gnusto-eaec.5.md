---
id: gnusto-eaec.5
title: Re-style Lurking Horror assets (graphic-novel horror)
type: task
priority: 3
created: '2026-06-16T02:17:13Z'
updated: '2026-06-16T02:18:47Z'
depends_on:
- gnusto-eaec.4
---

Replace the black-and-white pencil-sketch assets with full-color 'graphic novel horror' art matching the vibe of games/lurkinghorror/assets/refs/*.jpg.

- Define the new style block (world :visual-style) for TLH: dark, moody, comic ink + painted, dark-blue palette, panel-border framing. Retire the pencil STYLE in generate-art.sh (and the script itself once the manifest-driven flow exists).
- Re-render the keyed asset set via filfre fill (gnusto-eaec.4): EMPTY-STAGE rooms (no movable objects baked in) + single-subject objects/characters. Regenerate room images without microwave/fridge state baked in (those become floated single-subject panels).
- Update :render specs in the .grue files to the keyed assets as needed.
- This is the first real end-to-end exercise of the static pipeline; expect to feed learnings back into eaec.2-4. (User can help source fonts/reference images.)

Depends on gnusto-eaec.4.
