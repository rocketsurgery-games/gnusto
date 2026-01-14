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

