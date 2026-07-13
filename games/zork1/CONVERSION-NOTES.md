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

## Slice 3 (cellar + troll room) observations

- **Deterministic combat.** ZIL's troll fight is a random melee (MELEE tables +
  `PROB`). Converted to a deterministic strength duel (troll `:strength 2`; each
  armed blow decrements; 0 = dead, drops the axe, opens the passages) — same
  reasoning as the grue (keep frotz sound). Troll counter-attacks / knockout /
  give-food mechanics deferred and noted.
- **An NPC can be its own exit barrier.** The troll is the `:via` object for the
  troll room's east/west exits; its `:through` fends you off while alive and
  passes once `:dead`. No separate barrier object needed — the ZIL
  `IF TROLL-FLAG ELSE "..."` exit collapses onto the actor.
- **The dungeon is dark** (cellar + troll room have no ONBIT): the grue system
  gets its real workout here — the lit lantern becomes mandatory, and combat
  tests must carry one or the grue ends the fight.

## Slice 4 (Round Room + chasm/Gallery loop) observations

- **The chimney escape loop closes.** Studio -> up -> Kitchen via a `:via
  @chimney` barrier whose `:through` enforces ZIL's UP-CHIMNEY-FUNCTION rule
  (carry the lantern + at most one other item). This is the intended route for
  hauling treasures back up to the trophy case, and it validated the reusable
  scenery barrier + the `inventory`/`count`/`held?` builtins nicely.
- **Gallery is the one lit underground room** (ONBIT -> `:lit true`); everything
  else down here is `:lit false`, so the lantern stays mandatory.
- **Treasure tagging convention** established for the upcoming scoring slice:
  treasures carry `:treasure true :value N :tvalue N` (ZIL VALUE = take points,
  TVALUE = trophy-case points). The painting is the first; scoring will consume
  these when treasures land in the trophy case.

## Slice 6 (the thief) observations

- **Deterministic stationary thief.** ZIL's thief wanders, steals, and fights on
  random rolls (I-THIEF / ROBBER-FUNCTION). Converted to a fixed lair encounter
  in the (dark) Treasure Room with a deterministic duel, matching the
  troll/cyclops treatment. The full original behavior is documented in a header
  comment in `thief.grue`, and a richer still-analyzable version is tracked in
  **gnusto-fa93.9** (low-pri).
- **The "distract-then-strike" puzzle survives as a deterministic hook:** giving
  the thief a treasure sets `:engrossed`, and an engrossed thief takes 3 damage
  per blow instead of 2 (falls in 2 hits, not 3). The signature **egg puzzle is
  intact**: hand him the fragile egg and he opens it without wrecking the
  clockwork canary; open it yourself and the canary breaks (`:tvalue` 5->2).
- **Treasure Room is dark** — corrected from an earlier `:lit true`; ZIL's
  `RLANDBIT`-only (`CANT-HAVE-ONBIT`) den needs the lantern.
- **Testing gotcha:** a `test`'s `:setup` **merges after** (does not replace) the
  enclosing `test-group`'s `:setup`, so a bindings/items placed by the group
  setup persist into a child test. A bare-handed-attack test failed because the
  group setup had already armed the player. Fix: keep shared state minimal at the
  group level and put mutually-exclusive setup on the individual tests.

## Slice 8 (temple / dome / Egypt) observations

- **Rope/dome descent** models ZIL DOME-FLAG as `:tied` on the attic rope: tie it
  to the dome railing (the railing is both the tie-target and the `:via` barrier
  for the drop), then climb down one-way into the Torch Room (`up` is blocked —
  "You cannot reach the rope").
- **A second light source.** The flaming torch is a treasure that is also a
  permanent light (`:lightable :lit true`, always on). REPL-confirmed it lights
  the dark Egyptian Room with the lantern switched off — validating that `lit?`
  works with any carried source, not just the lamp.
- **Treasures banked:** torch (14/6), gold coffin (10/15, heavy, holds the
  sceptre), sceptre (4/6, for the rainbow later).
- **Deferred:** the altar `pray` teleport (needs the forest); the altar's
  down-hole to Hades + the bell/book/candle exorcism (Hades slice); the
  sceptre->rainbow (river slice). `frotz map`: `@engravings-cave` resolved;
  frontier now `@atlantis-room`/`@dam-base`/`@tiny-cave`/forest+surface.

## Engine fixes made mid-slice

- **Room `:on-enter` `(narrate …)` output was dropped from the `go` result.**
  `_do_go` merged on-enter effects + context but not the *output* stream, so
  arrival narration (the cellar trap door "crashes shut") was silently lost.
  Fixed to merge on-enter output. Affects any game with arrival narration.
- **Behavior arity is strict.** A bare `(do @troll :attack)` errors against
  `:attack (fn (?weapon) …)`; callers must pass `nil` (`(do @troll :attack
  nil)`), matching the LH convention. Candidate future ergonomic: optional /
  variadic behavior params so "attack" works with or without a named weapon.

## Friction / tooling observations

- **Test DSL vs REPL `go` syntax diverge.** Tests use `(go :direction east)`;
  the REPL wants `(go east)`. `(go :direction east)` in the REPL is parsed as a
  literal direction `:direction` and returns `no-exit`. Minor, but a footgun for
  manual probing. Candidate: accept both in both places.
- **Blocked messages assert via `(context? message "...")`, not `(output?
  ...)`.** `blocked :message` lands in terminator context, while `output?` only
  scans the narrate/focus/say output stream. `context?` is an *exact* match (no
  substring). Worth an explicit line in the `grue-testing` skill.

## Slice 5 (maze + cyclops) observations

- **Maze topology copied verbatim** (MAZE-1..15 + 4 dead ends + grating room).
  The `MAZE-DIODES` one-way passages became plain exits to their fixed target;
  the one-way-ness is inherent (the target has no reverse exit), so no special
  machinery — only the courtesy "you can't get back" message is dropped.
- **The cyclops is an unkillable NPC puzzle with two solutions**, both
  deterministic: naming Ulysses/Odysseus (`:odysseus`) routs him — setting
  `:subdued` (stairs up clear) *and* `(:magic @wooden-door)` (east wall smashed) —
  while feeding lunch-then-water only lulls him asleep (stairs clear, wall
  intact). The cyclops is again its own `:via` barrier for the stairs.
- **MAGIC-FLAG finally wired.** The cyclops's flight sets `(:magic
  @wooden-door)`, which flips the Living Room's long-nailed west door into the
  Strange Passage shortcut — a satisfying loop-closer three slices after the door
  was first stubbed.
- **Tooling: the maze motivated `frotz map`, now built (gnusto-otr.11).** It
  dumps the room graph + a dangling-reference report: an exit/`:location`
  *frontier* (the "what's left to wire" ledger — 10 undefined rooms + `@egg ->
  @nest` for Zork right now) and typo-prone `:via`/`:visible` refs (`--strict-refs`
  CI gate). It immediately paid off by finding latent LH issues (6 dangling
  `:visible` refs; 23 objects at an undefined `@global`), tracked in
  gnusto-otr.11.1. `--rooms` marks dark rooms; `--dot` renders Graphviz.
- **Deferred:** thief + Treasure Room loot (next slice); the rusty-knife death
  curse and the skeleton "disturb the remains" curse (both simplified to
  warnings); the grating->surface opening (forest slice); and the Living Room's
  *dynamic* description (it still reads "nailed shut" after MAGIC-FLAG — ZIL's
  LIVING-ROOM-FCN rewrites it; minor cosmetic, tracked).

## Slice 7 (reservoir + dam) observations

- **Water-level state machine.** The dam is a clean multi-step puzzle: yellow
  button -> `:bolt-enabled` (energize the bubble), turn the bolt *with the
  wrench* -> toggle `:gates-open` (== ZIL LOW-TIDE), which reveals the trunk,
  opens the reservoir crossing (`:via @reservoir-water`), and quiets the Loud
  Room so the platinum bar is takeable. ZIL's ~8-turn drain/fill
  (I-REMPTY/I-RFILL) is collapsed to an immediate flip (deterministic; the delay
  wasn't puzzle-critical).
- **The red button showcases the darkness system:** the Maintenance Room is dark
  (no ONBIT), and the red button toggles its `:lit` — you press it by name in the
  dark (accessibility is unaffected) and the room lights up.
- **The blue-button flood is a THIRD hazard event** (after the grue and LH's
  freezing), reusing the exact pattern: rise while you stay, dequeue+reset when
  you leave, deterministic drown past the grace. The pattern is proving very
  robust — reinforcing the case for a shared `hazard` helper (wishlist / adjacent
  to gnusto-fa93.9).
- **`frotz map` drove the slice.** Its frontier list picked the targets
  (@loud-room/@reservoir-south/@deep-canyon), and after wiring it advanced to the
  next frontier (@atlantis-room/@dam-base/@damp-cave) — exactly the ledger I
  wanted. Deferred: the Loud Room `echo` verb (bar is quieted via draining for
  now); the river/boat area (@dam-base) and Atlantis (@reservoir-north north).
- **Testing nuance:** a bare `(go)` doesn't advance the event clock for a
  same-turn `(queued?)` check the way `(wait)` does — assert event dequeue after a
  following `(wait)` (matches the LH freezing tests). Worth verifying whether the
  harness should process events on movement turns too.

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
