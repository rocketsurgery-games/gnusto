---
id: gnusto-dae1
title: Left sidebar — history, journal, player notes
type: task
priority: 3
created: '2026-02-24T12:00:00Z'
updated: '2026-03-01T01:23:57Z'
---

The left sidebar surfaces the player's accumulated knowledge and history. Since the
narrative stream is now room-scoped, this is where past events live.

## Scope

1. **Room history** — Per-room summary of what happened. Auto-generated from content
   blocks (we have Narrate, Speak, Reveal, etc. — summarize key events per room visit).
   Clicking a room in history could show the full transcript.

2. **Player notes** — Free-text entries the player can create. Pin to a room or keep
   global. Useful for tracking clues, puzzles in progress, things to come back to.
   Could be triggered by a /note command or a UI button.

3. **Key discoveries** — Auto-tracked from Reveal/Focus blocks. "You found the master
   key." "The professor told you about the ritual." Timeline of important moments.

4. **Character log** — NPCs encountered, what they said, what they want. Built from
   Speak blocks and entity interactions.

5. **Visited rooms list** — All rooms the player has been to, ordered by recency or
   grouped by area. Serves as a lightweight alternative to the full map.

## Data source

All of this data is already flowing through content blocks. The work is accumulation,
summarization, and presentation — not new backend features.
