---
id: gnusto-ntr.25
title: Per-entity :style override (alongside :rdesc on rooms/objects)
type: feature
priority: 3
created: '2026-06-20T21:14:56Z'
updated: '2026-06-20T21:14:56Z'
---

FOLLOW-UP from ntr.24 discussion. Allow specializing the render style on a SPECIFIC entity, declared on the room/object alongside :rdesc/:render, e.g. (object @vat :style "...extra framing..."). Composition layers between kind-style and the entity brief: base :prompt + kind :prompt (ntr.24) + entity :style + :rdesc brief. Design: add an optional :style str field to the entity model; parse in room+object forms; thread through build_render_manifest (carry on RenderManifestEntry) and assemble_brief(visual_style, brief, kind, entity_style); filfre uses it. Deferred from ntr.24 to keep that change focused (touches entity schema + manifest).
