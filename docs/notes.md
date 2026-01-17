# Grue Language + Runtime

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

## Globals
Are globals really necessary at all? Why not just force them to be object properties?

## Flag/bit cleanup
- Are these really different from boolean props? Or was it just an optimization in grue?
- They're used for lots of "built-in" behaviors; is there a cleaner way to accomplish this?

Existing flags:
- AN         - the fuck is this?
- CONTBIT    -
- DOORBIT    -
- INVISIBLE  -
- LOCKED     -
- NDESCBIT   -
- NOABIT     -
- NOTHEBIT   -
- ONBIT      -
- OUTSIDE    -
- OPENBIT    -
- PERSON     -
- POWERBIT   -
- ;RAIRBIT   -
- READBIT    -
- RLANDBIT   -
- RMUNGBIT   -
- ;RWATERBIT -
- SEARCHBIT  -
- SLIMEBIT   -
- SURFACEBIT -
- TAKEBIT    -
- THE        -
- TOOLBIT    -
- TOUCHBIT   -
- TRANSBIT   -
- TRYTAKEBIT -
- VEHBIT     -
- WEAPONBIT  -
- WEARBIT    -

## Result context
What do we _really_ want from effects like `(success :context (description "..."))`? Consider pulling all the context (e.g., `:context ((timer-display ...`) into explicit ui-effects that give instructions on how context should be displayed to the user.

This is best addressed when we start bolting on the LLM adapter for real. This will give us a much clearer idea of what we need to solve real needs.

## Drop/Take implementation
Are constructs like `(do @something :take)` properly generalized across actors? I.e., could we re-use them for NPCs without modification or special-casing?


# Developer tools

## Tree-sitter grammar
- Can we do something to make rooms / objects / events have better default icons in aerial?
- (event) missing from aerial hierarchy.

## LSP
We could really use an LSP for developer tools, to handle refactoring, symbol resolution, etc. Maybe this would obviate the tree-sitter grammar as well?

Hopefully we can just implement this on top of the existing python parser and related code.


# UI
The existing UI is just a terminal repl that requires you to interact via Grue syntax. I propose that we should have multiple UI modes:
- REPL:  Useful as a debugging tool.
- TUI:   A "real" terminal UI, that uses the LLM for interaction.
- GUI:   Conceptually the same as the terminal UI, but with images, and other bells and whistles.
- Voice: A voice input/output UI suitable for phones and visually-impaired players.

## Style
For the GUI mode, we want to add graphics judiciously, while respecting the feel (feelies?) of the original game. 

### Zork
Hand-drawn "Teenagers playing D&D" aesthetic.

### Enchanter: 
Florid calligraphy on parchment, much like the game's original feelies.

### Infidel: 

### Lurking Horror: 

### AMFV: 

## Terminal
In the terminal UI, how can we segregate different text streams?
- Room description
- Object, exit, character descriptions
- Conversation
- Action / reaction
- ...

## Notes, maps, & context
It would be a significant improvement to have much of this stuff taken on for you, like most modern games. Stylistically, we could still evoke a hand-written aesthetic (or whatever form's appropriate for the game in question).

