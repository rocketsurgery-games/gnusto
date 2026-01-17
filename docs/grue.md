# GRUE - Game Rules and Universe Expressions

## Overview

GRUE is a declarative language for defining interactive fiction game worlds, designed to be:

1. **Statically analyzable** - State space can be explored for winnability, soft-locks, invariants
2. **LLM-friendly** - Provides constraints and affordances for LLM-driven gameplay
3. **Expressive** - Can represent the complexity of Infocom-style games
4. **Extractable** - Can be generated from ZIL source with manual refinement

File extension: `.grue`

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

GRUE does NOT contain user-facing text. Instead, it provides:
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
@entity         ; entities (objects, rooms) - @ prefix, lowercase
?binding        ; context bindings - ? prefix
FLAG            ; flags/constants - UPPERCASE
:keyword        ; keywords (self-evaluating, Clojure-style)
"string"        ; string literals
42              ; numbers
true false      ; booleans

; Lists
(form arg1 arg2 ...)

; Quote (data, not code)
'(a b c)        ; literal list, not a function call
'@entity        ; literal symbol

; Keyword arguments (Clojure-style)
(form :key1 value1 :key2 value2)

; Keyword as function (Clojure-style)
(:key obj)      ; lookup :key on obj

; Result/response maps
(outcome :status blocked :reason locked)
```

### Predicates (Pure Functions → Boolean)

```scheme
; Object queries
(has-flag @door LOCKED)       ; does object have flag?
(prop @player score)          ; get property value (nil if missing)
(loc @key)                    ; get object's location
(= ?with @master-key)         ; equality

; Location predicates
(in-room? @player @lobby @hallway)  ; is object in any listed room?
(room-has-flag? OUTSIDE)            ; does player's current room have flag?
(here? @chest)                      ; is object in player's room?
(held? @key)                        ; is object in player's inventory?
(visible? @door)                    ; can player see object?
(in? @coin @chest)                  ; is object inside container?

; Boolean logic
(and EXPR ...)
(or EXPR ...)
(not EXPR)

; Quantifiers (see Formal Semantics for details)
(some (fn (?x) (has-flag ?x LIGHT)) (inventory))
(every? (fn (?x) (has-flag ?x SMALL)) (contents @chest))

; Event queue
(queued? HACKER-HELPS)        ; is event currently active?
```

### Effects (State Deltas)

Effects describe how state changes. They don't mutate - they declare the delta.

```scheme
(move! @key @player)          ; object moves to destination
(set-flag! @door LOCKED)      ; add flag to object
(clear-flag! @door LOCKED)    ; remove flag from object
(set-prop! @player score 10)  ; set property on object

; Compound effects
(seq EFFECT ...)              ; apply effects in order
(when COND EFFECT)            ; conditional effect

; Event queue
(queue! HACKER-HELPS)         ; activate event (indefinite)
(queue! LANTERN 200)          ; activate event with countdown
(dequeue! HACKER-HELPS)       ; deactivate event
```

### Objects

Everything in the game world is an object, including the player and rooms.

```scheme
(object @outside-door
  :description "A heavy exterior door with an electronic lock"
  :location @mass-ave           ; where object is (or nil for abstract objects)
  :flags (DOOR LOCKED OPENABLE FIXED)
  :properties (:lock-type electronic :key-required @master-key)
  :behaviors (
    :open (cond ...)
    :unlock (cond ...)
    :through (cond ...)))
```

**Flags vs Properties:**
- Flags are boolean presence/absence markers, optimized for `has-flag` checks
- Properties are key-value pairs for arbitrary data
- In practice, could unify these (flags are just boolean properties)

### Rooms

Rooms are objects with exits. The player's location is always a room.

```scheme
(room @mass-ave
  :description "The intersection of Mass Ave and Memorial Drive"
  :flags (OUTSIDE LIT)
  :exits ((in :to @lobby :via @outside-door)))

(room @lobby
  :description "The building's main lobby"
  :flags (INSIDE LIT)
  :exits ((out :to @mass-ave :via @outside-door)
          (north :to @hallway)))
```

**Exit structure:**
- `:to` - destination room (required)
- `:via` - object that mediates passage (optional)
- `:when` - condition for availability (optional, for simple cases)

When `:via` is specified, the referenced object's `through` behavior is consulted.
Most exits have no `:via` and allow free passage.

**Doors and boundaries:** A door (or other boundary object) is typically referenced
by exits in exactly two rooms - one on each side. The door's `:location` is cosmetic
(where it's "seen"), but its behaviors apply whenever any exit references it via `:via`.
Multiple rooms can reference the same door if the game's geometry requires it, but
unusual configurations are the author's responsibility to keep consistent.

**Global objects (`:globals`):** Rooms can declare objects that are visible/accessible
regardless of the object's `:location`. This is useful for:

- **Doors visible from both sides** - A door's `:location` is one room, but both
  rooms need to interact with it
- **Scenery in multiple rooms** - Snow, walls, sky visible from several locations
- **Abstract objects** - Conceptual objects with `:location nil` that are accessible
  in specific rooms

```scheme
(room @chemistry-bldg
  :globals (@alchemy-door @alchemy-window @office-door)
  :exits ((south :to @alchemy-dept :via @alchemy-door)))

(room @alchemy-dept
  :globals (@alchemy-door @alchemy-window)  ; same door, accessible from both sides
  :exits ((north :to @chemistry-bldg :via @alchemy-door)))

; Abstract scenery object with no physical location
(object @junk
  :location nil
  :description "junk"
  :flags (NDESCBIT))

(room @dead-storage :globals (@junk))   ; junk visible here
(room @storage-room :globals (@junk))   ; and here too
```

Objects in `:globals` override the `INVISIBLE` flag - they represent "known" scenery
that the player can always see and interact with when in that room.

### The Player

The player is an object identified by the `PERSON` flag. "Global" state is just player properties.

```scheme
(object @player
  :location @terminal-room      ; starting room
  :flags (PERSON)
  :properties (:score 0 :moves 0 :game-phase beginning))
```

Inventory is just objects whose location is the player:
```scheme
(held? @key)  ; equivalent to (= (loc @key) @player)
```

### Containers

Objects can contain other objects. An object's location can be another object.

```scheme
(object @chest
  :description "An old wooden chest"
  :location @attic
  :flags (CONTAINER OPENABLE LOCKED)
  :properties (:key-required @brass-key))

(object @coin
  :description "A gold coin"
  :location @chest              ; inside the chest
  :flags (TAKEBIT))
```

Visibility rules:
- Objects in closed containers are not visible
- Objects in open containers are visible if the container is visible

### Behaviors

Behaviors define how objects respond to actions. They are evaluated when
an action targets the object (or references it via `:with`, etc.).

```scheme
(object @outside-door
  :behaviors (
    :open (cond
      ((and (room-has-flag? OUTSIDE)
            (in-room? @player @mass-ave @smith-st @courtyard))
        (success :effects ()))  ; door auto-closes, no state change

      ((room-has-flag? OUTSIDE)
        (blocked :reason locked-from-outside))

      (true
        (success :context ((note auto-closing)))))

    :unlock (cond
      ((and (room-has-flag? OUTSIDE) (= ?with @master-key))
        (blocked :reason wrong-key-type
                 :context ((detail electronic-lock))))

      ((room-has-flag? OUTSIDE)
        (blocked :reason locked-from-outside))

      ((and (has-flag ?self LOCKED) (= ?with @master-key))
        (success :effects ((clear-flag! ?self LOCKED))))

      ((has-flag ?self LOCKED)
        (blocked :reason need-key))

      (true
        (blocked :reason not-locked)))

    :through (cond
      ((room-has-flag? OUTSIDE)
        (redirect :action (go :direction in)))

      (true
        (redirect :action (go :direction out))))))
```

**Clause structure:**
Each `cond` clause is `(CONDITION OUTCOME-FORM)` where OUTCOME-FORM is one of:
- `(success :effects (...) :context (...))` - action succeeds
- `(blocked :reason SYMBOL :context (...))` - action fails with semantic reason
- `(redirect :action EXPR)` - delegate to another action
- `(default :action EXPR)` - fall through to default behavior

**Dynamic bindings in behaviors:**
- `?self` - the object being acted upon (direct object)
- `?actor` - who is performing the action (defaults to player)
- `?with` - the instrument (e.g., "unlock X with Y")
- `?on` - surface/target (e.g., "put X on Y")
- `?in` - container (e.g., "put X in Y")
- `?to` - recipient (e.g., "give X to Y")
- `?topic` - conversation topic (e.g., "ask X about Y")
- `?direction` - movement direction

**Note on EXAMINE:** Examining an object is a behavior like any other - the object
is the direct object of the action. The behavior returns context about what's
observable, and the LLM generates a description. This keeps all object-specific
logic in behaviors.

**Conversation behaviors:**
NPCs can respond to conversation via `:ask-about` and `:tell-about` behaviors.
The `?topic` binding contains the topic being discussed.

```scheme
(object @hacker
  :behaviors (
    :ask-about (cond
      ((= ?topic @keys)
        (success :context ((response "Keys? I've got the master key for the building."))))
      ((= ?topic @food)
        (success :context ((response "I'm starving. Got anything to eat?"))))
      (true
        (blocked :reason unknown-topic)))

    :tell-about (cond
      ((= ?topic @assignment)
        (success :context ((response "I don't care about your homework."))))
      (true
        (blocked :reason not-interested)))))
```

Topics can be abstract objects defined just for conversation:
```scheme
(object @keys :description "the topic of keys")
(object @food :description "the topic of food")
```

### Actions

The LLM sends structured actions to the world model:

```scheme
(do :verb open :object @door)
(do :verb unlock :object @door :with @key)
(do :verb put :object @coin :in @chest)
(do :verb give :object @assignment :to @hacker)
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
        :effects ((moved @key @player))
        :context ((first-time true)))

; Blocked
(result :outcome blocked
        :reason locked
        :context ((lock-type electronic)))

; Error (unknown object, etc.)
(result :outcome error
        :error "Unknown object: foo")

; Redirect (internal, then followed automatically)
(result :outcome redirect
        :action (go :direction in))
```

The LLM interprets these responses and generates natural language for the user.

### Event Queues

Event queues track ongoing situations that affect behavior. They map to ZIL's
`QUEUE`/`QUEUED?` system used for timed events and state machines.

```scheme
; Check if an event is active
(queued? HACKER-HELPS)        ; is the hacker currently helping?
(queued? COMPULSION)          ; is player under compulsion?

; Activate/deactivate events in effects
(queue! HACKER-HELPS)         ; start the event (indefinite)
(queue! LANTERN 200)          ; start with 200-turn countdown
(dequeue! HACKER-HELPS)       ; end the event
```

**Use in behaviors:**

Events are commonly used to alter behavior based on ongoing situations:

```scheme
(object @pc
  :behaviors (
    :turn-off (cond
      ; Hacker blocks turning off PC while helping
      ((queued? HACKER-HELPS)
        (blocked :reason hacker-interference
                 :context ((blocker @hacker)
                           (message "You'll mung the bits, chomper!"))))
      (true
        (success :effects ((clear-flag! ?self POWER)))))))
```

### Turn-Based Events

Events are turn-based handlers that fire automatically when queued. They map directly
to ZIL's interrupt routines (`I-HACKER-HELPS`, `I-FOOD-HINT`, etc.).

```scheme
(event hacker-helps
  :location @terminal-room    ; only fires when player is here
  :on-turn (cond
    ((= hacker-help 0)
      (success :effects ((inc! hacker-help))
               :context ((stage 1) (description "The hacker glances at your screen..."))))
    ((= hacker-help 1)
      (success :effects ((inc! hacker-help))
               :context ((stage 2) (description "The hacker leans closer..."))))
    ((= hacker-help 2)
      (success :effects ((inc! hacker-help))
               :context ((stage 3) (description "The hacker starts typing..."))))
    (true
      (success :effects ((dequeue! hacker-helps) (move! @hacker @terminal-room))
               :context ((stage 4) (description "The hacker finishes and steps back."))))))
```

**Event structure:**
- `:location` - Optional room constraint; event only fires when player is in this room
- `:on-turn` - A `cond` form evaluated each turn the event is active

**Event lifecycle:**
1. Queue an event with `(queue! event-name)` or `(queue! event-name countdown)`
2. Each turn, queued events are processed:
   - If countdown > 0, decrement and skip
   - If location constraint exists and player isn't there, skip
   - Otherwise, evaluate the `:on-turn` cond
3. Event stays queued until explicitly dequeued with `(dequeue! event-name)`

**Common patterns:**

```scheme
; Multi-stage cutscene (use global counter)
(event cutscene
  :on-turn (cond
    ((= stage 0) (success :effects ((inc! stage)) :context ((stage 1))))
    ((= stage 1) (success :effects ((inc! stage)) :context ((stage 2))))
    (true (success :effects ((dequeue! cutscene)) :context ((complete true))))))

; Delayed event (re-queues itself with countdown)
(event reminder
  :on-turn (cond
    ((< hint-count 3)
      (success :effects ((inc! hint-count) (queue! reminder 5))
               :context ((hint "Don't forget the key..."))))
    (true
      (success :effects ((dequeue! reminder))))))

; Location-gated event
(event room-atmosphere
  :location @dark-cave
  :on-turn (success :context ((ambience "Water drips in the darkness..."))))
```

### Time and Turns

Games track turns via the `moves` global, incremented on successful actions.

```scheme
; In PLAYER properties
(moves 0)
```

For static analysis, we model time as part of state: each turn increments
`moves` and may trigger countdown-based events.

### Win/Lose Conditions

```scheme
(victory
  :when (and (>= (prop @player score) 100)
             (prop @player defeated-evil))
  :context ((ending good)))

(defeat eaten-by-grue
  :when (and (not (room-has-flag? LIT))
             (not (some (fn (?obj) (and (has-flag ?obj LIGHT)
                                        (has-flag ?obj ON)))
                        (inventory))))
  :context ((death-type grue)))

(defeat fell-in-pit
  :when (and (= (loc @player) @dark-pit)
             (not (has-flag @rope TIED)))
  :context ((death-type falling)))
```

## LLM Integration

### Input Translation

User: "I want to get into the building"

LLM considers:
- Current location (`@mass-ave`, has exit `:to @lobby :via @outside-door`)
- `@outside-door` has LOCKED flag
- Player has `@key` in inventory

LLM tries: `(go :direction in)`

World returns: `(result :outcome blocked :reason locked-from-outside)`

LLM: "The door is locked from the outside."

User: "Can I unlock it?"

LLM tries: `(do :verb unlock :object @outside-door :with @key)`

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

## Formal Semantics

This section provides a precise reference for GRUE language semantics, distinguishing
between different categories of constructs and their evaluation rules.

### Categories of Constructs

GRUE has three categories of constructs, each with different evaluation semantics:

| Category | Examples | Evaluation |
|----------|----------|------------|
| **Declarative Forms** | `world`, `room`, `object`, `victory`, `defeat`, `default` | Data definitions, not evaluated at runtime |
| **Special Forms** | `cond`, `and`, `or`, `when`, `seq`, `any`, `all` | Custom evaluation rules |
| **Functions** | `has-flag`, `loc`, `move!`, `set-flag!` | Uniform evaluation (all arguments evaluated) |

### Declarative Forms (Data Definitions)

Declarative forms define the static structure of the game world. They are processed
at parse time to build the `GrueWorld` datastructure and are not evaluated at runtime.

#### `(world :name "..." :description "..." :player @entity)`
Game metadata and player declaration.
- `:name` - Game title (optional)
- `:description` - Game description (optional)
- `:player` - Entity name of the player object (recommended)

#### `(room NAME :description "..." :flags (...) :exits (...) :behaviors (...))`
Room definition. Rooms are named entities with:
- `:description` / `:ldesc` - Short/long descriptions
- `:flags` - Boolean markers (e.g., `OUTSIDE`, `LIT`)
- `:exits` - List of exit forms `(DIRECTION :to ROOM [:via OBJECT] [:when EXPR])`
- `:properties` - Key-value properties
- `:behaviors` - Room-level action handlers (see Room Hooks below)

**Room Hooks:**

Rooms can define special behaviors that intercept or respond to player actions:

- `:on-enter` - Called when player enters the room, receives `?from-room` binding
- `:before-action` - Called before any action in the room, receives `?verb` and `?target` bindings

```scheme
(room @terminal-room
  :behaviors (
    ; Triggered when player enters from a specific room
    :on-enter (fn (?from-room)
      (cond
        ((= ?from-room @platform-room)
          (success :context ((nightmare-wake true))
                   :effects ((queue! hacker-helps))))
        (true (success))))

    ; Intercept actions - can block or allow them to proceed
    :before-action (fn (?verb ?target)
      (cond
        ((and (queued? compulsion)
              (not (= ?target "@more-box")))
          (blocked :reason possessed))
        (true (default))))))
```

The `:on-enter` hook is useful for triggering events when the player arrives from
specific locations (e.g., waking from a nightmare). The `:before-action` hook can
intercept and block actions based on game state (e.g., possession mechanics).

#### `(object NAME :location LOC :flags (...) :behaviors (...))`
Object definition. Objects are named entities with:
- `:description` / `:fdesc` / `:ldesc` - Descriptions
- `:location` - Where the object is (room, container, or entity name)
- `:flags` - Boolean markers (e.g., `TAKEBIT`, `LOCKED`, `PERSON`)
- `:properties` - Key-value properties
- `:behaviors` - Verb-to-handler mappings (see Behaviors section)

#### `(victory :when EXPR :context (...))`
Win condition. The `:when` expression is evaluated each turn.

#### `(defeat NAME :when EXPR :context (...))`
Lose condition. Named for narrative purposes.

#### `(default VERB (cond ...))`
Default behavior for a verb, applied when an object lacks its own handler.

#### `(event NAME :location ROOM :on-turn (cond ...))`
Turn-based event handler. Events fire each turn while queued.
- `:location` - Optional room constraint (event only fires when player is here)
- `:on-turn` - A `cond` form evaluated each turn

See [Turn-Based Events](#turn-based-events) for detailed documentation.

#### `(globals :name value ...)`
Global variable definitions. Globals are accessible throughout the world and
can be modified with `set!` and `inc!` effects.

```scheme
(globals
  :score 0
  :moves 0
  :hacker-help 0        ; stage counter for hacker-helps event
  :game-phase beginning)
```

### Special Forms (Custom Evaluation)

Special forms have custom evaluation rules - they control when and whether their
arguments are evaluated.

#### `(fn (PARAMS...) BODY)`
Anonymous function (lambda). Creates a closure that can be called later.
```scheme
(fn (?item)
  (cond
    ((has-flag ?item TAKEBIT) (success :effects ((move! ?item ?actor))))
    (true (blocked :reason not-takeable))))
```

The `lambda` keyword is also supported as an alias for `fn`.

#### `(defn NAME (PARAMS...) BODY)`
Named function definition. At top level, defines a global function. Inside an
entity (object/room), defines a scoped function visible only within that entity.

```scheme
; Global function
(defn is-lit (obj)
  (and (has-flag obj LIGHT)
       (has-flag obj ON)))

; Entity-scoped function
(object @door
  (defn check-locked ()
    (if (has-flag ?self LOCKED)
      (blocked :reason locked)
      (success)))

  :behaviors (
    :open check-locked))   ; reference by name
```

#### `(def NAME VALUE)`
Value binding. At top level, defines a global constant. Inside an entity,
defines a scoped value visible only within that entity's behaviors.

```scheme
; Entity-scoped values
(object @door
  (def door-desc "A heavy wooden door.")
  (def key-required @master-key)

  :behaviors (
    :examine (fn () (success :context ((description door-desc))))))
```

Entity-scoped `def` and `defn` can appear anywhere in the entity body (before
or after keyword properties). They help avoid polluting the global namespace
with many small helper functions and values.

**Shared Behaviors:** You can define shared behaviors at global scope and reference
them by symbol in multiple objects:

```scheme
; Define shared behaviors once
(def door-behaviors
  '(:examine (fn () (door-examine ?self))
    :open (fn () (door-open ?self))
    :close (fn () (door-close ?self))))

; Use in multiple objects
(object @door-1 :location @room-1 :behaviors door-behaviors)
(object @door-2 :location @room-2 :behaviors door-behaviors)
```

This avoids repetition when multiple objects have identical behavior logic.
Each object can still have unique properties that the shared functions read via `?self`.

#### `(if COND THEN ELSE)`
Conditional expression. Evaluates COND, then returns THEN if truthy, ELSE otherwise.
```scheme
(if (has-flag @door LOCKED)
    (blocked :reason locked)
    (success))
```

#### `(let ((VAR VAL) ...) BODY)`
Local binding with sequential semantics (like Clojure's `let`, not Scheme's parallel `let`).
Each binding can reference earlier bindings in the same `let`.
```scheme
(let ((target-room (exit-to ?direction)))
  (if (room-has-flag? target-room DARK)
      (blocked :reason too-dark)
      (success)))

; Sequential binding: y can reference x
(let ((x 10) (y (+ x 5)))  ; y = 15
  y)
```

#### `(cond CLAUSE ...)`
Conditional evaluation. Each clause is `(CONDITION OUTCOME-FORM)`. Conditions are
evaluated in order until one is truthy; its outcome form is then returned.

```scheme
(cond
  ((has-flag ?self LOCKED) (blocked :reason locked))
  (true (success :effects ((set-flag! ?self OPENBIT)))))
```

#### `(match (EXPRS...) CLAUSE ...)`
Pattern matching on a tuple of values. Cleaner than nested `cond` when matching
multiple conditions.

```scheme
(match ((has-flag ?self LOCKED) (has-flag ?self OPEN))
  ((true _)      (blocked :reason locked))
  ((_ true)      (blocked :reason already-open))
  ((false false) (success :effects ((set-flag! ?self OPEN)))))
```

Pattern elements:
- `_` or `?_` - Wildcard, matches anything
- `true`/`false` - Boolean literal match
- `?name` - Binding, captures value for use in result
- Other symbols/literals - Exact match

#### `(condp PRED EXPR TEST1 RESULT1 ...)`
Compare expression against test values using a predicate.

```scheme
(condp = (prop ?self :status)
  locked (blocked :reason locked)
  open   (blocked :reason already-open)
  closed (success))

(condp > health
  0   (defeat)
  10  (warn "low health")
  100 (success))
```

Evaluates `(PRED TEST EXPR)` for each test value. Returns result of first truthy test.
An odd trailing element is used as default.

#### `(cond-> INITIAL TEST1 EXPR1 ...)`
Conditional threading (first position). Threads value through expressions when tests pass.

```scheme
(cond-> 0
  true  (+ 1)    ; 0 -> (+ 0 1) = 1
  false (+ 10)   ; skipped
  true  (+ 2))   ; 1 -> (+ 1 2) = 3
```

Value is inserted as FIRST argument to each expression.

#### `(cond->> INITIAL TEST1 EXPR1 ...)`
Conditional threading (last position). Like `cond->` but threads as LAST argument.

```scheme
(cond->> 10
  true (- 5)    ; 10 -> (- 5 10) = -5
  true (- 3))   ; -5 -> (- 3 -5) = 8
```

#### Outcome Forms: `(success ...)`, `(blocked ...)`, `(redirect ...)`, `(default ...)`
Outcome declarations within `cond` clauses. Not evaluated - they declare the
result structure:
- `(success :effects (...) :context (...))` - Action succeeds
- `(blocked :reason SYMBOL :context (...))` - Action fails with semantic reason
- `(redirect :action EXPR)` - Delegate to another action
- `(default :action EXPR)` - Fall through to default, optionally with explicit action

#### `(and EXPR ...)`
Short-circuit logical AND. Returns false at first falsy value, otherwise returns
last value. Arguments evaluated left-to-right, stopping at first false.

#### `(or EXPR ...)`
Short-circuit logical OR. Returns first truthy value, or false if all falsy.
Arguments evaluated left-to-right, stopping at first true.

#### `(when COND EFFECT)`
Conditional effect. Only executes EFFECT if COND is truthy.
```scheme
(when (has-flag ?self FIRSTTIME)
  (seq (clear-flag! ?self FIRSTTIME)
       (set! score (+ score 10))))
```

#### `(seq EFFECT ...)`
Sequential effect execution. Effects are executed in order.
```scheme
(seq (move! ?self ?actor)
     (set-flag! ?self MOVEDBIT))
```

#### `(some PRED COLL)`
Existential quantifier (Clojure-style). Returns first truthy result of `(PRED x)`, or nil.
```scheme
(some (fn (?x) (has-flag ?x LIGHT)) (inventory))
(some (fn (?x) (> ?x 5)) '(1 3 7 9))  ; => true (from 7)
```

#### `(every? PRED COLL)`
Universal quantifier. Returns true if `(PRED x)` is truthy for all elements.
```scheme
(every? (fn (?x) (has-flag ?x SMALL)) (contents @chest))
(every? (fn (?x) (> ?x 0)) '(1 2 3))  ; => true
```

#### `'EXPR` or `(quote EXPR)`
Quote prevents evaluation. Returns EXPR as Python data (symbols become strings):
```scheme
'(a b c)           ; => ["a", "b", "c"]
'@hacker           ; => "@hacker" (string)
'(:foo "bar")      ; => [Keyword("foo"), "bar"]
```

#### `(list EXPR ...)`
List constructor. Evaluates all arguments and returns them as a list.
```scheme
(list 1 2 3)       ; => (1 2 3)
(list @pc @chair)  ; => (@pc @chair) - evaluates to object names
```

#### `(range END)` / `(range START END)` / `(range START END STEP)`
Generate integer sequence (Clojure-style).
```scheme
(range 5)          ; => (0 1 2 3 4)
(range 2 5)        ; => (2 3 4)
(range 0 10 2)     ; => (0 2 4 6 8)
(range 5 0 -1)     ; => (5 4 3 2 1)

; Common use: iterate floors 0-3
(for (?floor (range 4)) ...)
```

#### `(:keyword OBJ [DEFAULT])`
Keyword as function (Clojure-style). Looks up the keyword on the object.
Works for runtime properties and quoted keyword-value lists.
```scheme
(:size @pc)                         ; => 30 (property lookup)
(:missing @pc "default")            ; => "default" (with fallback)
(:foo '(:foo "bar" :baz "qux"))     ; => "bar" (quoted list lookup)
```

### Functions (Uniform Evaluation)

Functions have uniform evaluation: all arguments are evaluated before the function
is called. Functions are pure (no side effects) unless their name ends with `!`.

#### Predicates (Return Boolean or Value)

| Function | Arguments | Returns | Description |
|----------|-----------|---------|-------------|
| `has-flag` | OBJ FLAG | bool | Does object have flag? |
| `loc` | OBJ | string | Object's location |
| `prop` | OBJ PROP | any | Property value (nil if missing) |
| `desc` | OBJ | string | Object's :description (shorthand for `(prop OBJ :description)`) |
| `flags` | OBJ | set | All flags on object |
| `visible?` | OBJ | bool | Is object visible to player? |
| `held?` | OBJ | bool | Is object in player's inventory? |
| `here?` | OBJ | bool | Is object in player's room? |
| `loc?` | OBJ LOC | bool | Is object at expected location? |
| `in?` | OBJ CONTAINER | bool | Is object inside container? |
| `contained-in?` | OBJ CONTAINER | bool | Alias for `in?` |
| `inside?` | OBJ CONTAINER | bool | Recursive containment check (checks nested containers) |
| `held-by?` | OBJ ENTITY | bool | Is object held by entity? |
| `at?` | OBJ ROOM | bool | Is object at room? |
| `room?` | NAME | bool | Is this a room? |
| `in-room?` | OBJ ROOM... | bool | Is object in any listed room? |
| `room-has-flag?` | FLAG | bool | Does player's room have flag? |
| `inventory` | - | list | Player's inventory objects |
| `contents` | CONTAINER | list | Objects inside container |
| `exit?` | DIRECTION | bool | Does exit exist from current room? |
| `exit-to` | DIRECTION | string | Destination room for direction |
| `exit-via` | DIRECTION | string | Via object for direction (or nil) |
| `queued?` | EVENT | bool | Is event currently queued? |

#### Arithmetic Operators

| Operator | Arguments | Returns | Description |
|----------|-----------|---------|-------------|
| `+` | A B | number | Addition |
| `-` | A B | number | Subtraction |
| `*` | A B | number | Multiplication |
| `/` | A B | number | Integer division |
| `mod` | A B | number | Modulo (remainder) |

#### Comparison Functions

| Function | Arguments | Returns | Description |
|----------|-----------|---------|-------------|
| `=` | A B | bool | Equality |
| `>` | A B | bool | Greater than |
| `<` | A B | bool | Less than |
| `>=` | A B | bool | Greater or equal |
| `<=` | A B | bool | Less or equal |
| `not` | EXPR | bool | Boolean negation |
| `nil?` | EXPR | bool | Is value nil? |

#### String and List Functions

Standard library functions for working with strings and lists:

| Function | Arguments | Returns | Description |
|----------|-----------|---------|-------------|
| `str` | ARGS... | string | Concatenate arguments into string |
| `join` | SEP LIST | string | Join list elements with separator |
| `list` | ARGS... | list | Construct list from arguments |
| `range` | END or START END [STEP] | list | Generate integer sequence |
| `nth` | LIST N | any | Get nth element (0-indexed) |
| `list-set` | LIST N VALUE | list | Return new list with element N replaced |
| `first` | LIST | any | Get first element |
| `rest` | LIST | list | Get all but first element |
| `count` | LIST | number | Get list length |
| `empty?` | LIST | bool | Is list empty? |
| `cons` | ELEM LIST | list | Prepend element to list |
| `concat` | LISTS... | list | Concatenate lists |

#### Higher-Order Collection Functions

| Function | Arguments | Returns | Description |
|----------|-----------|---------|-------------|
| `map` | FN COLL | list | Apply FN to each element |
| `filter` | PRED COLL | list | Keep elements where PRED returns truthy |
| `remove` | PRED COLL | list | Remove elements where PRED returns truthy |
| `keep` | FN COLL | list | Like map but removes nil results |
| `reduce` | FN INIT COLL | any | Fold with accumulator: `(fn (?acc ?x) ...)` |
| `some` | PRED COLL | any | First truthy pred result, or nil |
| `every?` | PRED COLL | bool | True if pred is truthy for all elements |
| `for` | (VAR SEQ ...) BODY | list | Comprehension returning results |
| `doseq` | (VAR SEQ ...) BODY | nil | Comprehension for side effects |

Examples:
```scheme
(map (fn (?x) (* ?x 2)) '(1 2 3))           ; => (2 4 6)
(filter (fn (?x) (> ?x 0)) '(-1 0 1 2))     ; => (1 2)
(remove (fn (?x) (nil? ?x)) '(1 nil 2 nil)) ; => (1 2)
(keep (fn (?x) (if (> ?x 0) ?x nil)) '(-1 0 1 2)) ; => (1 2)
(reduce (fn (?acc ?x) (+ ?acc ?x)) 0 '(1 2 3 4))  ; => 10

; Comprehensions - for returns results, doseq for side effects only
(for (?x '(1 2 3)) (* ?x 2))                ; => (2 4 6)
(for (?x '(1 2) ?y '(a b)) (list ?x ?y))    ; => ((1 a) (1 b) (2 a) (2 b))
(doseq (?obj (contents @player)) (print (desc ?obj)))  ; prints each, returns nil
```

#### Effects (State Mutations)

Effects describe state changes. By convention, their names end with `!`.

| Effect | Arguments | Description |
|--------|-----------|-------------|
| `move!` | OBJ DEST | Move object to destination |
| `take!` | OBJ | Move object to player's inventory (shorthand for `(move! OBJ @player)`) |
| `set-flag!` | OBJ FLAG | Add flag to object |
| `clear-flag!` | OBJ FLAG | Remove flag from object |
| `set-prop!` | OBJ PROP VAL | Set property on object |
| `set!` | NAME VAL | Set global variable |
| `inc!` | NAME [AMOUNT] | Increment global (default +1) |
| `queue!` | EVENT [COUNT] | Queue event (indefinite or countdown) |
| `dequeue!` | EVENT | Remove event from queue |

### Binding Model

GRUE uses dynamic scoping for action bindings and lexical scoping for lambda parameters.

#### Dynamic Bindings (Action Context)

When a behavior is evaluated, these bindings are available:

| Binding | Description |
|---------|-------------|
| `?self` | The direct object of the action (target object) |
| `?actor` | Who is performing the action (defaults to player) |
| `?with` | Instrument ("unlock X with Y") |
| `?on` | Surface ("put X on Y") |
| `?in` | Container ("put X in Y") |
| `?to` | Recipient ("give X to Y") |
| `?topic` | Conversation topic ("ask X about Y") |
| `?direction` | Movement direction |
| `?value` | Parameterized value for custom behaviors (see below) |

**Parameterized behaviors:**
Custom behaviors can accept a value argument via `?value`. This supports explicit
LLM actions like `(do @microwave :set-timer 120)` or `(do @microwave :set-temp high)`.

```scheme
(object @microwave
  :behaviors (
    :set-timer (fn ()
      (success :effects ((set! microwave-timer ?value))))
    :set-temp (fn ()
      (let ((temp-val (condp = ?value warm 1 low 2 medium 3 high 4 nil)))
        (success :effects ((set! microwave-temp temp-val)))))))
```

Bindings are accessed with the `?` prefix:
```scheme
(has-flag ?self LOCKED)      ; is target object locked?
(= ?with @master-key)        ; was master-key used as instrument?
(move! ?self ?actor)         ; move target to actor
```

The `?` prefix retrieves the binding value. If a binding is not set, it returns `nil`.

#### Lexical Bindings (Lambda Parameters)

In `some` and `every?` quantifiers, the lambda parameter is lexically scoped:
```scheme
(some (fn (?x) (has-flag ?x LIGHT)) (inventory))
```
Here `?x` is bound to each inventory item in turn, shadowing any outer `?x`.

#### User-Defined Functions (defn)

Functions defined with `defn` use lexical scoping for parameters:
```scheme
(defn is-lit (obj)
  (and (has-flag obj LIGHT)
       (has-flag obj ON)))
```

### Naming Conventions

GRUE uses a consistent naming scheme for different types of identifiers:

| Pattern | Category | Examples |
|---------|----------|----------|
| `@lowercase` | Entities (objects, rooms) | `@player`, `@terminal-room`, `@brass-key` |
| `?binding` | Dynamic bindings | `?self`, `?actor`, `?with` |
| `UPPERCASE` | Flags (constants) | `LOCKED`, `TAKEBIT`, `PERSON` |
| `lowercase` | Keywords, verbs | `:description`, `open`, `take` |

Entity names use lowercase with hyphens (`@outside-door`), while flags use uppercase
(`LOCKED`, `OPENBIT`). This distinguishes runtime entity references from static flags.

### Evaluation Order

1. **Parse time**: Declarative forms are processed to build `GrueWorld`
2. **Runtime**: Actions are evaluated:
   - Verb and arguments are resolved
   - Object's behavior is looked up (or default behavior)
   - Bindings are established (`?self`, `?actor`, etc.)
   - Behavior's `cond` clauses are evaluated in order
   - First matching clause's outcome determines result
   - Effects (if any) are executed in order
   - Result is returned

## Test DSL

GRUE includes a built-in test DSL for writing game behavior tests in pure GRUE syntax.
Test files use the `.test.grue` extension and are colocated with game files.

### `(test NAME ...)`

Tests use a sequential style with explicit actions and assertions:

```scheme
(test "can exit south without carrying anything"
  (go :direction south)
  (assert (outcome? success))
  (assert (player-at? @cs-2nd)))

(test "blocked when carrying PC"
  :setup ((move! @pc @player))
  (go :direction south)
  (assert (outcome? blocked))
  (assert (reason? tech-property)))

(test "take PC then blocked at exit"
  (do @pc :take)
  (assert (held? @pc))
  (go :direction south)
  (assert (outcome? blocked)))
```

**Available test body forms:**

| Form | Description |
|------|-------------|
| `(do @obj :verb args...)` | Execute action on object |
| `(go :direction DIR)` | Move in direction |
| `(assert PRED)` | Check predicate, fail if false |
| `(until PRED BODY...)` | Loop until predicate is true (max 100 iterations) |
| `(wait)` | Pass time and process queued events |
| `(run ACTION-LIST)` | Execute a named list of actions |

### `(def NAME VALUE)` and `(run NAME)`

Define named action lists for reusable walkthrough segments:

```scheme
; Define action lists
(def walkthrough/to-kitchen
  '((do @movement :go south)
    (do @movement :go west)
    (do @movement :go north)))

(def walkthrough/get-food
  '((do @refrigerator :open)
    (do @carton :take)))

; Use in tests with (run)
(test "walkthrough-part2-master-key"
  (run walkthrough/to-kitchen)
  (run walkthrough/get-food)
  (assert (held? @carton))

  ; Heat food in microwave
  (do @microwave :open)
  (do @carton :put @microwave)
  (do @microwave :close)
  (do @microwave :set-timer 300)
  (do @microwave :start)

  ; Wait for food to heat
  (until (>= (prop @chinese-food heat) 12)
    (wait))

  ; Trade with hacker
  (do @hacker :trade @carton @master-key)
  (do @hacker :give @carton)
  (assert (held? @master-key)))
```

This enables building complete walkthroughs from composable segments without setup cheats.

### `(test-group NAME :setup EFFECTS TESTS...)`

Group related tests with shared setup. Reduces boilerplate when many tests need
the same initial state.

```scheme
(test-group "microwave set-timer"
  :setup ((move! @player @kitchen))

  (test "set to 2 minutes"
    (do @microwave :set-timer 120)
    (assert (global? microwave-timer 120)))

  (test "set to 30 seconds"
    (do @microwave :set-timer 30)
    (assert (global? microwave-timer 30)))

  (test "can't set over 1 hour"
    (do @microwave :set-timer 3601)
    (assert (outcome? blocked))
    (assert (reason? too-long))))
```

**Semantics:**
- Group `:setup` runs before each test in the group
- Test-level `:setup` runs after group setup (additive)
- Each test starts from fresh game state (group setup is not cumulative)
- Tests inside a group can override group setup by specifying their own

### Test Predicates

**Result predicates** (check last action result):

| Predicate | Description |
|-----------|-------------|
| `(outcome? STATUS)` | Check action outcome (success, blocked, error) |
| `(reason? SYMBOL)` | Check blocked reason |
| `(context? KEY VALUE)` | Check context contains key-value pair |
| `(death? BOOL)` | Check if death occurred |
| `(victory? BOOL)` | Check if victory occurred |

**State predicates** (check game state):

| Predicate | Description |
|-----------|-------------|
| `(player-at? ROOM)` | Player is in room |
| `(held? OBJ)` | Object is in player's inventory |
| `(loc? OBJ LOCATION)` | Object is at location |
| `(in? OBJ CONTAINER)` | Object is inside container |
| `(has-flag? OBJ FLAG)` | Object has flag |
| `(no-flag? OBJ FLAG)` | Object does not have flag |
| `(prop? OBJ PROP VALUE)` | Object property has value |
| `(global? NAME VALUE)` | Global variable has value |
| `(queued? EVENT)` | Event is in queue |
| `(not-queued? EVENT)` | Event is not in queue |

Any predicate from the expression language (e.g., `visible?`, `here?`, `inside?`) also
works in `(assert ...)` via the evaluator fallback.

### Test Effects

Setup can use any standard effect: `move!`, `set!`, `set-flag!`, `clear-flag!`,
`set-prop!`, `queue!`, etc.

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
game.grue              ; single file

; or

game/
  world.grue           ; meta, globals, win/lose conditions
  rooms.grue           ; room definitions
  objects.grue         ; object definitions
  npcs.grue            ; NPCs with conversation behaviors
```

Files use `.grue` extension. For editor support, configure your editor to use
Scheme/Lisp mode for `.grue` files.
