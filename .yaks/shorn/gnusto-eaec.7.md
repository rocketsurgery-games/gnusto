---
id: gnusto-eaec.7
title: 'Event beat rendering: :rdesc catalog + :render-tagged emissions'
type: feature
priority: 2
created: '2026-06-19T22:30:07Z'
updated: '2026-06-20T00:49:56Z'
labels:
- render
- lang
---

Extend the variant render model to EVENTS, for scripted multi-turn beats (e.g. the professor-ritual cutscene) whose imagery is a sequence of transient moments, not a queryable steady state.

Settled design (see discussion):
- An event has NO state-reading :render selector. The firing control-flow arm IS the selector. So:
  - Event declares a :rdesc CATALOG: a keyword-keyed brief map, e.g. (:stage1 "..." :stage5 "..." :stage8-death "..." :stage8-survive "..."). Pure static data; the catalog keys are the beat tag set. Key = <event-base>-<tag>, parallel to entity <base>-<tag>.
  - Emission sites tag the beat via :render <keyword> on (success ...)/(blocked ...), e.g. (success :render :stage5 :message ...). Drop the unused :stage marker.
- Enumeration: build_render_manifest includes event beats (event base + catalog keys). kind="event". Trivially bounded (1-D beat sequence).
- Lint: the set of :render keyword tags emitted in the event body must be a subset of the declared :rdesc catalog keys (simple AST walk for literal tags; non-literal -> unbounded warning). Mirrors the entity codomain-subset rule.
- Beats are opt-in and room-independent; emissions with no :render are text-only.

In scope for this yak (Grue-side static pipeline):
1. Parse :rdesc catalog on (event ...).
2. Accept :render <keyword> on success/blocked emissions; thread the beat tag to the ActionResult/output so downstream can resolve <event>-<tag>.
3. Manifest + lint cover event beats; frotz render and filfre brief/fill handle them.
4. Migrate professor-ritual to declare its catalog and tag each stage emission; drop :stage.

Deferred to Epic B (panel stream UI): actually DISPLAYING beat panels in the UI (content block carrying the beat asset). This yak just makes beats declared, enumerable, lintable, and fillable.

Builds on gnusto-ntr.22 (keyword tags) and gnusto-eaec.2/.3/.4 (variant model, manifest, fill).
