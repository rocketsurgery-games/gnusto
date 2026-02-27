---
id: gnusto-9xf.8
title: 'Implement item acquisition: axe, boots, note, hand'
type: task
priority: 2
created: '2026-01-17T14:06:18.777415-05:00'
updated: '2026-02-08T19:07:11.01726Z'
---

Multiple lines in walkthrough use (move! @item @player) to give player items:

1. Line 744: @note - where does player get the note to show professor?
2. Line 788: @mummified-hand - should come from steam tunnels
3. Line 832: @axe - should come from maintenance-man
4. Line 833: @boots - should come from brown-basement

Need to implement proper acquisition paths for each item.
