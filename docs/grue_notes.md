# Grue Language + Runtime

## Globals → Object Properties (frotzlm-krs)
Globals are a ZIL/MDL legacy from 70s 8-bit systems. We're eliminating them in favor of
Clojure-style object properties:

```scheme
; Old (globals)
(globals :microwave-timer 0)
(set! microwave-timer 120)

; New (object properties)
(object @microwave :properties (:timer 0))
(:timer @microwave)                        ; keyword-as-function read
(success :effects ((set @microwave :timer 120)))  ; effect for mutation
```

See epic frotzlm-krs for implementation tasks.


## Flag/bit cleanup
- Are these really different from boolean props? Or was it just an optimization in grue?
- They're used for lots of "built-in" behaviors; is there a cleaner way to accomplish this?

### Runtime flags
These flags have effects built into the runtime. We should consider whether there's a more general mechanism that doesn't rely upon these very specific flags being baked into the runtime.

- NDESCBIT   - Exclude objects from room descriptions
- INVISIBLE  - Used in get_inventory() and is_visible()
- ONBIT      - Lit room
- PERSON     - Mainly in game code; used as a fallback in _find_player_name()
- VEHBIT     - Marks an object as a "vehicle"
- SURFACEBIT - Overrides visibility for objects on surfaces; on > in
- OPENBIT    - Overrides visibility in open/transparent containers
- TRANSBIT   - ...

### Game flags
These are only used in game code, but they could just as well be boolean properties. This may have just been an optimization for the old 8-bit implementations.

AN CONTBIT DOORBIT LOCKED NOABIT NOTHEBIT OUTSIDE POWERBIT READBIT RLANDBIT RMUNGBIT SEARCHBIT SLIMEBIT TAKEBIT THE TOOLBIT TOUCHBIT TRYTAKEBIT WEAPONBIT WEARBIT


## Result context
What do we _really_ want from effects like `(success :context (description "..."))`? Consider pulling all the context (e.g., `:context ((timer-display ...`) into explicit ui-effects that give instructions on how context should be displayed to the user.

This is best addressed when we start bolting on the LLM adapter for real. This will give us a much clearer idea of what we need to solve real needs.

## Drop/Take implementation
Are constructs like `(do @something :take)` properly generalized across actors? I.e., could we re-use them for NPCs without modification or special-casing?

## Multiline strings
It could make strings a lot more readable if we made multi-line string literals that require explicit
carriage-returns.

## Dynamic instantiation
Dare we broach the idea of dynamically-allocated objects and perhaps rooms? The current structure is really nice in that you can refer to any @object or @room with a single symbol. OTOH, it's somewhat limiting if you want to create new objects at runtime, rather than just shuffling them in and out of rooms / containers / nil.

The obvious downside is that it complicates references, adds garbage collection, requires new syntax and runtime support, etc. Likely only worth it, in its general form, if there's a compelling need. Though we might find some simpler approaches that get at necessary use-cases without full generality of allocation.

## Multi-part encapsulation
Can we completely encapsulate something complex like the elevator, so that it's easily reusable?
- It uses globals to track state -- buttons, direction, location, etc.
- Multiple door objects connecting in/out of external rooms
  - (@cs-elevator-room) exit connects back to itself
  - (@elevator-exit) redirects to external room on exit
  - So elevator needs to know about its external connecting rooms statically


# Development tools

## Tree-sitter grammar
- Can we do something to make rooms / objects / events have better default icons in aerial?
- (event) missing from aerial hierarchy.

## LSP
We could really use an LSP for developer tools, to handle refactoring, symbol resolution, etc. Maybe this would obviate the tree-sitter grammar as well?

Hopefully we can just implement this on top of the existing python parser and related code.

