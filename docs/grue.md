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

The "mutative" syntax (`set`, `move`) is notation for describing the delta,
not actual mutation. This enables:
- State space exploration (branching without rollback complexity)
- Deterministic replay
- Easy save/restore

### Unified Property Model

All object state is stored as properties. Boolean properties serve the role that "flags"
played in ZIL (e.g., `:locked true` instead of a separate LOCKED flag). Access properties
using Clojure-style keyword-as-function syntax: `(:locked @door)` returns the value,
`(:locked @door false)` provides a default. Set properties with `(set @door :locked true)`.

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
:keyword        ; keywords (self-evaluating, Clojure-style)
"string"        ; string literals (see String Syntax below)
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
(:key obj)         ; lookup :key on obj (error if missing)
(:key obj default) ; lookup :key, return default if missing

; Result/response maps
(outcome :status blocked :reason locked)
```

### String Syntax

Strings are designed for interactive fiction prose. **Newlines and surrounding whitespace
are collapsed to a single space**, allowing descriptions to be formatted nicely in source
without affecting output:

```scheme
; This multi-line string in source...
(object @hallway
  :description "A long corridor stretches before you, its walls lined
                with flickering fluorescent lights. The floor is scuffed
                from decades of foot traffic.")

; ...becomes this single-line output:
; "A long corridor stretches before you, its walls lined with flickering
;  fluorescent lights. The floor is scuffed from decades of foot traffic."
```

This follows ZIL convention where source formatting is for readability, not output.

**Escape sequences:**
| Sequence | Result |
|----------|--------|
| `\n` | Actual newline in output |
| `\t` | Tab character |
| `\\` | Literal backslash |
| `\"` | Literal quote |

```scheme
; Use \n for actual newlines in output
:description "Line one.\n\nLine three (with blank line between)."
```

### Predicates (Pure Functions → Boolean)

```scheme
; Object queries - properties are accessed with keyword-as-function syntax
(:locked @door)               ; get property (error if missing)
(:locked @door false)         ; get property with default
(:score @player)              ; get property value (error if missing)
(:score @player 0)            ; get property with default
(loc @key)                    ; get object's location
(= ?with @master-key)         ; equality

; Location predicates
(in-room? @player @lobby @hallway)  ; is object in any listed room?
(:outside (loc (player)))           ; check room property
(here? @chest)                      ; is object in player's room?
(held? @key)                        ; is object in player's inventory?
(visible? @door)                    ; can player see object?
(in? @coin @chest)                  ; is object inside container?

; Boolean logic
(and EXPR ...)
(or EXPR ...)
(not EXPR)

; Quantifiers (see Formal Semantics for details)
(some (fn (?x) (:light ?x)) (inventory))
(every? (fn (?x) (:small ?x)) (contents @chest))

; Event queue
(queued? HACKER-HELPS)        ; is event currently active?
```

### Effects (State Deltas)

Effects describe how state changes. They don't mutate - they declare the delta.
Effects are returned from behaviors as quoted lists containing effect descriptors
followed by a terminator (`success`, `blocked`, `redirect`, or `default`):

```scheme
; Return effects from a behavior as a quoted list
'((move @key @player)         ; object moves to destination
  (set @door :locked true)    ; set property on object
  (success :message "Done.")) ; terminator

; Available effect descriptors (in quoted lists):
(move OBJ DEST)               ; move object to destination
(set OBJ :prop VALUE)         ; set property on object (booleans for flags)
(set-in OBJ PATH VALUE)       ; set nested property (PATH is list of keys)
(inc OBJ :prop [AMT])         ; increment numeric property (default: 1)
(dec OBJ :prop [AMT])         ; decrement numeric property (default: 1)
(queue EVENT [COUNT])         ; activate event
(dequeue EVENT)               ; deactivate event
(expose OBJ)                  ; set :known true (makes entity available in agent context)

; Conditional effects in quoted lists
(when COND (EFFECT ...))      ; conditional effect
```

### Objects

Everything in the game world is an object, including the player and rooms.

```scheme
(object @outside-door
  :description "A heavy exterior door with an electronic lock"
  :location @mass-ave           ; where object is (or nil for abstract objects)
  :properties (:door true :locked true :openable true :fixed true
               :lock-type electronic :key-required @master-key)
  :behaviors (
    :open (cond ...)
    :unlock (cond ...)
    :through (cond ...)))
```

**Properties:** All object state is stored as properties. Boolean properties (like `:locked true`)
serve the role that flags played in ZIL. Use keyword-as-function syntax to check: `(:locked @door)`.

### Rooms

Rooms are objects with exits. The player's location is always a room.

```scheme
(room @mass-ave
  :description "The intersection of Mass Ave and Memorial Drive"
  :properties (:outside true :lit true)
  :exits ((in :to @lobby :via @outside-door)))

(room @lobby
  :description "The building's main lobby"
  :properties (:inside true :lit true)
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

**Visible objects (`:visible`):** Rooms can declare objects that are visible/accessible
regardless of the object's `:location`. This is useful for:

- **Doors visible from both sides** - A door's `:location` is one room, but both
  rooms need to interact with it
- **Scenery in multiple rooms** - Snow, walls, sky visible from several locations
- **Abstract objects** - Conceptual objects with `:location nil` that are accessible
  in specific rooms

```scheme
(room @chemistry-bldg
  :visible (@alchemy-door @alchemy-window @office-door)
  :exits ((south :to @alchemy-dept :via @alchemy-door)))

(room @alchemy-dept
  :visible (@alchemy-door @alchemy-window)  ; same door, accessible from both sides
  :exits ((north :to @chemistry-bldg :via @alchemy-door)))

; Abstract scenery object with no physical location
(object @junk
  :location nil
  :description "junk"
  :properties (:nodesc true))

(room @dead-storage :visible (@junk))   ; junk visible here
(room @storage-room :visible (@junk))   ; and here too
```

Objects in `:visible` override the `:invisible` property - they represent "known" scenery
that the player can always see and interact with when in that room.

### Known Entities (Abstract Topics)

Some entities represent abstract concepts (conversation topics, off-screen things) that are
never physically present but can be used as arguments to behaviors like `:ask-about`. Set
`:known true` to make them available in the agent's context:

```scheme
(object @students
  :description "missing students"
  :location nil
  :properties (:invisible true :known true))
```

Known entities appear in a **"Known references"** section in the agent's context, allowing the
agent to resolve natural language like "the missing students" → `@students`.

To reveal entities during gameplay, use the `(expose @entity)` effect:

```scheme
:ask-about (fn (?topic)
  (cond
    ((= ?topic @keyring)
      '((expose @master-key)
        (say @hacker "This is a master key.")
        (success "revealed master key")))))
```

### The Player

The player object must be declared in the world definition with `(world ... :player @name)`.
The object should have the `:person` property for semantic clarity. Score and moves are
stored as properties on the player object.

```scheme
(world :name "My Game" :player @player)

(object @player
  :location @terminal-room      ; starting room
  :properties (:person true :score 0 :moves 0 :game-phase beginning))
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
  :properties (:container true :openable true :locked true :key-required @brass-key))

(object @coin
  :description "A gold coin"
  :location @chest              ; inside the chest
  :properties (:takeable true))
```

Visibility rules:
- Objects in closed containers are not visible
- Objects in open containers are visible if the container is visible

### Vehicles

Vehicles are objects the player can be "in" or "on" for movement purposes.
The `:vehicle` property marks an object as a vehicle. When the player is in
a vehicle, movement behavior depends on whether the vehicle is also furniture:

**Portable vehicles** (`:vehicle true`, no `:furniture`):
- Boats, carts, etc.
- When the player moves, the vehicle moves with them
- The vehicle's location becomes the destination room

**Furniture vehicles** (`:vehicle true` AND `:furniture true`):
- Chairs, beds, etc.
- The player automatically exits before moving
- The furniture stays in its original location
- A message indicates the auto-exit: "First, you arise from the chair."

```scheme
; Portable vehicle (moves with player)
(object @rowboat
  :properties (:vehicle true :takeable false)
  :location @lake-shore)

; Furniture vehicle (player exits before moving)
(object @chair
  :properties (:vehicle true :furniture true :takeable true)
  :location @terminal-room)
```

**Vehicle containment semantics:**
- Player "in" vehicle: `(loc @player)` returns the vehicle, not the room
- Use `(get-player-room)` to get the actual room when player is in a vehicle
- Objects in the same room as the vehicle are visible to the player
- The player can interact with room objects while in a vehicle

**Vehicle preposition:**
- `:surface true` → player is "on" the vehicle (e.g., "on the raft")
- No `:surface` → player is "in" the vehicle (e.g., "in the boat")

### Behaviors

Behaviors define how objects respond to actions. They are evaluated when
an action targets the object (or references it via `:with`, etc.).

```scheme
(object @outside-door
  :behaviors (
    :open (cond
      ((and (:outside (loc (player)))
            (in-room? @player @mass-ave @smith-st @courtyard))
        (success))  ; door auto-closes, no state change

      ((:outside (loc (player)))
        (blocked :reason locked-from-outside))

      (true
        (success :context ((note auto-closing)))))

    :unlock (cond
      ((and (:outside (loc (player))) (= ?with @master-key))
        (blocked :reason wrong-key-type
                 :context ((detail electronic-lock))))

      ((:outside (loc (player)))
        (blocked :reason locked-from-outside))

      ((and (:locked ?self) (= ?with @master-key))
        '((set ?self :locked false) (success)))

      ((:locked ?self)
        (blocked :reason need-key))

      (true
        (blocked :reason not-locked)))

    :through (cond
      ((:outside (loc (player)))
        (redirect :action (go :direction in)))

      (true
        (redirect :action (go :direction out))))))
```

**Clause structure:**
Each `cond` clause is `(CONDITION OUTCOME-FORM)` where OUTCOME-FORM is one of:
- `(success :context (...))` - action succeeds with no state change
- `'((effect ...) (success))` - action succeeds with effects (quoted list)
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
        :effects-applied ("moved @key to @player")
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
(queue HACKER-HELPS)          ; start the event (indefinite)
(queue LANTERN 200)           ; start with 200-turn countdown
(dequeue HACKER-HELPS)        ; end the event
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
        '((set ?self :power false) (success))))))
```

### Turn-Based Events

Events are turn-based handlers that fire automatically when queued. They map directly
to ZIL's interrupt routines (`I-HACKER-HELPS`, `I-FOOD-HINT`, etc.).

```scheme
(event hacker-helps
  :location @terminal-room    ; only fires when player is here
  :on-turn (cond
    ((= (:help-stage @hacker) 0)
      '((set @hacker :help-stage 1)
        (success :context ((stage 1) (description "The hacker glances at your screen...")))))
    ((= (:help-stage @hacker) 1)
      '((set @hacker :help-stage 2)
        (success :context ((stage 2) (description "The hacker leans closer...")))))
    ((= (:help-stage @hacker) 2)
      '((set @hacker :help-stage 3)
        (success :context ((stage 3) (description "The hacker starts typing...")))))
    (true
      '((dequeue hacker-helps) (move @hacker @terminal-room)
        (success :context ((stage 4) (description "The hacker finishes and steps back.")))))))
```

**Event structure:**
- `:location` - Optional room constraint; event only fires when player is in this room
- `:on-turn` - A `cond` form evaluated each turn the event is active

**Event lifecycle:**
1. Queue an event with `(queue event-name)` or `(queue event-name countdown)`
2. Each turn, queued events are processed:
   - If countdown > 0, decrement and skip
   - If location constraint exists and player isn't there, skip
   - Otherwise, evaluate the `:on-turn` cond
3. Event stays queued until explicitly dequeued with `(dequeue event-name)`

**Common patterns:**

```scheme
; Multi-stage cutscene (use object property for counter)
(event cutscene
  :on-turn (cond
    ((= (:stage @game) 0) '((set @game :stage 1) (success :context ((stage 1)))))
    ((= (:stage @game) 1) '((set @game :stage 2) (success :context ((stage 2)))))
    (true '((dequeue cutscene) (success :context ((complete true)))))))

; Delayed event (re-queues itself with countdown)
(event reminder
  :on-turn (cond
    ((< (:hint-count @game) 3)
      '((set @game :hint-count (+ (:hint-count @game) 1))
        (queue reminder 5)
        (success :context ((hint "Don't forget the key...")))))
    (true
      '((dequeue reminder) (success)))))

; Location-gated event
(event room-atmosphere
  :location @dark-cave
  :on-turn (success :context ((ambience "Water drips in the darkness..."))))
```

### Time and Turns

Games track turns via the `:moves` property on the player, incremented on successful actions.

```scheme
(object @player
  :properties (:person true :score 0 :moves 0))
```

For static analysis, we model time as part of state: each turn increments
the player's `:moves` and may trigger countdown-based events.

### Win/Lose Conditions

```scheme
(victory
  :when (and (>= (:score @player) 100)
             (:defeated-evil @player))
  :context ((ending good)))

(defeat eaten-by-grue
  :when (and (not (:lit (loc (player))))
             (not (some (fn (?obj) (and (:light ?obj)
                                        (:on ?obj)))
                        (inventory))))
  :context ((death-type grue)))

(defeat fell-in-pit
  :when (and (= (loc @player) @dark-pit)
             (not (:tied @rope)))
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
| **Declarative Forms** | `world`, `room`, `object`, `victory`, `defeat`, `default`, `event` | Data definitions, not evaluated at runtime |
| **Special Forms** | `cond`, `and`, `or`, `when`, `seq`, `fn`, `let` | Custom evaluation rules |
| **Functions** | `loc`, `held?`, `visible?`, `move`, `set` | Uniform evaluation (all arguments evaluated) |

### Declarative Forms (Data Definitions)

Declarative forms define the static structure of the game world. They are processed
at parse time to build the `GrueWorld` datastructure and are not evaluated at runtime.

#### `(world :name "..." :description "..." :player @entity :intro "...")`
Game metadata and player declaration.
- `:name` - Game title (optional)
- `:description` - Game description (optional)
- `:player` - Entity name of the player object (**required**)
- `:intro` - Introductory text displayed at game start (optional)
- `:visual-style` - Render style keyword-map (optional). A static style prefix
  and hooks prepended to generation briefs. Keys:
  - `:prompt` - Style sentence prepended to every brief (e.g. `"Color graphic-novel horror, inked."`)
  - `:palette` - Palette hint woven into briefs (e.g. `"dark blues, sickly greens"`)
  - `:aspect-ratio` - Default aspect ratio (e.g. `"16:9"`)

```scheme
(world :name "The Lurking Horror" :player @player
  :visual-style (:prompt "Color graphic-novel horror, inked, painted shading."
                 :palette "dark blues, sickly fluorescent greens"
                 :aspect-ratio "16:9"))
```

#### `(room NAME :description "..." :flags (...) :exits (...) :behaviors (...))`
Room definition. Rooms are named entities with:
- `:description` / `:ldesc` - Short/long descriptions
- `:flags` - Boolean markers (e.g., `OUTSIDE`, `LIT`)
- `:exits` - List of exit forms `(DIRECTION :to ROOM [:via OBJECT] [:when EXPR])`
- `:properties` - Key-value properties
- `:behaviors` - Room-level action handlers (see Room Hooks below)
- `:render` - Variant selector (only needed when the room has more than one
  variant): a `(fn () ...)` returning a variant **tag keyword** (e.g. `:lit`), a
  literal keyword tag, or a literal **string** to reuse a verbatim shared key.
  Absent ⇒ a single variant. Room variants should depend only on room-global
  state (see Rendering below).
- `:rdesc` - Render brief(s): a string (single variant) or a
  `(:variant "brief" ...)` map (one brief per variant tag). Falls back to
  `:description` when absent.

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
          '((queue hacker-helps)
            (success :context ((nightmare-wake true)))))
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
- `:description` / `:ldesc` - Descriptions (can be string or fn)
- `:location` - Where the object is (room, container, or entity name)
- `:flags` - Boolean markers (e.g., `TAKEBIT`, `LOCKED`, `PERSON`)
- `:properties` - Key-value properties
- `:behaviors` - Verb-to-handler mappings (see Behaviors section)
- `:render` - Variant selector (only needed when the object has more than one
  variant): a `(fn () ...)` returning a variant **tag keyword** (e.g. `:open`), a
  literal keyword tag, or a literal **string** to reuse a verbatim shared key.
  Absent ⇒ a single variant.
- `:rdesc` - Render brief(s): a string (single variant) or a
  `(:variant "brief" ...)` map (one brief per variant tag). Falls back to
  `:description` when absent. Fixed objects may carry contextual briefs
  (in-situ); movable objects neutral (white background).

#### Rendering (`:render`, `:rdesc`, `:visual-style`)

Illustrations are **pre-generated**. An entity's art is keyed by a small set of
**variants**, and filenames are *derived* — authors never hand-maintain them:

```
base name (entity sans @) + variant tag  ->  <base>-<tag>.jpg
@microwave + :open                       ->  microwave-open.jpg
```

A variant **tag is a keyword** (`:open`) — a self-denoting name, distinct from a
string. A **string** means something different in `:render`: a verbatim asset key
(the escape hatch). This keyword/string split is type-directed:

- `:render` is the **variant selector**: a pure `(fn () ...)` returning a tag
  keyword (e.g. `:open`). Omit it for single-variant entities (key =
  `<base>`). Returning (or giving as a literal) a **string** instead means "use
  this verbatim key" (e.g. a door reusing its room's image).
- `:rdesc` declares the **brief per variant** (a `(:open "..." :closed "...")`
  map), or a single brief string. The map keys *are* the variant set, so the
  keyset is declarative and enumerable without running the selector.
- The world `:visual-style` prefixes a consistent look.

```scheme
(object @microwave
  :render (fn () (cond ((:open self) :open)
                       ((queued? microwave-running) :running)
                       (true :closed)))
  :rdesc (:open    "A 1980s microwave, door open, interior visible, above a counter."
          :running "A 1980s microwave running, interior light on, above a counter."
          :closed  "A 1980s microwave, door closed, above a counter."))
; keys: microwave-open.jpg / microwave-running.jpg / microwave-closed.jpg
```

> Keywords vs strings: a keyword `:open` is a self-denoting, interned-by-name
> value and is **not** equal to the string `"open"`. Variant tags are keywords;
> arbitrary literal values (verbatim keys, asset filenames) are strings.

The **stage-vs-subject** rule keeps this bounded: a room selector keys only on
room-global state (lights, flood, power), while an object selector keys only on
its own state; per-object state is shown as separate floated panels, never baked
into the room. See [`render.md`](render.md) for the full pipeline and design.

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

#### `(globals :name value ...)` *(Removed)*
> **Note:** The `(globals)` form has been removed. Use object properties instead.
> State should live on the object it describes.

```scheme
; Use object properties:
(object @microwave
  :properties (:timer 0 :temp 0))

; Access with keyword-as-function:
(:timer @microwave)              ; read property
(set @microwave :timer 120)      ; write property (as effect)
(inc @microwave :timer 60)       ; increment property (as effect)
(dec @microwave :timer)          ; decrement property by 1 (as effect)

; Nested property access:
(get-in @elevator '(:buttons :go 2))     ; read nested value
(set-in @elevator '(:buttons :go 2) true) ; set nested value (as effect)
```

`score` and `moves` are stored as properties on the player object. Access them with
`(:score @player)` and `(:moves @player)`, or use `(inc @player :score)` as an effect.

### Special Forms (Custom Evaluation)

Special forms have custom evaluation rules - they control when and whether their
arguments are evaluated.

#### `(fn (PARAMS...) BODY)`
Anonymous function (lambda). Creates a closure that can be called later.
```scheme
(fn (?item)
  (cond
    ((:takeable ?item) '((move ?item ?actor) (success)))
    (true (blocked :reason not-takeable))))
```

The `lambda` keyword is also supported as an alias for `fn`.

**Parameter type annotations:** Parameters may have optional type annotations
using a keyword after the parameter name:

```scheme
(fn (?seconds :number) (+ ?seconds 60))
(fn (?level :symbol) (= ?level 'high))
(fn (?value :string) (str "You typed: " ?value))
(fn (?target :entity) (= ?target @door))   ; explicit, same as default
```

Available types: `:entity`, `:string`, `:number`, `:symbol`.

For **behavior parameters**, the default type is `:entity` — the agent will
resolve natural language references to `@object` IDs before passing them.
Non-entity types (`:string`, `:number`, `:symbol`) must be annotated explicitly
so the agent knows to pass literal values instead:

```scheme
(object @microwave
  :behaviors (
    :set-timer (fn (?seconds :number) ...)   ; agent passes a number
    :set-temp (fn (?level :symbol) ...)      ; agent passes warm/low/medium/high
    :open (fn () ...)                        ; no params
    :put-in (fn (?item) ...)))               ; default: entity (@object ID)
```

#### `(defn NAME (PARAMS...) BODY)`
Named function definition. At top level, defines a global function. Inside an
entity (object/room), defines a scoped function visible only within that entity.

```scheme
; Global function
(defn is-lit (obj)
  (and (:light obj)
       (:on obj)))

; Entity-scoped function
(object @door
  (defn check-locked ()
    (if (:locked ?self)
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
(if (:locked @door)
    (blocked :reason locked)
    (success))
```

#### `(let ((VAR VAL) ...) BODY)`
Local binding with sequential semantics (like Clojure's `let`, not Scheme's parallel `let`).
Each binding can reference earlier bindings in the same `let`.
```scheme
(let ((target-room (exit-to ?direction)))
  (if (not (:lit target-room))
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
  ((:locked ?self) (blocked :reason locked))
  (true '((set ?self :open true) (success))))
```

#### `(match (EXPRS...) CLAUSE ...)`
Pattern matching on a tuple of values. Cleaner than nested `cond` when matching
multiple conditions.

```scheme
(match ((:locked ?self) (:open ?self))
  ((true _)      (blocked :reason locked))
  ((_ true)      (blocked :reason already-open))
  ((false false) '((set ?self :open true) (success))))
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

#### `(-> INITIAL EXPR1 EXPR2 ...)`
Thread-first macro. Threads value as first argument through expressions.

```scheme
(-> 5 (+ 3) (* 2))    ; = (* (+ 5 3) 2) = 16
(-> @obj :prop)       ; = (:prop @obj)
```

Each expression receives the previous result as its first argument.

#### `(->> INITIAL EXPR1 EXPR2 ...)`
Thread-last macro. Threads value as last argument through expressions.

```scheme
(->> (list 1 2 3)
  (map (fn (x) (* x 2)))     ; = (map (fn ...) '(1 2 3))
  (filter (fn (x) (> x 3)))) ; = (filter (fn ...) '(2 4 6)) = '(4 6)
```

Useful for collection pipelines where collection is the last argument.

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
Outcome declarations within `cond` clauses. Can be returned directly or as part of
a quoted effect list:
- `(success :context (...))` - Action succeeds with no effects
- `'((effect ...) (success))` - Action succeeds with effects (quoted list)
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
(when (:firsttime ?self)
  (seq (set ?self :firsttime false)
       (inc @player :score 10)))
```

#### `(seq EFFECT ...)`
Sequential effect execution. Effects are executed in order.
```scheme
(seq (move ?self ?actor)
     (set ?self :moved true))
```

#### `(some PRED COLL)`
Existential quantifier (Clojure-style). Returns first truthy result of `(PRED x)`, or nil.
```scheme
(some (fn (?x) (:light ?x)) (inventory))
(some (fn (?x) (> ?x 5)) '(1 3 7 9))  ; => true (from 7)
```

#### `(every? PRED COLL)`
Universal quantifier. Returns true if `(PRED x)` is truthy for all elements.
```scheme
(every? (fn (?x) (:small ?x)) (contents @chest))
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

#### `(:keyword OBJ [DEFAULT])` — Property Access
Keyword as function (Clojure-style). **This is the preferred way to read properties.**
Works for runtime properties and quoted keyword-value lists.
```scheme
(:timer @microwave)                 ; => 0 (read property)
(:heat @food)                       ; => 12 (read property)
(:missing @obj "default")           ; => "default" (with fallback)
(:foo '(:foo "bar" :baz "qux"))     ; => "bar" (quoted list lookup)
```

For writing properties, use the `(set @obj :prop value)` effect in a quoted list:
```scheme
'((set @microwave :timer 120) (success))
```

### Functions (Uniform Evaluation)

Functions have uniform evaluation: all arguments are evaluated before the function
is called. Functions are pure (no side effects).

#### Predicates (Return Boolean or Value)

| Function | Arguments | Returns | Description |
|----------|-----------|---------|-------------|
| `(:key obj)` | - | any | Property value (error if missing) |
| `(:key obj default)` | - | any | Property value (default if missing) |
| `loc` | OBJ | string | Object's location |
| `desc` | OBJ | string | Object's :description |
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
| `get-in` | TARGET KEYS [DEFAULT] | any | Traverse nested structure via list of keys |

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

Effects describe state changes. They use the same syntax in game code (quoted effect lists),
test `:setup` blocks, and the REPL (for debugging).

| Effect | Arguments | Description |
|--------|-----------|-------------|
| `move` | OBJ DEST | Move object to destination |
| `take` | OBJ | Move object to player's inventory (shorthand for `(move OBJ @player)`) |
| `set` | OBJ :PROP VAL | Set property on object (use `:prop true` for boolean flags) |
| `inc` | OBJ :PROP [AMOUNT] | Increment numeric property (default: 1) |
| `queue` | EVENT [COUNT] | Queue event (indefinite or countdown) |
| `dequeue` | EVENT | Remove event from queue |
| `expose` | OBJ | Set `:known true` on entity (makes it available in agent context) |

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
  :properties (:timer 0 :temp 0)
  :behaviors (
    :set-timer (fn ()
      '((set @microwave :timer ?value) (success)))
    :set-temp (fn ()
      (let ((temp-val (condp = ?value warm 1 low 2 medium 3 high 4 nil)))
        '((set @microwave :temp temp-val) (success))))))
```

Bindings are accessed with the `?` prefix:
```scheme
(:locked ?self)              ; is target object locked?
(= ?with @master-key)        ; was master-key used as instrument?
```

The `?` prefix retrieves the binding value. If a binding is not set, it returns `nil`.

#### Lexical Bindings (Lambda Parameters)

In `some` and `every?` quantifiers, the lambda parameter is lexically scoped:
```scheme
(some (fn (?x) (:light ?x)) (inventory))
```
Here `?x` is bound to each inventory item in turn, shadowing any outer `?x`.

#### User-Defined Functions (defn)

Functions defined with `defn` use lexical scoping for parameters:
```scheme
(defn is-lit (obj)
  (and (:light obj)
       (:on obj)))
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
  :setup ((move @pc @player))
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
| `(set @obj :prop VAL)` | Set property on object (inline setup) |
| `(move @obj @loc)` | Move object to location (inline setup) |
| `(inc @obj :prop [AMT])` | Increment property (inline setup) |
| `(queue EVENT [DELAY])` | Queue an event (inline setup) |
| `(dequeue EVENT)` | Remove event from queue (inline setup) |
| `(take @obj)` | Move object to player (inline setup) |

**Inline setup** allows manipulating game state mid-test without using `:setup` blocks.
This is useful for full walkthrough tests that need to skip unimplemented mechanics:

```scheme
(test "walkthrough-full"
  ; ... earlier actions ...

  ; SKIP: Forklift puzzle - pre-set junk state
  (set @junk-pile :moved 4)

  ; Continue with navigation
  (go :direction east)
  (assert (loc? @player @storage-room))

  ; SKIP: Complex ritual state - position for escape
  (move @player @pentagram)
  (set @pentagram :rmung true)

  ; ... continue test ...)
```

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
  :setup ((move @player @kitchen))

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
| `(prop? OBJ PROP VALUE)` | Object property has value |
| `(:prop @obj)` | Check property is truthy |
| `(queued? EVENT)` | Event is in queue |
| `(not-queued? EVENT)` | Event is not in queue |

Any predicate from the expression language (e.g., `visible?`, `here?`, `inside?`) also
works in `(assert ...)` via the evaluator fallback.

### Test Effects

Setup can use any standard effect: `move`, `set`, `inc`, `queue`, `dequeue`, `take`, `expose`.

## Open Questions

1. **NPC modeling** - Are NPCs just objects with PERSON flag and behaviors for
   TALK/ASK/GIVE? Do they need special handling for conversation state?

2. **Lighting propagation** - Does light from objects illuminate containers?
   Rooms? How do we model "the lantern lights the room"?

3. **Scope/disambiguation** - When there are two KEYs visible, how does
   "unlock door with key" resolve? Is this purely LLM responsibility?

4. **Complex conditionals** - ZIL has `PER` routines that do arbitrary computation.
   Can all such cases be expressed declaratively, or do we need an escape hatch?

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
