# The Lurking Horror - FrotzLM / Grue conversion

This is a conversion of Infocom's _The Lurking Horror_ to Grue, to execute in the FrotzLM runtime.

# Structure

`./lurkinghorror.grue` is the entrypoint, defining the world and player objects. The rest of the files are largely
organized by room (e.g., `./terminal-room.grue`), object (e.g., `./pc.grue`), and character (`./hacker.grue`). Most
non-trivial objects have unit tests (as in `./terminal-room.test.grue`) to validate their behavior.

# Running the Original

The original compiled game is in ./compiled/lurking.dat, and can be run from the root of the repo with `frotz
games/lurkinghorror/lurking.dat`. There are also sound files in that directory, but they haven't been integrated.

# Object Flags Reference

ZIL uses bit flags to control object behavior. These are set via `:flags (FLAG1 FLAG2 ...)` in Grue. Understanding
these flags is essential when converting ZIL source to Grue.

## Visibility and Description

| Flag | Purpose | Runtime Behavior |
|------|---------|------------------|
| **INVISIBLE** | Object cannot be seen or interacted with | `is_visible()` returns false; parser won't find it |
| **NDESCBIT** | "No describe" - object not listed in room descriptions | Visible/interactable but not shown in "Visible:" list. Use for scenery mentioned in room ldesc (microwave, refrigerator), screen elements (menu-box), or items carried by NPCs (keyring on hacker) |
| **TOUCHBIT** | Object has been "seen" or "touched" by player | Used to show FDESC (first description) vs LDESC (subsequent). Also used as a "revealed" flag (e.g., master-key becomes visible when hacker mentions it) |

## Containers and Surfaces

| Flag | Purpose | Runtime Behavior |
|------|---------|------------------|
| **CONTBIT** | Object is a container | Can hold other objects via `(in? obj container)` and `(move! obj container)` |
| **OPENBIT** | Container/door is currently open | Contents visible; player can take/put items. For containers: contents accessible. For doors: passage allowed |
| **OPENABLE** | Container/door can be opened/closed | Enables :open and :close behaviors |
| **SEARCHBIT** | Contents can be searched/examined | With OPENBIT or TRANSBIT, parser can find contents. Required for examining inside containers |
| **TRANSBIT** | Container is transparent | Contents visible even when closed (glass case, etc.). Combined with SEARCHBIT, contents are findable |
| **SURFACEBIT** | Object is a surface (table, counter) | Items placed "on" rather than "in". Changes prepositions in descriptions |

Typical combinations:
- Open container: `CONTBIT OPENBIT SEARCHBIT` (box, drawer)
- Closed container: `CONTBIT SEARCHBIT OPENABLE` (needs to be opened first)
- Transparent container: `CONTBIT TRANSBIT SEARCHBIT` (glass case - see inside but can't reach)
- Surface: `CONTBIT OPENBIT SEARCHBIT SURFACEBIT` (table, counter)
- Closed surface: Rare but possible for desks with items on top

## Taking and Carrying

| Flag | Purpose | Runtime Behavior |
|------|---------|------------------|
| **TAKEBIT** | Object can be picked up | Default :take behavior works; object can be moved to player inventory |
| **TRYTAKEBIT** | Object seems takeable but has special handling | Parser allows "take X" but the object's behavior blocks or customizes it. Used for heavy objects (PC), fixed objects, or objects with side effects |

## Vehicles and Sitting

| Flag | Purpose | Runtime Behavior |
|------|---------|------------------|
| **VEHBIT** | Object is a "vehicle" - player can be inside it | Enables "sit in/on", "enter". Player's location becomes this object. Used for chairs, beds, vehicles |
| **FURNITURE** | Object is furniture | Variant of VEHBIT for immobile sittable objects. Player can sit but can't take it |

## Rooms

| Flag | Purpose | Runtime Behavior |
|------|---------|------------------|
| **ONBIT** | Room is lit | Player can see without a light source. Most indoor rooms have this |
| **OUTSIDE** | Room is outdoors | Used for weather effects, freezing mechanic, etc. |

## Object State

| Flag | Purpose | Runtime Behavior |
|------|---------|------------------|
| **RMUNGBIT** | "Ruined/munged" - object is consumed or destroyed | Set when food is eaten (snack wrapper), items are burned, etc. Usually means object's original purpose is gone |
| **LOCKED** | Door/container is locked | Requires a key or special action to open |
| **DOORBIT** | Object is a door | Blocks passage when closed; connects rooms |
| **POWER** | Object is powered on | Custom flag for electrical devices (PC, flashlight) |

## Actors and NPCs

| Flag | Purpose | Runtime Behavior |
|------|---------|------------------|
| **PERSON** | Object is a person/NPC | Enables conversation, following, and combat. Parser recognizes for "ask", "tell", "give" |
| **OPENBIT + CONTBIT** (on PERSON) | Person can carry/hold objects | Contents are their inventory. With SEARCHBIT, you can examine what they carry |

## Combat and Tools

| Flag | Purpose | Runtime Behavior |
|------|---------|------------------|
| **WEAPONBIT** | Object can be used as a weapon | "Attack X with Y" works. Also affects "throw at", "hit with" |
| **TOOLBIT** | Object is a tool | May be required for certain actions |

## Parser/Article Flags (less relevant for Grue)

| Flag | Purpose | Original Use |
|------|---------|--------------|
| **NOABIT** | No article "a/an" | Parser: "Chinese food" not "a Chinese food" |
| **NOTHEBIT** | No article "the" | Parser: "it" not "the it" |
| **AN** | Uses "an" instead of "a" | Parser: "an elevator" not "a elevator" |
| **THE** | Always uses "the" | Parser: "the flashlight" |
| **READBIT** | Object has text that can be read | Enables :read behavior |
| **FOODBIT** | Object is food | Enables :eat behavior; hacker responds to food gifts |
| **KEYBIT** | Object is a key | Works with :unlock behavior |
| **WEARBIT** | Object can be worn | Enables :wear, :remove behaviors |
| **LIGHTBIT** | Object provides light | Enables illumination when ONBIT set |

## Common Patterns

```scheme
; Takeable object - can pick up and carry
:flags (TAKEBIT)

; Scenery - visible in room but not in listing, can't take
:flags (NDESCBIT)

; Container that starts closed
:flags (CONTBIT SEARCHBIT OPENABLE)

; Open container (e.g., box that starts open)
:flags (CONTBIT OPENBIT SEARCHBIT)

; Surface (table, counter)
:flags (CONTBIT OPENBIT SEARCHBIT SURFACEBIT)

; Chair/bed - can sit in/on
:flags (VEHBIT SURFACEBIT CONTBIT OPENBIT SEARCHBIT)

; NPC with inventory
:flags (PERSON CONTBIT OPENBIT SEARCHBIT)

; Lit indoor room
:flags (ONBIT)

; Dark outdoor room
:flags (OUTSIDE)

; Hidden object - revealed later
:flags (INVISIBLE)  ; or start with location nil

; Screen UI element
:flags (NDESCBIT READBIT)

; Heavy object with custom take
:flags (TAKEBIT TRYTAKEBIT)
```

## Runtime Implementation Notes

The runtime checks these flags in several places:
- `is_visible()`: Filters INVISIBLE; recursively checks container OPENBIT/TRANSBIT
- `get_visible_objects(for_description=True)`: Also filters NDESCBIT for room listings
- Default behaviors use TAKEBIT, CONTBIT, OPENBIT, etc. to determine valid actions
- Events can use `has-flag` and `set-flag!`/`clear-flag!` to check and modify flags


# ZIL to Grue Conversion Pitfalls

This section documents patterns in ZIL that are easy to miss or misunderstand when converting to Grue.

## Verb-Level State Machines

**Problem**: Some mechanics live in verb handlers, not object behaviors. These are easy to miss because
our conversion process focuses on objects.

**Example**: The PC login flow uses V-TYPE, V-LOGIN, and V-PASSWORD verb routines with global state
variables (USERNAME?, LOGGED-IN?) to implement a multi-step interaction:

```zil
; In ZIL, the TYPE verb redirects based on state
<ROUTINE V-TYPE ()
   <COND (<NOT ,USERNAME?>
          <NEW-VERB ,V?LOGIN>)    ; Redirect to login
         (<NOT ,LOGGED-IN?>
          <NEW-VERB ,V?PASSWORD>) ; Redirect to password
         ...>>
```

**In Grue**: Convert to object behaviors that check object properties:

```scheme
(object @pc
  :properties (:logged-in false :username false)
  :behaviors (
    :type (fn (?value)
      (cond
        ((not (:username @pc)) (redirect :action (do ?self :login ?value)))
        ((not (:logged-in @pc)) (redirect :action (do ?self :password ?value)))
        ...))))
```

**How to spot**: Look for:
- `NEW-VERB` calls that redirect to other verbs based on state
- Global variables like `FOO?` that track multi-step flows
- SYNTAX definitions for custom verbs (LOGIN, PASSWORD, etc.)

## INIT-* Routines for State Reset

**Problem**: ZIL often has INIT-FOO routines that reset state when objects change (power off, close, etc.).
These are called from multiple places and easy to miss.

**Example**: INIT-PC resets login state and removes screen elements:

```zil
<ROUTINE INIT-PC ()
   <FCLEAR ,PC ,POWERBIT>
   <SETG LOGGED-IN? <>>
   <SETG USERNAME? <>>
   <REMOVE ,MENU-BOX>
   <REMOVE ,MORE-BOX>
   ...>
```

**In Grue**: Include these effects in all relevant behaviors:

```scheme
:turn-off (fn ()
  '((clear-flag ?self POWER)
    (set @pc :logged-in false)
    (set @pc :username false)
    (move @menu-box nil)
    (move @more-box nil)
    (success)))
```

**How to spot**: Search for `INIT-` routines and trace all call sites.

## Objects That Start in Limbo

**Problem**: Some objects start with no location (REMOVE'd or never placed) and only appear after
certain actions. Easy to assume they start somewhere visible.

**Example**: MENU-BOX only appears on the PC screen after successful login:

```zil
; MENU-BOX has no (IN ...) declaration - starts in limbo
<OBJECT MENU-BOX
   (DESC "menu box")
   ...>

; Only moved to PC after password succeeds
<ROUTINE V-PASSWORD ()
   ...
   <MOVE ,MENU-BOX ,PC>
   ...>
```

**In Grue**: Set `:location nil` and move via effects:

```scheme
(object @menu-box
  :location nil  ; Starts hidden
  ...)

:password (fn (?value)
  '((move @menu-box @pc) (success)))
```

**How to spot**: Objects without `(IN ...)` in ZIL, or with `(IN GLOBAL-OBJECTS)` or `(IN LOCAL-GLOBALS)`.

## Physical Parts vs. Conceptual Contents

**Problem**: Objects can contain both physical parts (always present) and conceptual contents
(appear/disappear based on state). Need to distinguish them for descriptions.

**Example**: The PC contains mouse and help-key (physical, always there) plus screen elements
(menu-box, yak-window, etc. that come and go):

```zil
; Physical parts - always in PC
<OBJECT MOUSE (IN PC) (FLAGS NDESCBIT) ...>
<OBJECT HELP-KEY (IN PC) (FLAGS NDESCBIT) ...>

; Screen elements - moved in/out dynamically
<OBJECT MENU-BOX ...>  ; Moved to PC after login
```

**In Grue**: Filter by flag or explicitly check specific objects:

```scheme
; Don't just use (first (contents ?self)) - that might return @mouse!
:examine (fn ()
  (cond
    ((in? @odd-paper ?self) ...)   ; Check screen elements specifically
    ((in? @menu-box ?self) ...)
    ...))
```

**How to spot**: Objects with NDESCBIT inside containers are usually "part of" not "contents of".

## Testing Against the Original

**Best practice**: Run `dfrotz games/lurkinghorror/compiled/lurking.dat` to test the original game's
behavior. This reveals interaction flows that aren't obvious from reading ZIL source.

Common discoveries:
- Multi-step sequences (login flow, combination locks)
- Required preconditions (must be seated? must be holding X?)
- State dependencies (only works after Y happens)
- Custom rejection messages

