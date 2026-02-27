---
id: gnusto-b2e7
title: Behavior param type annotations for agent entity resolution
type: bug
priority: 1
created: '2026-02-21T00:01:55Z'
updated: '2026-02-24T00:00:00Z'
---

When the agent needs to pass entity references as behavior arguments (e.g.,
"ask hacker about missing students"), it must resolve natural language to @entity
IDs. This required three changes:

1. **Parameter type annotations** — Behaviors default to :entity type, with
   explicit :string/:number/:symbol for exceptions. Agent sees `ask-about <@topic>`
   vs `set-timer <seconds>` and knows how to pass each.

2. **Known entity exposure** — Abstract topic entities (@students, @food, etc.)
   now appear in agent context via :known property and (expose @entity) effect.

3. **Duplicate entity cleanup** — Removed duplicate object definitions from
   ZIL conversion (topic stubs in objects.grue that shadowed real definitions).
   Split scenery entities sharing IDs into distinct @alchemy-ladder, @dome-ladder,
   @tunnel-ladder, @basement-pool, @lair-pool.

Files changed:
- sexpr.py: parse_param_list() helper, PARAM_TYPES
- forms.py: GrueBehavior.param_types
- expr.py: GrueFn.param_types, (expose) effect in EffectInterpreter
- state.py: _format_behavior() with @ prefix, known_entities in GameState
- agent.py: Entity References section in system prompt
- llm.py: args schema description
- Game files: type annotations, :known true, duplicate cleanup, entity renames
- docs/grue.md: type annotations, Known Entities section, expose effect
- Tests: 15 new tests (param types, expose, known context)
