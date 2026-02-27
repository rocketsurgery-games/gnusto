---
id: gnusto-266.2
title: 'Phase 2: Unified state model with builtin specs'
type: task
priority: 1
created: '2026-01-23T17:55:39.727485-05:00'
updated: '2026-02-08T19:07:10.955849Z'
depends_on:
- gnusto-266.1
---

Replace StateRef variants with unified StatePath and add builtin specifications.

1. Unified StatePath:
   - Replace PropertyRef|LocationRef|QueueRef|HeldRef with single StatePath class
   - StatePath is just a string path like 'loc(@key)', 'prop(@door,locked)'
   - Hashable, comparable, serializable

2. Builtin specifications for runtime-provided symbols:
   - Define BuiltinSpec class for runtime operations (go, take, drop)
   - Define BuiltinFunc class for runtime functions (loc, held?, in-room?)
   - Each spec declares parameter domains and return value domains
   - Example: runtime:go provides ?from ∈ rooms, ?via ∈ objects

3. Refactor effect analysis to use new model:
   - Operate on reduced expressions (from Phase 1)
   - Use StatePath instead of StateRef variants
   - Consult builtin specs for runtime parameter domains

Deliverables:
- src/frotz/state.py with StatePath, BuiltinSpec, BuiltinFunc
- Update src/frotz/effects.py to use new model
- Maintain backward compatibility during transition
