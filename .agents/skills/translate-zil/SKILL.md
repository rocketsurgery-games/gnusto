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
2. Translate the ZIL routine/file into Grue rooms/objects/behaviors/events.
3. **Remove the ported ZIL comments once the code is fully implemented** — do
   not leave translated ZIL lingering as comments.
4. **Add Grue tests as you go** (`*.test.grue`; see the `grue-testing` skill).
5. **File bugs found in *already-converted* code as P1 yaks** so they're fixed
   before continuing the conversion.
6. If you spot a language construct that isn't general, or that an experienced
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
  :exits ((north :to @bar :via @door))
  :behaviors (:on-enter (fn (?from) ...) :before-action (fn (?verb ?target) ...)))

(object @thing :location @foo :description "thing"
  :properties (:takeable true)
  :behaviors (:examine (fn () '((focus @thing "...") (success)))))

(event my-event :location @foo :on-turn <cond/condp>)   ; maps to a ZIL I-* interrupt
```

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
bug (it will fire once instead of chaining). See `docs/grue.md`.

## Truthiness gotcha (ZIL 0 is true; Grue 0 is currently false)

In ZIL/MDL only `<>` is false — `0` is truthy, which is why ZIL uses explicit
`<ZERO?>` / `<G? x 0>` everywhere. Grue currently leaks Python truthiness, so
`0`, `""`, `[]`, `{}` are **falsy**. When a value can legitimately be `0` (a
floor number, a counter, an index), never test it with raw truthiness:

- ZIL `<COND (<GET ...> ...)>` on a numeric → Grue `(if (not (nil? x)) ...)` or
  an explicit compare, **not** `(if x ...)`.
- Beware `(and ?floor ...)` when `?floor` can be `0` — this caused a real
  basement bug. Use `(nil? x)` / `(empty? x)` / `(= x 0)` as appropriate.

(This asymmetry is tracked for a possible language fix in yak `gnusto-be0a`.)

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
