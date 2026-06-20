---
id: gnusto-4ac5.8
title: Player commands as caption panels
type: feature
priority: 3
created: '2026-06-16T02:18:42Z'
updated: '2026-06-20T20:50:16Z'
depends_on:
- gnusto-4ac5.1
---

Make the player's own input part of the comic.

- Style the command input as the protagonist's in-world narrator caption box.
- On submit, the command lands in the stream as a player CAPTION PANEL ('You try the door.'), so the player's actions are part of the narrative strip.
- Reinforces continuity (gnusto-4ac5.3) and immersion; helps the stream read as a continuous account rather than a Q&A log.

Depends on gnusto-4ac5.1.

---
▸ 2026-06-20T20:50:16Z
SHORN. CommandBlock.svelte restyled as an in-world player CAPTION panel: right-aligned mono box, panel-ink bg, --game-accent left border + '› ' prefix, accent-glow text. Commands already land in the stream client-side (App.svelte), so this was pure styling. Verified live: 'examine the hacker' renders as a right-aligned caption above the LLM's response. Right-aligned 'you' voice vs left narrator gives the call-and-response cadence from the spike.
