# Zork I → Grue conversion notes

A running log of what went well, what created friction, and concrete
skill/tooling improvements surfaced while converting Zork I. Zork (1980) is the
*earliest* Infocom game; The Lurking Horror (1987) is one of the latest, so
patterns that show up in both are near-universal and belong in the shared
`translate-zil` skill.

## Process

- Hand-translating directly into clean root `.grue` files (skipping the `zilch`
  bootstrap for small, well-understood slices) is fast and produces tidy output.
  Reserve `zilch` for bulk scaffolding of large unfamiliar files.
- Slice granularity: "white-house exterior + mailbox/leaflet" was a good first
  unit — self-contained, fully testable, gets the canonical opening right.

## What went well

- **LOCAL-GLOBALS / GLOBAL-OBJECTS scenery** → `:location nil` object +
  per-room `:visible (@x ...)` maps over cleanly (white-house, board, forest,
  boarded-window). Matches the LH idiom exactly.
- **Shared barrier objects**: the boarded front door and boarded windows are
  genuine scenery objects *and* the `:via` barriers for the boarded exits, so
  the "blocked exit" and "examinable scenery" collapse into one object with no
  waste.

## Slice 2 (house interior) observations

- **Two flavors of conditional exit.** ZIL's `(DIR TO ROOM IF FLAG IS OPEN)`
  (window, trap door) maps to a `:via` barrier object whose `:through` gates on
  state; ZIL's `(DIR TO ROOM IF FLAG ELSE "msg")` (nailed door, chimney) also
  becomes a `:via` barrier `:through` returning `(blocked :message ...)` on the
  else branch. Only *unconditional* message exits use the new `:blocked` form.
  The barrier's `:through` cleanly reproduces ZIL PER-exits like
  `TRAP-DOOR-EXIT` (rug-not-moved → "You can't go that way"; closed → "The trap
  door is closed"; open → pass).
- **Reveal-by-uncovering** (rug hides trap door) = a `:moved` flag on the rug +
  `(set @trap-door :invisible false)`; the trap door starts `:invisible true`.
  Cross-object writes are fine as long as the *target* declares the property.
- **Darkness is not enforced by the engine yet.** The attic has no ONBIT (it's
  dark), and the brass lantern is the canonical light source, but nothing in the
  runtime blocks seeing/acting in an unlit room or introduces the grue. This is
  the next major cross-cutting mechanic (Zork's whole underground depends on it)
  and almost certainly needs engine support — to be designed with the user
  before the underground slice. For now unlit rooms are marked `:lit false`
  faithfully but behave as lit.

## Friction / tooling observations

- **Test DSL vs REPL `go` syntax diverge.** Tests use `(go :direction east)`;
  the REPL wants `(go east)`. `(go :direction east)` in the REPL is parsed as a
  literal direction `:direction` and returns `no-exit`. Minor, but a footgun for
  manual probing. Candidate: accept both in both places.
- **Blocked messages assert via `(context? message "...")`, not `(output?
  ...)`.** `blocked :message` lands in terminator context, while `output?` only
  scans the narrate/focus/say output stream. `context?` is an *exact* match (no
  substring). Worth an explicit line in the `grue-testing` skill.

## Engine improvements made

- **Deterministic darkness/light + persistent start-events (gnusto-fa93.4).**
  Motivated by Zork's underground. Design settled with the user:
  - `lit?`/`light-source?`/`accessible` are **pure Grue** in `builtins.grue`
    (keyword lookups return defaults, so probing `:lightable` on any object is
    safe). Darkness is **opt-in**: a room's `:lit` defaults true; only `:lit
    false` rooms can go dark, relit by a carried/present lit `:lightable`.
  - Perception is a **thin Python seam** (`is_room_lit` -> the Grue `lit?`):
    `get_room_description` returns the world `:dark-message`, and
    `get_visible_objects(for_description)` returns `[]`, when the player's room
    is unlit. Only the *listing* is suppressed — accessibility (`take` by name)
    is unchanged; the deterrent is the grue.
  - The grue **danger** is game-specific Grue (`grue-hazard.grue`), a hazard
    event of the exact same shape as LH `freezing`: reset when lit, tick a
    `:dark-turns` counter while dark, deterministic death once `:grue-grace`
    (default 1) is spent. No RNG (frotz stays sound). Divergence from ZIL, which
    rolls a random grue death on *movement* in the dark; we count turns, which
    makes the grace clean and is analyzable. Noted intentionally.
  - **`:start-events (evt …)`** (world) queues events indefinitely at init — a
    general facility for always-on background events ("the grue is always
    lurking"; clocks; NPC schedulers). Used to start `grue-lurks` from turn 1.

## Language improvements made

- **Message-only exits → `:blocked` (gnusto-fa93.2).** ZIL rooms very frequently
  use string-exits like `(EAST "The rank undergrowth prevents eastward
  movement.")` — a blocked direction whose only effect is a custom message, with
  *no* associated object. Zork's forest/mountain/house rooms are full of these.
  Added a first-class `(direction :blocked "message")` exit form (mutually
  exclusive with `:to`): parses into `GrueExit.blocked`, `_do_go` returns
  `(blocked :message ...)`, the direction is omitted from the traversable exits
  map, and frotz's explorer skips it. Documented in `docs/grue.md` and the
  `translate-zil` skill. Reserve `:via` barrier objects for boundaries the
  player can actually examine/manipulate (doors, boarded windows).
