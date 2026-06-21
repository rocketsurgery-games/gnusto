---
id: gnusto-4ac5.2.2
title: 'Spatial exits experiment: directional marginalia around the viewport edge'
type: feature
priority: 4
created: '2026-06-21T01:40:00Z'
updated: '2026-06-21T01:40:00Z'
---

Follow-on/refinement from gnusto-4ac5.2. The live frame currently presents exits
as a "Ways out" list in the right rail (clicks prefill "go <dir>"). The user
floated a more graphic-novel idea worth trying WITH visual iteration: position
exits as DIRECTIONAL MARGINALIA around the outer edge of the viewport (north top,
east right, west left, etc.) — spatial, outside the scrolling column, and not
duplicated panel-vs-rail.

Considerations to work through visually:
- Robustness for non-compass exits (up/down, in/out, named like "enter elevator")
  — they need a home (corner cluster) since they have no edge.
- Avoid collisions with the sticky pager (top) and the input bar (bottom); the
  narrative column is centered so the side gutters are the natural canvas, but
  they vanish at mid widths — needs care.
- Mobile collapse (keep simple; the rail already slides over today).

Held for visual iteration (the user was ambivalent on the idea and it's
layout-fiddly). The rail version shipped in gnusto-4ac5.2 is the robust baseline.
