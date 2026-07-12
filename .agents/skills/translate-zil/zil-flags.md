# ZIL flags → Grue properties (conversion reference)

Infocom ZIL controls object behavior with bit `FLAGS`. In Grue these become
`:properties (:name true ...)`. This mapping is the same across Infocom games
(Zork, Enchanter, LH, …). **Grue is strict about properties: every property a
behavior/event reads or writes must be declared** in the entity's `:properties`
(a write to an undeclared property raises an error at runtime — run
`frotz lint <game>` to catch these statically, even on cold paths).

## Flag reference

### Visibility & description
| ZIL flag | Grue | Meaning |
|----------|------|---------|
| `INVISIBLE` | `:invisible true` (or `:location nil`) | Not seen/interactable until revealed |
| `NDESCBIT` | `:nodesc true` | Interactable but NOT listed in the room's object list. Use for scenery named in the room `:ldesc`, screen/UI elements, or items carried by an NPC |
| `TOUCHBIT` | `:touched` | "Seen/handled" — drives first-vs-subsequent description, or as a "revealed" flag |

### Containers & surfaces
| ZIL flag | Grue | Meaning |
|----------|------|---------|
| `CONTBIT` | `:container true` | Can hold objects |
| `OPENBIT` | `:open true` | Currently open (contents accessible; door passable) |
| `OPENABLE` | `:openable true` | Can be opened/closed (implies `:open false` by default) |
| `SEARCHBIT` | `:searchable true` | Contents can be examined/found |
| `TRANSBIT` | `:transparent true` | Contents visible even when closed (glass case) |
| `SURFACEBIT` | `:surface true` | Items go "on" not "in" |

### Taking / vehicles / rooms / state
| ZIL flag | Grue | Meaning |
|----------|------|---------|
| `TAKEBIT` | `:takeable true` | Can be picked up |
| `TRYTAKEBIT` | `:trytake true` | Parser allows "take" but the object's own `:take` blocks/customizes it (heavy/fixed items) |
| `VEHBIT` | `:vehicle true` | Player can be inside it (chairs, boats); player location becomes this object |
| `ONBIT` (room) | `:lit true` | Room is lit (see without a light source) |
| `RLANDBIT`/outdoor | `:outside true` | Outdoors (weather, freezing, grue-in-the-dark, etc.) |
| `RMUNGBIT` | `:rmung` | Ruined / consumed / destroyed (cut cable, broken glass, eaten food) |
| `LOCKED` | `:locked true` | Needs a key/action to open |
| `DOORBIT` | `:door true` | A door; blocks passage when closed |
| `LIGHTBIT`+`ONBIT` | `:lightable`/`:lit` | Provides light when on (implied pair: `:lightable → :lit false`) |

### Actors, combat, kinds
| ZIL flag | Grue | Meaning |
|----------|------|---------|
| `PERSON` | `:person true` | NPC — enables ask/tell/give/attack/follow |
| `WEAPONBIT` | `:weapon true` | Usable as a weapon ("attack X with Y", "throw Y at X") |
| `TOOLBIT` | `:tool true` | A tool; may be required for certain actions |
| `WEARBIT` | `:wearable true` | Can be worn (implies `:worn false`) |
| `READBIT` | `:readable true` | Has text to read |
| `FOODBIT` | `:food true` | Edible |
| `KEYBIT` | `:key`/via `:unlock` arg | A key |

Parser/article flags (`NOABIT`, `THEBIT`, `AN`, `SYNONYM`, `ADJECTIVE`) are
**mostly irrelevant** in Grue: the LLM front-end resolves names, and the formal
action interface (`(do @x :verb @arg)`) doesn't need adjectives. Drop them.

## Common property patterns
```grue
:properties (:takeable true)                                   ; portable item
:properties (:nodesc true)                                     ; scenery (in room, not listed)
:properties (:container true :searchable true :openable true)  ; closed container
:properties (:container true :open true :searchable true)      ; open container
:properties (:container true :open true :searchable true :surface true)  ; table/counter
:properties (:vehicle true :surface true :container true :open true :searchable true)  ; chair/bed
:properties (:person true :container true :open true :searchable true)   ; NPC + inventory
:properties (:lit true)                                        ; lit indoor room
:properties (:outside true)                                    ; dark/outdoor room
:properties (:takeable true :trytake true)                     ; heavy item w/ custom take
```

## Pseudo-objects visible in many rooms (`LOCAL-GLOBALS` / `GLOBAL-OBJECTS`)
Infocom uses `(IN LOCAL-GLOBALS)` / `(IN GLOBAL-OBJECTS)` for scenery referenced
from many rooms (walls, forest, the white house, water). In Grue, model these as
objects with `:location nil` plus a room's `:visible (@thing ...)` list (or a
global-object convention), not as a real occupant of one room. They usually carry
`:nodesc true` and exist mainly to answer examine/interact.

## Runtime property checks (where these matter)
- `is_visible()` filters `:invisible`; recursively honors container `:open`/`:transparent`.
- Room object listing filters `:nodesc`.
- Engine default behaviors key off `:takeable`, `:container`, `:open`, `:openable`, `:surface`, `:vehicle`, etc.
- Reads/writes use `(:prop @obj)` / `(set @obj :prop v)` — **both require `:prop` declared**.
