---
id: gnusto-f1j
title: Generalize :via to support (through) behaviors on arbitrary objects
type: bug
priority: 1
created: '2026-01-10T11:02:22.794361-05:00'
updated: '2026-02-08T19:07:10.97702Z'
---

## Problem
Converter emits `:per ROUTINE` on exits but this doesn't map well to a declarative model. PER routines handle many different patterns:
- Object barriers (manhole cover blocking exit)
- NPC interactions (hacker preventing theft)
- Inventory checks (too bulky to squeeze through)
- Progress gates (need to clear junk pile)
- Complex state machines (elevator)

## Solution
Generalize `:via` to work with any object that has a `(through)` behavior:

1. **Parser**: Remove `:per` field from GrueExit. Keep `:via` pointing to object names.

2. **Runtime**: When moving through an exit with `:via OBJECT`:
   - Find the object
   - If it has a `(through)` behavior, evaluate it
   - Allow movement only if behavior succeeds

3. **Converter**: Transform PER routines into objects:
   - Simple object gates → `:via THAT-OBJECT` (e.g., MANHOLE-COVER)
   - NPC gates → `:via NPC-NAME` with (through) behavior
   - Complex cases → synthesize `{ROOM}-{DIR}-PASSAGE` barrier object
   - Attach ZIL routine source as comment for translation agent

## Examples

### NPC blocking (HACKER-EXIT)
```lisp
(room TERMINAL-ROOM
  :exits ((south :to CS-2ND :via HACKER)))

(object HACKER
  :behaviors (
    (through (direction)
      :when (not (or (player-has PC) (player-has CHAIR)))
      :otherwise "You can't walk off with that!")))
```

### Inventory check (TOMB-SQUEEZE)
```lisp
(room TOMB
  :exits ((northwest :to SUB-BASEMENT :via TOMB-PASSAGE)))

(object TOMB-PASSAGE
  :location TOMB
  :flags (INVISIBLE)
  :behaviors (
    (through (direction)
      :when (not (player-carrying-heavy-item))
      :otherwise "It's too tight a fit.")))
```

### Progress gate (STORAGE-EXIT)
```lisp
(object JUNK-PILE
  :properties (:moved-count 0 :moves-needed 5)
  :behaviors (
    (through (direction)
      :when (> (self :moved-count) (self :moves-needed))
      :otherwise "The junk blocks your way.")))
```

## Acceptance Criteria
- [ ] Parser handles `:via OBJECT` on exits (already works)
- [ ] Runtime evaluates `(through)` behavior on via objects before allowing movement
- [ ] Converter transforms PER routines into `:via` with appropriate objects
- [ ] Synthesized barrier objects include ZIL source as comments
- [ ] REPL shows blocking messages from (through) behaviors
