# World Definition DSL Design

## Overview

A declarative domain-specific language for defining interactive fiction game worlds. The DSL captures game state, valid actions, transitions, and invariants in a form that is:

1. **Formally verifiable** - State space can be analyzed for winnability, soft-locks, invariant violations
2. **LLM-friendly** - Clear enough for an LLM to understand and reason about
3. **Extensible** - New actions and behaviors without code changes
4. **Extractable from ZIL** - Can be generated from existing Infocom source

## Design Goals

### Primary Goals

- **Correctness over flexibility**: The game state must always be consistent
- **Verifiable winnability**: Provable that a path from start to victory exists
- **Deterministic core**: State transitions are predictable and reproducible
- **LLM integration points**: Explicit places where LLM has interpretive latitude

### Secondary Goals

- Human-readable/writable format
- Tooling support (validation, visualization, analysis)
- Efficient runtime execution
- Round-trip compatibility with ZIL (where possible)

## Expression Language

Expressions use S-expression (Lisp-like) syntax, as a nod to ZIL's MDL heritage
and because S-expressions are trivially parseable, unambiguous, and naturally
form expression trees suitable for static analysis.

### Basic Syntax

```lisp
; Predicates
(has-flag OBJ TAKEBIT)
(= (loc OBJ) PLAYER)
(in? OBJ ROOM)

; Boolean operations
(and EXPR EXPR ...)
(or EXPR EXPR ...)
(not EXPR)

; Comparisons
(= A B)
(> A B)
(< A B)
(>= A B)
(<= A B)

; Property access
(prop OBJ property-name)      ; -> value
(loc OBJ)                     ; -> location of object
(flags OBJ)                   ; -> set of flags

; Quantifiers (for collections)
(any COLLECTION (lambda (x) PRED))
(all COLLECTION (lambda (x) PRED))

; Special forms
(visible? OBJ)                ; shorthand for visibility check
(held? OBJ)                   ; shorthand for (= (loc OBJ) PLAYER)
(here? OBJ)                   ; shorthand for (= (loc OBJ) (loc PLAYER))
```

### Effects Syntax

Effects use a similar S-expression style but with mutation operators:

```lisp
; Move object
(move! OBJ DEST)

; Set flag
(set-flag! OBJ FLAG)
(clear-flag! OBJ FLAG)

; Set property
(set-prop! OBJ PROP VALUE)

; Modify global
(set! GLOBAL VALUE)
(inc! GLOBAL)
(inc! GLOBAL AMOUNT)

; Compound effects
(seq EFFECT EFFECT ...)       ; execute in order
(when COND EFFECT)            ; conditional effect
```

## Core Concepts

### World State

The complete game state at any moment:

```yaml
state:
  player:
    location: TERMINAL-ROOM
    inventory: [FLASHLIGHT, KEY]

  objects:
    FLASHLIGHT:
      location: PLAYER
      flags: [TAKEBIT, LIGHTBIT, ONBIT]
      properties:
        battery_level: 100

    DOOR:
      location: TERMINAL-ROOM
      flags: [DOORBIT]
      properties:
        locked: true

  globals:
    SCORE: 0
    MOVES: 0
    GAME_PHASE: "beginning"
```

### Objects and Rooms

Static definitions of what exists in the world:

```yaml
rooms:
  TERMINAL-ROOM:
    description: "A large room crammed with computer terminals..."
    exits:
      SOUTH:
        to: HALLWAY
        when: (not (prop HACKER blocking))  # S-expr condition
      OUT: HALLWAY
    properties:
      lit: true

objects:
  FLASHLIGHT:
    description: "A sturdy flashlight"
    initial_location: MAINTENANCE-CLOSET
    flags: [TAKEBIT, LIGHTBIT]
    properties:
      battery_level: 100

  HACKER:
    description: "A pale young man hunched over a terminal"
    initial_location: TERMINAL-ROOM
    flags: [PERSONBIT]
    properties:
      blocking: true  # Blocks south exit initially
```

### Actions

Declarative action definitions with S-expression preconditions and effects:

```yaml
actions:
  TAKE:
    syntax: ["take {object}", "get {object}", "grab {object}"]
    preconditions:
      - (has-flag object TAKEBIT)
      - (visible? object)
      - (not (held? object))
    effects:
      - (move! object PLAYER)
    messages:
      success: "Taken."
      not_here: "You don't see that here."
      not_takeable: "You can't take that."

  UNLOCK:
    syntax: ["unlock {object} with {tool}"]
    preconditions:
      - (has-flag object LOCKBIT)
      - (prop object locked)
      - (held? tool)
      - (= (prop tool unlocks) object)
    effects:
      - (set-prop! object locked false)
    messages:
      success: "Click! The {object} is now unlocked."
      wrong_key: "That doesn't fit."
```

### Transitions (State Machine)

For complex multi-step state changes triggered by specific actions:

```yaml
transitions:
  HACKER-LEAVES:
    trigger:
      action: GIVE
      object: ASSIGNMENT
      recipient: HACKER
    when: (here? HACKER)
    effects:
      - (set-prop! HACKER blocking false)
      - (move! HACKER NOWHERE)
      - (inc! SCORE 5)
    message: "The hacker glances at your assignment, nods, and shuffles off."
```

### Invariants

Conditions that must always hold (verified after every state change):

```yaml
invariants:
  # Player must always be in a valid room
  player-in-room: (room? (loc PLAYER))

  # Score can never decrease (uses special prev form)
  score-monotonic: (>= SCORE (prev SCORE))

  # Light source required in dark rooms (or bad things happen)
  light-required:
    check: (or (prop (loc PLAYER) lit)
               (any (inventory PLAYER)
                    (lambda (obj) (and (has-flag obj LIGHTBIT)
                                       (has-flag obj ONBIT)))))
    on-violation: trigger-grue
```

### Win/Lose Conditions

```yaml
victory:
  when: (and (>= SCORE 100) EVIL_DEFEATED)
  message: "Congratulations! You have vanquished the darkness..."

defeat:
  EATEN_BY_GRUE:
    when: (and (not (lit? (loc PLAYER)))
               (>= MOVES_IN_DARK 2))
    message: "Oh no! You have been eaten by a grue!"
```

## LLM Integration Points

### Deterministic vs Stochastic Actions

```yaml
actions:
  TAKE:
    determinism: strict  # Must follow rules exactly
    # ...

  TALK:
    determinism: flexible  # LLM has latitude within constraints
    syntax: ["talk to {npc}", "ask {npc} about {topic}"]
    preconditions:
      - (has-flag npc PERSONBIT)
      - (visible? npc)
    effects: []  # No state change - purely conversational
    constraints:
      # What the LLM MUST respect (natural language, not S-expr)
      - response must be in-character for npc
      - response must not reveal information npc doesn't know
      - response must not imply state changes
    llm_context:
      # Additional context provided to LLM
      - (prop npc personality)
      - (prop npc knowledge)
      - conversation_history
```

### Flavor Text Generation

```yaml
rooms:
  TERMINAL-ROOM:
    description:
      static: "A large room crammed with computer terminals..."
      llm_embellish: true  # LLM can add atmospheric details
      constraints:
        must_mention: [terminals, exit south]
        must_not_mention: (objects-not-in (loc PLAYER))
        tone: "creepy academic"
```

### Outcome Interpretation

For actions where the outcome is determined by state but message is flexible:

```yaml
actions:
  SEARCH:
    syntax: ["search {container}"]
    preconditions:
      - (has-flag container SEARCHABLE)
    outcomes:
      found:
        when: (prop container has_hidden_item)
        effects:
          - (move! (prop container hidden_item) (loc PLAYER))
          - (set-prop! container has_hidden_item false)
        message_template: "You find {(prop container hidden_item)}!"
      nothing:
        when: (not (prop container has_hidden_item))
        effects: []
        llm_message: true  # LLM generates "nothing found" flavor
```

## Formal Verification

### State Space Analysis

The DSL enables:

```
Given: Initial state S₀
Prove: ∃ path P where P(S₀) → Victory

Check: ∀ reachable states S:
  - invariants(S) holds
  - ¬defeat(S) ∨ ∃ recovery path
```

### Tools We Could Build

1. **Winnability checker** - BFS/DFS through state space
2. **Soft-lock detector** - Find states with no path to victory
3. **Invariant validator** - Verify no transition violates invariants
4. **Difficulty estimator** - Minimum steps to victory
5. **Hint generator** - Given current state, suggest next action

## File Format

YAML for human readability, with JSON schema for validation:

```
game/
  world.yaml       # Core definitions
  rooms.yaml       # Room definitions
  objects.yaml     # Object definitions
  actions.yaml     # Action definitions
  npcs.yaml        # NPC definitions with personalities
  transitions.yaml # Complex state transitions
  invariants.yaml  # Game invariants
  schema/          # JSON Schema for validation
```

Or single-file for simple games:

```yaml
# lurking-horror.world.yaml
meta:
  name: "The Lurking Horror"
  author: "Infocom"
  version: "1.0"

rooms:
  # ...

objects:
  # ...

actions:
  # ...
```

## Migration Path

### Phase 1: Extract from ZIL
- Parse existing ZIL source
- Generate DSL definitions for rooms, objects
- Extract SYNTAX → action mappings

### Phase 2: Core Runtime
- DSL parser and validator
- State machine executor
- Basic action handling

### Phase 3: Verification Tools
- State space explorer
- Winnability checker
- Invariant validator

### Phase 4: LLM Integration
- Flexible action handlers
- Description embellishment
- NPC conversation system

## Related Documents

- **[Behavioral DSL Extension](./behavioral-dsl.md)** - Object-specific behaviors, conditional responses, state-dependent logic

## Open Questions

1. **Expression language**: What syntax for preconditions/effects?
   - Simple predicates? Full expression language?
   - Needs to be parseable AND verifiable
   - **Resolved**: S-expressions, see Expression Language section

2. **Inheritance/composition**: Can objects/actions inherit from templates?
   - See behavioral-dsl.md for object type inheritance discussion

3. **Scripting escape hatch**: Do we need a way to drop to code for truly complex logic?
   - **Resolved**: No. Behavioral DSL handles complex cases declaratively.

4. **Serialization**: How do we save/load game state?

5. **Debugging**: How do we trace why an action failed or state changed?

6. **Versioning**: How do we handle DSL evolution while maintaining compatibility?
