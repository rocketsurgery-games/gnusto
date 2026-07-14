---
name: translate-zil
description: Translate Infocom ZIL/MDL source into Grue (rooms, objects, behaviors, events). Use when converting a ZIL routine, file, or game to Grue — covers the verb/predicate mapping, the engine-authoritative output vocabulary, the event-queue contract, and the truthiness gotchas that bite ZIL conversions.
---

# ZIL → Grue translation

You are translating Infocom's ZIL (a compiled MDL dialect) into Grue, a
Lisp/Scheme/Clojure-style DSL for interactive fiction. Produce Grue that
replicates the game logic faithfully, using current Grue idioms.

The Lurking Horror (`games/lurkinghorror/`) is the canonical reference
conversion — mirror its style. ZIL source lives under
`games/lurkinghorror/source/*.zil`; keep conversion notes in
`games/lurkinghorror/README.md`.

## Workflow (non-negotiable)

1. **Shave a yak before writing code** (see the `yak` skill).
2. **Bootstrap with `zilch`** if starting a game fresh: `zilch games/<game>/source -d games/<game>/converted` scaffolds `converted/*.grue` (with the ZIL preserved as comments). Hand-translate from there into clean root `.grue` files; never edit `converted/` for behavior. (See `games/notes.md`.)
3. Translate the ZIL routine/file into Grue rooms/objects/behaviors/events.
4. **Remove the ported ZIL comments once the code is fully implemented** — do
   not leave translated ZIL lingering as comments.
5. **Add Grue tests as you go** (`*.test.grue`; see the `grue-testing` skill).
6. **Run `frotz lint <game>` and keep both suites green** (`grue-test`, `pytest`)
   before moving on — the lint catches undeclared-property writes and dropped
   event chains in cold paths the tests never hit.
7. **File bugs found in *already-converted* code as P1 yaks** so they're fixed
   before continuing the conversion.
8. If you spot a language construct that isn't general, or that an experienced
   Scheme/Clojure dev wouldn't expect, **stop and discuss with the user**; track
   language/runtime work as `lang`/`runtime` yaks.

## ZIL quick reference

MDL/ZIL is a Lisp dialect. The false value is the FALSE object `<>`; **every
other value — including `0`, empty strings, and objects — is TRUE.**

**Predicates:** `<VERB? OPEN CLOSE>` (current verb), `<PRSO? OBJ>` /
`<PRSI? OBJ>` (direct/indirect object), `<HERE? ROOM>`, `<FSET? ,OBJ ,FLAG>`,
`<IN? ,OBJ ,CONT>`, `<EQUAL? A B C>`, `<ZERO? X>`, `<G? A B>`, `<L? A B>`.

**State:** `<FSET ,OBJ ,FLAG>` / `<FCLEAR ,OBJ ,FLAG>` (flags),
`<MOVE ,OBJ ,DEST>`, `<SETG VAR VAL>` (global), `<PUTP>`/`<GETP>` (properties).

**Output/flow:** `<TELL "..." CR>` (print), `<RTRUE>`/`<RFALSE>` (handled or not),
`<DO-WALK ,P?DIR>` (move player), `<QUEUE I-RTN N>` / `<DEQUEUE I-RTN>` (events).

## Grue targets

### Behaviors — outcomes

```grue
:behaviors (
  :verb (cond
    (CONDITION (blocked :reason REASON-SYMBOL :message "why it failed"))
    (CONDITION '((effect1) (effect2) (success)))
    (CONDITION (redirect :action (do @other :verb)))
    (true (default))))          ; fall back to engine default handling
```

- `(blocked :reason SYM :message "...")` — the action is refused. Map each
  refusing `<TELL>` here. Keep `(blocked ...)` handlers verbatim from ZIL intent.
- `(redirect :action (do @x :v))` / `(redirect :to @room)` — dispatch elsewhere
  (e.g. ZIL `THROUGH` on a door → redirect to movement).
- `(default)` — let the engine's stdlib handler run.
- `?self` is the entity; action args are bound like `?with` / arguments passed
  via `(do @a :verb @b)`.

### Output vocabulary — emit the real text (engine-authoritative)

**Critical, and the opposite of the old guidance:** the game engine is the
author of record. Convert each `<TELL>` into a concrete output effect carrying
the *actual game text* (strip the outer quotes). Do **not** "capture the why" or
defer prose to the LLM.

| ZIL intent | Grue effect |
|-----------|-------------|
| Narrator/room prose, event beats | `(narrate "...")` |
| NPC speech (`<TELL "\"...\"">`) | `(say @npc "...")` (no surrounding quotes) |
| Examining an object | `(focus @obj "...")` |
| Revealing/uncovering something | `(reveal @obj "...")` |
| Climax / dramatic emphasis | `(emphasize "...")` |
| Full-bleed dramatic beat | `(splash "...")` |
| Onomatopoeia / sound lettering | `(sfx "...")` |

Structural descriptions stay structural: room `:describe` and object
`:describe` return `(success :context ((description "...")))`; object
`:examine` uses `(focus ...)`.

When the text is built from bindings or `(str ...)`, use quasiquote/unquote:
`` `((narrate ,(str "You have " ?n " coins.")) (success)) ``.

### Rooms, objects, events

```grue
(room @foo :description "Name" :ldesc "Long desc..."
  :exits ((north :to @bar :via @door)
          (west :blocked "Storm-tossed trees block your way."))  ; ZIL string exit
  :behaviors (:on-enter (fn (?from) ...) :before-action (fn (?verb ?target) ...)))

(object @thing :location @foo :description "thing"
  :properties (:takeable true)
  :behaviors (:examine (fn () '((focus @thing "...") (success)))))

(event my-event :location @foo :on-turn <cond/condp>)   ; maps to a ZIL I-* interrupt
```

### Flags & properties

ZIL `FLAGS` become `:properties`. The full ZIL-flag → Grue-property table and
the common property combinations live in **`zil-flags.md`** (in this skill dir) —
consult it when converting an object. Two rules that bite:

- **Declare every property you touch.** Grue is strict: reading or writing a
  property the entity doesn't declare in `:properties` raises at runtime. If an
  event/behavior does `(set @x :foo ...)`, `@x` must declare `:foo` (with a
  default). A stray write in a *cold* branch passes the tests and only crashes
  in real play — **`frotz lint <game>` catches these statically** (see
  `docs/frotz.md`). Fix by declaring the property or deleting the stray write.
- **Drop parser vocab** (`SYNONYM`/`ADJECTIVE`/article flags): the LLM resolves
  names and the formal `(do @x :verb @arg)` interface needs no adjectives.

## Event queue — ZIL `CLOCKER`-faithful (read this)

Grue's queue matches ZIL's `CLOCKER` (see `source/misc.zil`) exactly:

- **`(queue X N)` with finite `N ≥ 1` is a ONE-SHOT.** It counts down and fires
  once (N=1 fires this turn), then **auto-dequeues**. To keep firing, the
  `:on-turn` body must **re-queue itself** — the chain idiom, mirroring ZIL's
  `<QUEUE I-X 1>` at the end of the routine.
- **`(queue X)` / `nil` / negative is INDEFINITE** (ZIL `-1`): fires every turn,
  never auto-removed; the body must `(dequeue X)` to stop.

So when ZIL does `<QUEUE I-X 2>` then re-queues with `<QUEUE I-X 1>` each turn,
the Grue event **must** include `(queue X 1)` in its advancing branches. A
finite-countdown event that neither re-queues nor dequeues is almost always a
bug (it will fire once instead of chaining). See `docs/grue.md`. Run
**`frotz lint <game>`** after converting an event with a `(condp = (:counter ...))`
state machine — it flags exactly this dropped-chain mistake.

## Light, darkness, and environmental hazards

Darkness is engine-supported and **opt-in**. A room's `:lit` defaults to true, so
declare `:lit false` (ZIL rooms lacking `ONBIT`) to make a room dark; it relights
if the player carries/【has present】a `:lightable` object switched `:lit true`
(ZIL `LIGHTBIT`, e.g. the brass lantern). The engine's `(lit? ROOM)` predicate
(`builtins.grue`) drives perception: in an unlit room the description becomes the
world `:dark-message` and objects aren't listed. See `docs/grue.md`.

The *danger* of the dark (ZIL's random grue death) is **game code**, written as a
normal turn-based **hazard event** — the same shape as LH's `freezing`: reset a
counter when safe, tick it while in the hazard, deliver a deterministic death
once a configurable grace is spent (see "Randomness → determinism" below for why
the RNG goes). Queue a persistent hazard from turn 1 with the world's
`:start-events (evt …)`. ZIL's other environmental death timers (freezing,
drowning, suffocation) convert to the same pattern.

## Randomness → determinism (drop the RNG)

Infocom games lean on `<RANDOM>` everywhere, and **we strip or replace all of it**
so the world stays statically analyzable — RNG makes frotz's state space unsound
to explore (`reach`/`deadends`/winnability). This is one of the most pervasive
conversion decisions; it touches nearly every game. Where you'll find it:

- **Combat** — ZIL melee is `MELEE` result tables indexed by a `<RANDOM>`/`PROB`
  roll (hit/miss, wound, knock-out, flee, kill). Convert a fight to a
  **deterministic strength-countdown duel**: the monster carries `:strength N`,
  each *armed* blow decrements it, at `0` it dies (drops its weapon, frees its
  guarded treasure). Bare-handed or already-dead cases become fixed `(blocked
  …)` refusals. This is the troll, thief, and cyclops pattern in `games/zork1`.
- **NPC wandering / theft** — the thief's `I-THIEF` moves him and snatches loot
  at random. Reduce to a **stationary or scripted** encounter, with theft
  triggered by *state* (not probability). State-triggered flavor (e.g. giving
  him a treasure `:engrossed`s him so blows land harder) preserves the puzzle.
- **Environmental death timers** — the grue, freezing, drowning: a **grace
  counter then certain death**, not a per-turn roll (see the hazard section).
- **Fixed counts for `<RANDOM n>` quantities** — dig counts, number of blows,
  etc. become a constant.

Always leave a conversion comment at the top of the file noting the original
random behavior and the deterministic substitution (see `games/zork1/thief.grue`
for the template). The open design question — how to reintroduce *bounded,
analyzable* variety (scripted patrols, seeded/enumerable RNG, a first-class
hazard construct) without breaking analysis — is tracked in **`gnusto-6b4f`**
(and `gnusto-5818` for the `defhazard` idea); don't revive `<RANDOM>` to solve it.

## Death, victory, and JIGS-UP (end-state handling)

Signal an end-state from game code with a **result-context flag**; the engine
records it on the player. A `(death true)` context sets `@player :dead`
(`_check_death_context`); a `(victory true)` context sets `@player :won`
(`_check_victory_context`). A hazard/death emits `(blocked :context ((death
true) (description "…")))`; a win emits `(success :context ((victory true)))`
(e.g. a sentinel end-room's `:on-enter`). Keep the declarative `(victory :when
…)` world clause too — it's the analyzable mirror frotz reads.

**We deliberately differ from the original on what happens next.** Infocom's
`JIGS-UP` (`gverbs.zil`) *resurrects* the player: it prints the death text, then
a deity voice, scatters the carried objects to random/aboveground spots, drops
the player at a fixed/again-random location, and only ends for good after a
death cap. Our conversions make **death — and victory — terminal**: the harness
prints an out-of-world banner (`*** You have died ***` / `*** You have won ***`)
and refuses further commands until `/reset`. No resurrection, item-scattering,
score penalty, or death counter.

Why: resurrection reintroduces exactly the nondeterminism (random re-placement)
and hidden state (a death counter) we strip elsewhere to keep frotz's
state-space analysis sound, and a clean terminal state is simpler for the LLM
harness. If a game genuinely needs resurrection, model it explicitly and
deterministically as game code — don't revive ZIL's RNG. (harness: gnusto-0bf7.9)

## Truthiness (Grue matches ZIL/Clojure)

In ZIL/MDL only `<>` is false — `0`, strings, and objects are truthy, which is
why ZIL uses explicit `<ZERO?>` / `<G? x 0>` everywhere. **Grue matches this:**
only `nil` and `false` are falsy; `0`/`""`/`[]`/`{}` are truthy. So a ZIL
`<COND (<GET ...> ...)>` on a numeric maps cleanly to `(if (:prop @x) ...)` and
`(and ?floor ...)` works even when `?floor` is `0`. Still prefer explicit
compares (`(= x 0)`, `(> x 0)`) or `(empty? x)` / `(nil? x)` when you mean them.

## Conversion pitfalls (spot these — they generalize across Infocom games)

- **Verb-level state machines.** Some mechanics live in verb routines
  (`ACTION`/`V-*`), not object behaviors — easy to miss when porting object by
  object. Look for `NEW-VERB` redirects and global flags (`FOO?`, `LOGGED-IN?`)
  tracking a multi-step flow. Convert to object behaviors that branch on the
  object's own properties (e.g. `:type` → `(redirect :action (do ?self :login ...))`
  based on `(:username ?self)`).
- **`INIT-*` reset routines.** ZIL `INIT-FOO` routines reset state (power-off,
  close, leave) and are called from several places. Fold their effects into
  *every* relevant behavior (e.g. turning a device off must also clear its
  login/screen state). Search for `INIT-` and trace all call sites.
- **Objects in limbo.** Objects with no `(IN ...)`, or `(IN LOCAL-GLOBALS)` /
  `(IN GLOBAL-OBJECTS)`, don't start in a room. Give them `:location nil` and
  reveal via effects (`(move @x @dest)`), or — for scenery visible from many
  rooms (walls, forest, water) — a room `:visible` entry. See `zil-flags.md`.
- **String/`SORRY` exits → `:blocked`.** ZIL rooms constantly use message-only
  exits — a direction whose only effect is a refusal message, with no room
  behind it: `(WEST "You would need a machete to go further west.")`,
  `(NORTH SORRY "...")`. Map these to a first-class blocked exit
  `(west :blocked "...")` (mutually exclusive with `:to`) — *not* a synthesized
  barrier object. Reserve a `:via` barrier object for boundaries the player can
  actually examine or manipulate (doors, boarded windows). See `docs/grue.md`.
- **Physical parts vs conceptual contents.** `NDESCBIT` objects inside a
  container are usually *part of* it (a PC's mouse/help-key), not transient
  contents. Don't `(first (contents ?self))` blindly — check the specific
  screen/contents object you mean.
- **Two-object actions are direction-ambiguous.** "put X in Y", "throw X at Y",
  "unlock X with Y" — the natural phrasing doesn't tell you which entity is the
  action target. The engine's **default `put` and `throw` are bidirectional**
  (`(do @item :put @container)` == `(do @container :put @item)`; `throw` at a
  target redirects to `attack`). For a *custom* two-object verb, don't rely on
  target/arg order the LLM can't guess — accept both, or `(redirect ...)` to a
  canonical form. (yaks gnusto-1ce1 / gnusto-7f83)
- **Test against the original.** Run the compiled game
  (`dfrotz games/<game>/source/<game>.dat` or `frotz …`) to observe real
  interaction flows — multi-step sequences, required preconditions, state
  dependencies, and exact rejection messages that aren't obvious from the ZIL.

## Example

ZIL:
```zil
<ROUTINE SIMPLE-DOOR-F ()
  <COND (<VERB? OPEN>
         <COND (<FSET? ,SIMPLE-DOOR ,LOCKED> <TELL "It's locked." CR>)
               (T <FSET ,SIMPLE-DOOR ,OPENBIT> <TELL "The door creaks open." CR>)>)>>
```

Grue:
```grue
:behaviors (
  :open (cond
    ((:locked ?self)
      (blocked :reason locked :message "It's locked."))
    (true
      '((set ?self :open true) (narrate "The door creaks open.") (success)))))
```
