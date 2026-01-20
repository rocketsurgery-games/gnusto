# Grue Language + Runtime

## Visible objects
`(room :visible (@obj) ... )` declares objects visible from multiple rooms even when their `:location` is elsewhere or `nil`. Useful for doors (visible from both sides), spanning objects (cables, pipes), and abstract scenery.

## Dynamic instantiation
Dare we broach the idea of dynamically-allocated objects and perhaps rooms? The current structure is really nice in that you can refer to any @object or @room with a single symbol. OTOH, it's somewhat limiting if you want to create new objects at runtime, rather than just shuffling them in and out of rooms / containers / nil.

The obvious downside is that it complicates references, adds garbage collection, requires new syntax and runtime support, etc. Likely only worth it, in its general form, if there's a compelling need. Though we might find some simpler approaches that get at necessary use-cases without full generality of allocation.

## Multi-part encapsulation
Can we completely encapsulate something complex like the elevator, so that it's easily reusable?
- It uses object properties to track state -- buttons, direction, location, etc.
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

