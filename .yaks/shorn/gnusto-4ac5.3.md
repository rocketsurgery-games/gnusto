---
id: gnusto-4ac5.3
title: Continuity via stream + scene-break styling
type: task
priority: 2
created: '2026-06-16T02:17:54Z'
updated: '2026-06-20T21:34:23Z'
depends_on:
- gnusto-4ac5.1
---

Let inter-room continuity fall out of the panel stream and delete the special-cased transition machinery.

- Remove the special-cased 'transition' plumbing (the partially-working preserve-exposition mechanism). In a stream, the panels that got you here sit directly above the new establishing panel — continuity is automatic.
- Add only a SCENE-BREAK visual treatment on establishing panels (wide/full-bleed panel, divider, 'page turn' feel) so a new room/scene reads as a beat change. Pure CSS, no state plumbing.

Depends on gnusto-4ac5.1.

---
▸ 2026-06-20T21:34:23Z
SHORN. Added the scene-break VISUAL treatment to EstablishingBlock (the delete-half of the transition machinery already landed in .1). Pure CSS, no state plumbing: extra top air (2.25rem) before the panel, a faded chapter divider with a small green accent diamond, and a soft 'page-turn' fold-shadow across the top of the stage art (locandum lifted above it via z-index). Verified live against lurkinghorror \u2014 a new establishing panel reads clearly as a beat change. Continuity remains automatic (the panels that got you here sit directly above).
