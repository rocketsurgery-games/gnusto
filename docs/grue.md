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
(any (inventory) (lambda (x) (has-flag x LIGHT)))
(all (contents @chest) (lambda (x) (has-flag x SMALL)))

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
- `?direction` - movement direction

**Note on EXAMINE:** Examining an object is a behavior like any other - the object
is the direct object of the action. The behavior returns context about what's
observable, and the LLM generates a description. This keeps all object-specific
logic in behaviors.

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

**Note:** The current implementation provides queue flags for behavior conditions.
Turn-by-turn event handlers (like ZIL's interrupt routines that run each turn)
are planned for future implementation.

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
             (not (any (inventory)
                       (lambda (obj) (and (has-flag obj LIGHT)
                                          (has-flag obj ON))))))
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

#### `(world :name "..." :description "...")`
Game metadata. Both `:name` and `:description` are optional.

#### `(room NAME :description "..." :flags (...) :exits (...))`
Room definition. Rooms are named entities with:
- `:description` / `:ldesc` - Short/long descriptions
- `:flags` - Boolean markers (e.g., `OUTSIDE`, `LIT`)
- `:exits` - List of exit forms `(DIRECTION :to ROOM [:via OBJECT] [:when EXPR])`
- `:properties` - Key-value properties

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

### Special Forms (Custom Evaluation)

Special forms have custom evaluation rules - they control when and whether their
arguments are evaluated.

#### `(cond CLAUSE ...)`
Conditional evaluation. Each clause is `(CONDITION OUTCOME-FORM)`. Conditions are
evaluated in order until one is truthy; its outcome form is then returned.

```scheme
(cond
  ((has-flag ?self LOCKED) (blocked :reason locked))
  (true (success :effects ((set-flag! ?self OPENBIT)))))
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

#### `(any COLLECTION (lambda (VAR) PRED))`
Existential quantifier. Returns true if PRED is true for any element.
```scheme
(any (inventory) (lambda (x) (has-flag x LIGHT)))
```

#### `(all COLLECTION (lambda (VAR) PRED))`
Universal quantifier. Returns true if PRED is true for all elements.
```scheme
(all (contents @chest) (lambda (x) (has-flag x SMALL)))
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
| `flags` | OBJ | set | All flags on object |
| `visible?` | OBJ | bool | Is object visible to player? |
| `held?` | OBJ | bool | Is object in player's inventory? |
| `here?` | OBJ | bool | Is object in player's room? |
| `in?` | OBJ CONTAINER | bool | Is object inside container? |
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

#### Comparison Functions

| Function | Arguments | Returns | Description |
|----------|-----------|---------|-------------|
| `=` | A B | bool | Equality |
| `>` | A B | bool | Greater than |
| `<` | A B | bool | Less than |
| `>=` | A B | bool | Greater or equal |
| `<=` | A B | bool | Less or equal |
| `not` | EXPR | bool | Boolean negation |

#### Effects (State Mutations)

Effects describe state changes. By convention, their names end with `!`.

| Effect | Arguments | Description |
|--------|-----------|-------------|
| `move!` | OBJ DEST | Move object to destination |
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
| `?direction` | Movement direction |

Bindings are accessed with the `?` prefix:
```scheme
(has-flag ?self LOCKED)      ; is target object locked?
(= ?with @master-key)        ; was master-key used as instrument?
(move! ?self ?actor)         ; move target to actor
```

The `?` prefix retrieves the binding value. If a binding is not set, it returns `nil`.

#### Lexical Bindings (Lambda Parameters)

In `any` and `all` quantifiers, the lambda parameter is lexically scoped:
```scheme
(any (inventory) (lambda (x) (has-flag x LIGHT)))
```
Here `x` is bound to each inventory item in turn, shadowing any outer `x`.

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
