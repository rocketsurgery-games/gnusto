# The Lurking Horror — Grue conversion

A conversion of Infocom's _The Lurking Horror_ to Grue, running in the Gnusto
runtime. This is the **canonical reference conversion** — mirror its style when
converting other Infocom games.

# Structure

`./lurkinghorror.grue` is the entrypoint, defining the world and player objects.
The rest of the files are organized by room (e.g. `./terminal-room.grue`),
object (`./pc.grue`), and character (`./hacker.grue`). Most non-trivial objects
have unit tests (`./terminal-room.test.grue`) validating their behavior, plus a
full end-to-end `./walkthrough.test.grue`.

ZIL source is under `./source/*.zil`; the walkthrough prose is
`./source/walkthrough.md`.

# Running the Original

The original compiled game is `./source/lurkinghorror.dat`:

```bash
dfrotz games/lurkinghorror/source/lurkinghorror.dat   # play the original
```

Use it to observe real interaction flows (multi-step sequences, required
preconditions, exact rejection messages) that aren't obvious from the ZIL.

# Converting ZIL → Grue

The **general** ZIL→Grue conversion knowledge — the ZIL-flag → Grue-property
reference, the common property patterns, the event-queue (`CLOCKER`) contract,
the output vocabulary, truthiness, and the recurring pitfalls (verb-level state
machines, `INIT-*` reset routines, objects in limbo / `LOCAL-GLOBALS`, physical
parts vs conceptual contents, direction-ambiguous two-object actions) — now
lives in the **`translate-zil` skill** (`.agents/skills/translate-zil/`,
including `zil-flags.md`). That's the source of truth; consult it first.

## LH-specific notes worth remembering

- **The PC login mini-game** (`pc.grue`) is the canonical example of a ZIL
  verb-level state machine (`V-TYPE`/`V-LOGIN`/`V-PASSWORD` + `LOGGED-IN?`)
  converted to object behaviors that branch on `@pc` properties.
- **Screen elements** (`@menu-box`, `@more-box`, `@yak-window`, `@odd-paper`)
  start in limbo (`:location nil`) and move in/out of `@pc`; the PC's physical
  parts (`@mouse`, `@help-key`) are `:nodesc` and always present.
- **Timed cutscenes** (`compulsion`, `hacker-helps`, `yuggoth-advance`,
  `professor-ritual`, the endgame `frob-appears`) use the one-shot chain idiom;
  the endgame throw is a one-turn window (`frob :count 2`).
- Keep both suites green (`grue-test games/lurkinghorror/`, `pytest`) and the
  game **`frotz lint`-clean**.
