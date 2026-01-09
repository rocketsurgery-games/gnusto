# World Definition DSL

## Overview

A declarative language for defining interactive fiction game worlds, designed to be:

1. **Statically analyzable** - State space can be explored for winnability, soft-locks, invariants
2. **LLM-friendly** - Provides constraints and affordances for LLM-driven gameplay
3. **Expressive** - Can represent the complexity of Infocom-style games
4. **Extractable** - Can be generated from ZIL source with manual refinement

## Design Principles

### Pure S-Expression Syntax

The entire world definition uses S-expressions with Clojure-style keyword arguments.
This provides:
- Unambiguous parsing
- Good editor support (paredit, rainbow parens, etc.)
- Natural fit for static analysis (homoiconic)
- Clear heritage from ZIL/MDL

### Immutable State Model

Game state is immutable. Effects are **declarative descriptions of state deltas**,
not imperative mutations. An action transforms state:

```
State × Action → State'
```

The "mutative" syntax (`set!`, `move!`) is notation for describing the delta,
not actual mutation. This enables:
- State space exploration (branching without rollback complexity)
- Deterministic replay
- Easy save/restore

### LLM as Interpreter

The DSL does NOT contain user-facing text. Instead, it provides:
- Semantic outcomes (success, blocked, etc.)
- Structured reasons for failures
- Context hints for narrative generation

The LLM translates between natural language and structured actions,
and generates narrative from outcomes. This separation allows:
- Multiple narrative styles from same world
- Flexible input parsing ("go north" vs "head to the lobby")
- Rich, contextual responses

## Syntax

### Basic Forms

```scheme
; Atoms
SYMBOL          ; uppercase by convention for game entities
keyword         ; lowercase for structural keywords
:keyword        ; keyword arguments
"string"        ; string literals
42              ; numbers
true false      ; booleans

; Lists
(form arg1 arg2 ...)

; Keyword arguments (Clojure-style)
(form :key1 value1 :key2 value2)

; Result/response maps
(outcome :status blocked :reason locked)
```

### Predicates (Pure Functions → Boolean)

```scheme
; Object queries
(has-flag OBJ FLAG)           ; does object have flag?
(prop OBJ property)           ; get property value (falsy if missing)
(loc OBJ)                     ; get object's location
(= A B)                       ; equality

; Location predicates
(in-room? OBJ ROOM1 ROOM2 ...)  ; is object in any listed room?
(room-has-flag? FLAG)           ; does player's current room have flag?
(here? OBJ)                     ; is object in player's room?
(held? OBJ)                     ; is object in player's inventory?
(visible? OBJ)                  ; can player see object?
(contained-in? OBJ CONTAINER)   ; is object inside container?

; Boolean logic
(and EXPR ...)
(or EXPR ...)
(not EXPR)

; Quantifiers
(any COLLECTION PRED)         ; any element satisfies predicate
(all COLLECTION PRED)         ; all elements satisfy predicate
```

### Effects (State Deltas)

Effects describe how state changes. They don't mutate - they declare the delta.

```scheme
(move! OBJ DEST)              ; object moves to destination
(set-flag! OBJ FLAG)          ; add flag to object
(clear-flag! OBJ FLAG)        ; remove flag from object
(set! OBJ :prop VALUE)        ; set property on object

; Compound effects
(seq EFFECT ...)              ; apply effects in order
(when COND EFFECT)            ; conditional effect
```

### Objects

Everything in the game world is an object, including PLAYER and rooms.

```scheme
(object OUTSIDE-DOOR
  :description "A heavy exterior door with an electronic lock"
  :location MASS-AVE           ; where object is (or nil for abstract objects)
  :flags (DOOR LOCKED OPENABLE FIXED)
  :properties
    ((lock-type electronic)
     (key-required MASTER-KEY))
  :behaviors
    ((open ...)
     (unlock ...)
     (through ...)))
```

**Flags vs Properties:**
- Flags are boolean presence/absence markers, optimized for `has-flag` checks
- Properties are key-value pairs for arbitrary data
- In practice, could unify these (flags are just boolean properties)

### Rooms

Rooms are objects with exits. The PLAYER's location is always a room.

```scheme
(room MASS-AVE
  :description "The intersection of Mass Ave and Memorial Drive"
  :flags (OUTSIDE LIT)
  :exits
    ((in :to LOBBY :via OUTSIDE-DOOR)))

(room LOBBY
  :description "The building's main lobby"
  :flags (INSIDE LIT)
  :exits
    ((out :to MASS-AVE :via OUTSIDE-DOOR)
     (north :to HALLWAY)))
```

**Exit structure:**
- `:to` - destination room (required)
- `:via` - object that mediates passage (optional)
- `:when` - condition for availability (optional, for simple cases)

When `:via` is specified, the referenced object's `through` behavior is consulted.
Most exits have no `:via` and allow free passage.

### The Player

PLAYER is an object. "Global" state is just player properties.

```scheme
(object PLAYER
  :location TERMINAL-ROOM      ; starting room
  :flags (PERSON)
  :properties
    ((score 0)
     (moves 0)
     (game-phase beginning)))
```

Inventory is just objects whose location is PLAYER:
```scheme
(held? KEY)  ; equivalent to (= (loc KEY) PLAYER)
```

### Containers

Objects can contain other objects. An object's location can be another object.

```scheme
(object CHEST
  :description "An old wooden chest"
  :location ATTIC
  :flags (CONTAINER OPENABLE LOCKED)
  :properties
    ((key-required BRASS-KEY)))

(object COIN
  :description "A gold coin"
  :location CHEST              ; inside the chest
  :flags (TAKEABLE))
```

Visibility rules:
- Objects in closed containers are not visible
- Objects in open containers are visible if the container is visible

### Behaviors

Behaviors define how objects respond to actions. They are evaluated when
an action targets the object (or references it via `:with`, etc.).

```scheme
(object OUTSIDE-DOOR
  :behaviors
    ((open
       (case (and (room-has-flag? OUTSIDE)
                  (in-room? PLAYER MASS-AVE SMITH-ST COURTYARD))
         :outcome success
         :effects ())  ; door auto-closes, no state change

       (case (room-has-flag? OUTSIDE)
         :outcome blocked
         :reason locked-from-outside)

       (case true
         :outcome success
         :effects ()
         :context ((note auto-closing))))

     (unlock
       (case (and (room-has-flag? OUTSIDE)
                  (= ?with MASTER-KEY))
         :outcome blocked
         :reason wrong-key-type
         :context ((detail electronic-lock)))

       (case (room-has-flag? OUTSIDE)
         :outcome blocked
         :reason locked-from-outside)

       (case (and (has-flag self LOCKED)
                  (= ?with MASTER-KEY))
         :outcome success
         :effects ((clear-flag! self LOCKED)))

       (case (has-flag self LOCKED)
         :outcome blocked
         :reason need-key)

       (case true
         :outcome blocked
         :reason not-locked))

     (through
       (case (room-has-flag? OUTSIDE)
         :outcome redirect
         :action (go :direction in))

       (case true
         :outcome redirect
         :action (go :direction out)))))
```

**Case structure:**
- First element is the condition (predicate)
- `:outcome` - result type: `success`, `blocked`, `redirect`
- `:effects` - state changes on success (list of effects)
- `:reason` - semantic failure reason (for LLM interpretation)
- `:context` - additional hints for LLM narrative
- `:action` - for redirects, the action to perform instead

**Special variables in behaviors:**
- `self` - the object being acted upon
- `?with` - the instrument (e.g., "unlock X with Y")
- `?on` - surface/target (e.g., "put X on Y")
- `?in` - container (e.g., "put X in Y")
- Other slots as needed, dynamically bound from action

### Actions

The LLM sends structured actions to the world model:

```scheme
(open DOOR)
(unlock DOOR :with KEY)
(put COIN :in CHEST)
(give ASSIGNMENT :to HACKER)
(go :direction north)
```

The world model:
1. Resolves the target object(s)
2. Checks visibility/reachability
3. Evaluates the object's behavior for that verb
4. Returns a structured response

**Response format:**
```scheme
; Success
(result :outcome success
        :effects ((moved KEY PLAYER))
        :context ((first-time true)))

; Blocked
(result :outcome blocked
        :reason locked
        :context ((lock-type electronic)))

; Unknown slot
(result :outcome failed
        :slot with
        :reason not-applicable)

; Redirect
(result :outcome redirect
        :action (go :direction in))
```

The LLM interprets these responses and generates natural language for the user.

### Time and Turns

Games track turns for timed events:

```scheme
; In PLAYER properties
(moves 0)

; Scheduled events
(timer HACKER-LEAVES
  :turns 10
  :when (and (here? HACKER) (not (prop HACKER appeased)))
  :effects ((move! HACKER ELSEWHERE))
  :context ((reason bored)))
```

For static analysis, we model time as part of state: each turn increments
`(prop PLAYER moves)` and may trigger scheduled effects.

### Win/Lose Conditions

```scheme
(victory
  :when (and (>= (prop PLAYER score) 100)
             (prop PLAYER defeated-evil))
  :context ((ending good)))

(defeat EATEN-BY-GRUE
  :when (and (not (room-has-flag? LIT))
             (not (any (inventory PLAYER)
                       (lambda (obj) (and (has-flag obj LIGHT)
                                          (has-flag obj ON))))))
  :context ((death-type grue)))

(defeat FELL-IN-PIT
  :when (and (= (loc PLAYER) DARK-PIT)
             (not (has-flag ROPE TIED)))
  :context ((death-type falling)))
```

## LLM Integration

### Input Translation

User: "I want to get into the building"

LLM considers:
- Current location (MASS-AVE, has exit `:to LOBBY :via OUTSIDE-DOOR`)
- OUTSIDE-DOOR has LOCKED flag
- Player has KEY in inventory

LLM tries: `(go :direction in)`

World returns: `(result :outcome blocked :reason locked-from-outside)`

LLM: "The door is locked from the outside."

User: "Can I unlock it?"

LLM tries: `(unlock OUTSIDE-DOOR :with KEY)`

World returns: `(result :outcome blocked :reason wrong-key-type :context ((detail electronic-lock)))`

LLM: "You try your key, but this appears to be an electronic lock - a physical key won't work."

### Output Generation

The LLM generates narrative from:
1. The action attempted
2. The outcome and reason
3. Context hints
4. Current game state
5. Narrative style/tone settings

This allows rich, varied prose while maintaining precise game state.

## Static Analysis

The pure functional model enables:

### State Space Exploration

```
Given: Initial state S₀
Enumerate: All reachable states via valid actions
Check: Victory reachable, no unrecoverable states
```

### Winnability Analysis

```
Prove: ∃ action sequence A₁...Aₙ where Aₙ(...A₁(S₀)) satisfies victory
```

### Soft-Lock Detection

```
Find: States S where:
  - victory(S) = false
  - ∀ valid actions A: leads to states already explored (cycle)
  - no unexplored states reachable
```

### Invariant Verification

```
Verify: ∀ reachable states S, ∀ actions A:
  invariants(apply(A, S)) = true OR defeat triggered
```

## Open Questions

1. **NPC modeling** - Are NPCs just objects with PERSON flag and behaviors for
   TALK/ASK/GIVE? Do they need special handling for conversation state?

2. **Lighting propagation** - Does light from objects illuminate containers?
   Rooms? How do we model "the lantern lights the room"?

3. **Scope/disambiguation** - When there are two KEYs visible, how does
   "unlock door with key" resolve? Is this purely LLM responsibility?

4. **Complex conditionals** - ZIL has `PER` routines that do arbitrary computation.
   Can all such cases be expressed declaratively, or do we need an escape hatch?

5. **Save/restore semantics** - How does save/restore interact with the
   immutable state model? (Likely trivial - just serialize state)

## File Format

Single file for simple games, or directory structure for larger ones:

```
game.world           ; single file (S-expressions)

; or

game/
  world.scm          ; meta, globals, win/lose conditions
  rooms.scm          ; room definitions
  objects.scm        ; object definitions
  npcs.scm           ; NPCs with conversation behaviors
```

Files use `.scm` or `.world` extension for editor mode detection.
