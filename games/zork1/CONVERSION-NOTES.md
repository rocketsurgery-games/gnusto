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

## Friction / tooling observations

- **Test DSL vs REPL `go` syntax diverge.** Tests use `(go :direction east)`;
  the REPL wants `(go east)`. `(go :direction east)` in the REPL is parsed as a
  literal direction `:direction` and returns `no-exit`. Minor, but a footgun for
  manual probing. Candidate: accept both in both places.
- **Blocked messages assert via `(context? message "...")`, not `(output?
  ...)`.** `blocked :message` lands in terminator context, while `output?` only
  scans the narrate/focus/say output stream. `context?` is an *exact* match (no
  substring). Worth an explicit line in the `grue-testing` skill.

## Open language-design question (raised with user)

- **Message-only exits.** ZIL rooms very frequently use string-exits like
  `(EAST "The rank undergrowth prevents eastward movement.")` — a blocked
  direction whose only effect is a custom message, with *no* associated object.
  Zork's forest/mountain/house rooms are full of these. Grue currently has no
  first-class form; you must synthesize an invisible `:via` barrier object per
  message. That's heavy boilerplate when there's no real object behind it.
  Proposed: a first-class blocked-exit form, e.g.
  `(east :blocked "The ... prevents eastward movement.")` (ZIL's `SORRY`/string
  exit). Pending user decision before the forest slice.
