---
id: gnusto-4ac5.3
title: Continuity via stream + scene-break styling
type: task
priority: 2
created: '2026-06-16T02:17:54Z'
updated: '2026-06-16T02:17:54Z'
depends_on:
- gnusto-4ac5.1
---

Let inter-room continuity fall out of the panel stream and delete the special-cased transition machinery.

- Remove the special-cased 'transition' plumbing (the partially-working preserve-exposition mechanism). In a stream, the panels that got you here sit directly above the new establishing panel — continuity is automatic.
- Add only a SCENE-BREAK visual treatment on establishing panels (wide/full-bleed panel, divider, 'page turn' feel) so a new room/scene reads as a beat change. Pure CSS, no state plumbing.

Depends on gnusto-4ac5.1.
