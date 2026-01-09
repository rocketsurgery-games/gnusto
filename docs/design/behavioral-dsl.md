# Behavioral DSL Extension

**Status**: Draft
**Related**: [world-dsl.md](./world-dsl.md)
**Issue**: frotzlm-bkv

## Problem Statement

The current DSL design handles static world definitions well (rooms, objects, actions) but cannot represent object-specific behavioral logic. In ZIL, objects often have custom `ACTION` routines that:

1. Override or supplement generic action handling
2. Respond differently based on game state (location, flags, etc.)
3. Trigger complex effects (timers, game events, NPC behavior)
4. Provide context-sensitive messages

### Example: OUTSIDE-DOOR-F

```zil
<ROUTINE OUTSIDE-DOOR-F ()
   <COND (<FSET? ,HERE ,OUTSIDE>           ; If player is outside
          <COND (<VERB? THROUGH>           ; "go through door" -> walk in
                 <DO-WALK ,P?IN>)
                (<HERE? ,MASS-AVE ,SMITH-ST ,COURTYARD ,CS-ROOF>
                 <COND (<VERB? OPEN>       ; At these locations, door opens
                        <TELL "The door opens from this side." CR>)
                       (<P? UNLOCK * MASTER-KEY>  ; Wrong key
                        <TELL "The door is not keyed to this key." CR>)>)
                (<VERB? OPEN UNLOCK>       ; Other outside locations
                 <TELL "The door is securely locked." CR>)>)
         (ELSE                             ; Player is inside
          <COND (<VERB? THROUGH>           ; "go through door" -> walk out
                 <DO-WALK ,P?OUT>)
                (<VERB? OPEN>              ; Opens but auto-closes
                 <TELL "You can open the door, but it shuts automatically
immediately thereafter." CR>)>)>>
```

This single routine encodes:
- Location-dependent behavior (OUTSIDE flag, specific rooms)
- Verb-specific responses (THROUGH, OPEN, UNLOCK)
- Instrument checking (MASTER-KEY rejection)
- Implicit actions (THROUGH → movement)

## Design Goals

1. **Expressiveness**: Capture ZIL behavioral logic declaratively
2. **Analyzability**: Static analysis can trace all possible behaviors
3. **LLM-friendliness**: Clear enough for LLMs to understand and execute
4. **Compatibility**: Builds on existing DSL constructs

## Proposed Solution: Object Behaviors

Add a `behaviors` block to object definitions that declares how the object responds to verbs in different contexts.

### Core Structure

```yaml
objects:
  OUTSIDE-DOOR:
    description: "outside door"
    flags: [DOORBIT, LOCKED, NDESCBIT, OPENABLE]
    properties:
      locked: true

    behaviors:
      # Each behavior handles one or more verbs
      through:
        # Cases are evaluated in order; first match wins
        cases:
          - when: (has-flag (loc PLAYER) OUTSIDE)
            do: (go-direction IN)
          - when: true  # Default case (inside)
            do: (go-direction OUT)

      open:
        cases:
          - when: (and (has-flag (loc PLAYER) OUTSIDE)
                       (in-room? PLAYER MASS-AVE SMITH-ST COURTYARD CS-ROOF))
            message: "The door opens from this side."
          - when: (has-flag (loc PLAYER) OUTSIDE)
            message: "The door is securely locked."
          - when: true  # Inside
            message: "You can open the door, but it shuts automatically immediately thereafter."

      unlock:
        cases:
          - when: (and (has-flag (loc PLAYER) OUTSIDE)
                       (in-room? PLAYER MASS-AVE SMITH-ST COURTYARD CS-ROOF)
                       (= INSTRUMENT MASTER-KEY))
            message: "The door is not keyed to this key."
          - when: (has-flag (loc PLAYER) OUTSIDE)
            message: "The door is securely locked."
```

### Behavior Execution Model

When a player performs an action on an object:

1. Check if the object has a behavior for that verb
2. If yes, evaluate cases in order until one matches
3. Execute the matched case's effects and/or show its message
4. Return `handled: true` (action complete) or `handled: false` (fall through to generic)

### Case Structure

Each case has:

```yaml
- when: <S-EXPRESSION>      # Condition (required)
  do: <S-EXPRESSION>        # Effects (optional)
  message: <STRING>         # Response text (optional)
  handled: <BOOL>           # Stop processing? (default: true)
```

### New Expression Forms

#### Location Predicates

```lisp
; Check if object is in specific room(s)
(in-room? OBJ ROOM1 ROOM2 ...)      ; true if OBJ in any listed room

; Check room flags
(has-flag (loc PLAYER) FLAG)        ; check flag on current room
```

#### Action Context

```lisp
; Current action's instrument (second object)
INSTRUMENT                          ; bound to PRSI equivalent
DIRECT-OBJECT                       ; bound to PRSO equivalent

; Check instrument
(= INSTRUMENT KEY)
(eq? INSTRUMENT nil)                ; no instrument provided
```

#### Implicit Actions

```lisp
; Redirect to movement
(go-direction NORTH)
(go-direction IN)
(go-direction OUT)

; Redirect to another action
(perform VERB OBJECT)
(perform VERB OBJECT INSTRUMENT)
```

## Complex Example: SMOOTH-STONE

The smooth stone in Lurking Horror has even more complex behavior:

```yaml
objects:
  SMOOTH-STONE:
    description: "smooth stone"
    flags: [TAKEBIT]
    properties:
      touched: false

    # Dynamic descriptions based on state
    descriptions:
      examine:
        cases:
          - when: (and (in-room? self INNER-LAIR) (not (prop self touched)))
            text: "It's a cracked piece of what might be obsidian. Scratched on it is a symbol."
          - default:
            text: "It's a smooth, shiny piece of what might be obsidian. Scratched on it is a symbol."

      # "You see X here" text
      room-description:
        cases:
          - when: (not (prop self touched))
            cases:
              - when: (in-room? self INNER-LAIR)
                text: "The stone sits on a hummock of mud. From here it appears to have a crack in it."
              - default:
                text: "One small stone stands out in the pile, smooth, shiny, and glowing with a blazing light."

    behaviors:
      take:
        cases:
          # Platform room: start timers
          - when: (and (in-room? self HERE) (in-room? PLAYER PLATFORM-ROOM))
            do:
              (seq
                (queue I-COOL 20)
                (queue I-LURKER-APPEARS -1))
            handled: false  # Let generic TAKE proceed

          # Brown roof with flier: blocked
          - when: (and (in-room? self HERE)
                       (in-room? PLAYER BROWN-ROOF INSIDE-DOME)
                       (here? FLIER))
            message: "The noisome creature jabs at you with its razor beak, but appears unwilling to approach the stone."

          # Inner lair first touch: trigger ending
          - when: (and (in-room? PLAYER INNER-LAIR) (not (prop self touched)))
            do:
              (seq
                (play-sound S-CRACK)
                (set-prop! self touched true))
            message: |
              You pick up the stone. It has a long jagged crack that almost breaks
              it in half. As you pick it up, you feel it bump to one side...
              [Full hatching sequence...]
            trigger: GAME-ENDING-HACKER-SAVED

      drop:
        cases:
          - when: (here? FLIER)
            do: (move! self HERE)
            message: "The shape becomes agitated, screeching and cawing as it approaches the stone."
```

## Timer/Queue System

ZIL uses queued interrupts for timed events. The DSL needs:

```yaml
timers:
  I-COOL:
    # Triggered after N turns
    on-trigger:
      message: "The temperature drops noticeably."
      effects:
        - (set! TEMPERATURE-DROPPING true)

  I-LURKER-APPEARS:
    # Triggered on specific condition (turn -1 = immediate next)
    on-trigger:
      when: (in-room? PLAYER PLATFORM-ROOM)
      message: "A dark shape rises from the depths..."
      effects:
        - (move! LURKER PLATFORM-ROOM)
```

Expression forms for timers:

```lisp
(queue TIMER-NAME TURNS)           ; Schedule timer
(queue TIMER-NAME -1)              ; Trigger on next applicable turn
(dequeue TIMER-NAME)               ; Cancel timer
```

## Game Events / Triggers

For complex state transitions that span multiple effects:

```yaml
triggers:
  GAME-ENDING-HACKER-SAVED:
    effects:
      - (play-sound S-GHIDRA)
      - (move! HACKER INNER-LAIR)
      - (set-prop! HACKER rescued true)
    message: |
      Something rises out of the mud, slowly straightening.
      The hacker, mud-covered and weak, staggers to his feet.
      "Can I have my key back?" he asks.
    then: VICTORY-HACKER-ENDING
```

## Resolution Order

When processing a verb + object:

1. **Object behavior** - Does object have a handler for this verb?
   - Evaluate cases in order
   - If matched and `handled: true`, stop
2. **Generic action** - Apply global action rules
   - Check preconditions
   - Apply effects
3. **Default response** - "Nothing happens" or similar

## Open Questions

### 1. Inheritance

Should objects inherit behaviors from categories?

```yaml
object-types:
  DOOR:
    behaviors:
      open:
        # Default door behavior

objects:
  OUTSIDE-DOOR:
    type: DOOR
    behaviors:
      open:
        # Override door behavior
```

### 2. Partial Handling

Sometimes behaviors want to add effects but still run generic handling:

```yaml
behaviors:
  take:
    cases:
      - when: (in-room? PLAYER PLATFORM-ROOM)
        do: (queue I-COOL 20)
        handled: false  # Let generic TAKE also run
```

### 3. Message Templates

Should messages support interpolation?

```yaml
message: "The {(prop self adjective)} door is locked."
```

### 4. Sound/Media

How do we handle `SOUNDS` calls?

```lisp
(play-sound S-CRACK)
(play-music M-THEME)
```

### 5. Return Values

ZIL routines return `<RTRUE>` or `<RFALSE>` to indicate handling. Our `handled` field captures this, but what about more nuanced returns?

## Implementation Plan

1. **Parser**: Extend world.py to parse `behaviors` blocks
2. **Evaluator**: Extend executor.py to check object behaviors before generic actions
3. **Expression forms**: Add new predicates (in-room?, INSTRUMENT, etc.)
4. **Test case**: Implement OUTSIDE-DOOR and verify behavior matches ZIL

## Migration

The ZIL converter can emit behavioral stubs:

```yaml
objects:
  OUTSIDE-DOOR:
    # ... properties ...

    # ZIL source for manual translation:
    # <ROUTINE OUTSIDE-DOOR-F ()
    #    <COND (<FSET? ,HERE ,OUTSIDE>
    #           ...
    behaviors: {}  # TODO: Translate from ZIL above
```

This allows incremental manual refinement with the source as reference.
