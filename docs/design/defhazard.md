# `defhazard` — a hazard-event macro, and how it should drive the macro system

Status: **design note / deferred** (yak `gnusto-5818`, depends on the macro
system `gnusto-2q9`). Written while converting Zork I, after hand-rolling the
same hazard three times. Come back to this after the conversion.

This note captures (a) the recurring pattern, (b) a proposed `defhazard` surface
and expansion, and — most importantly — (c) the concrete requirements it places
on the general macro system, so that implementing `gnusto-2q9` is driven by a
real, cross-game use case rather than only the `->` / `->>` threading macros it
currently cites.

## The pattern

An **environmental hazard** is a turn-based event that, each turn:

1. checks an "unsafe?" condition on some actor's situation,
2. **resets** a counter to 0 when the actor is safe (and stops, if triggered),
3. **ticks** the counter (optionally emitting an escalating message) while unsafe,
4. delivers a **deterministic death** once the counter passes a configurable grace.

Determinism (no RNG) is deliberate: it keeps `frotz` reach/deadends sound. The
grace period is the analyzable stand-in for the original games' random timing.

### The three current instances (the boilerplate we want to remove)

| Hazard | Game | `unsafe?` | counter | grace | rise message |
|--------|------|-----------|---------|-------|--------------|
| `freezing`   | Lurking Horror | player is outside          | `:freeze-count` | ~4 | 5 staged lines |
| `grue-lurks` | Zork I         | player's room is unlit     | `:dark-turns`   | 1 | none |
| `dam-flood`  | Zork I         | player in the flooding room | `:flood-level`  | 4 | one line |

They share one skeleton (abbreviated `grue-lurks`):

```grue
(event grue-lurks
  :on-turn
    (cond
      ((lit? (loc @player))                                  ; safe -> reset
        (cond ((> (:dark-turns @player) 0)
               '((set @player :dark-turns 0) (success)))
              (true (success))))
      ((< (:dark-turns @player) (:grue-grace @player))       ; tick (within grace)
        (let ((?n (+ (:dark-turns @player) 1)))
          `((set @player :dark-turns ,?n) (success))))
      (true                                                  ; grace spent -> death
        (blocked :reason death
                 :context ((death true) (description "... a lurking grue!"))))))
```

Everything but the four cells in the table above is identical ceremony.

## Proposed surface syntax

```grue
(defhazard grue-lurks
  :unsafe?  (not (lit? (loc @player)))   ; predicate; expr, not a passed fn value
  :actor    @player                      ; optional, default @player
  :counter  :dark-turns                  ; counter property on the actor
  :grace    1                            ; turns of unsafe before death
  :rise     nil                          ; per-tick message: nil | "str" | ("l1" "l2" ...)
  :death    "Oh, no! ... a lurking grue!"
  :start    false)                       ; if true, register in world :start-events
```

- `freezing` → `:unsafe? (:outside (loc @player)) :counter :freeze-count :grace 4
  :rise (list of 5 lines)`.
- `dam-flood` → `:unsafe? (= (loc @player) @maintenance-room) :counter :flood-level
  :grace 4 :rise "The water is rising alarmingly." :death "... drowned ..."`.

Staged `:rise` (a list) reproduces `freezing`'s escalating messages by indexing
on the counter; a bare string repeats; `nil` is silent.

## Expansion target

`defhazard` expands, **at load time**, into exactly the hand-written event (plus,
optionally, a `:start-events` registration). It does **not** silently declare the
counter property — the author still writes `:counter-prop 0` on the actor, so the
undeclared-property lint and the reader both see it (keep state visible). The
macro may *warn* if the counter isn't declared.

## Requirements this places on the macro system (`gnusto-2q9`)

This is the part that should shape the implementation. `defhazard` is a
**definitional** macro (it emits a top-level `(event …)` form), which is a bigger
ask than the expression-level `->`/`->>`. To support it, the macro system needs:

1. **A macroexpansion pre-pass over top-level forms.** Macros must expand
   *before* the form-dispatcher turns forms into `GrueWorld` entries, and before
   `frotz`/`lint` run. So the pipeline becomes: parse → **macroexpand** →
   form-dispatch / analyze. Crucially, the runtime **and** the analyzers consume
   the *expanded* forms, so a `defhazard` event is linted and explored exactly
   like a hand-written one (dropped-chain lint, undeclared-write lint, reach,
   deadends all "just work"). This preserves analyzability — the reason to prefer
   a macro over a higher-order-function helper (which would hide the hazard's
   effects behind a passed-in predicate and trip `gnusto-zbg`'s "unknown effects"
   problem).

2. **Macros that emit *definitional* forms, not just expressions.** `->` rewrites
   an expression in place; `defhazard` produces a whole `(event …)` declaration
   (and maybe a `(world :start-events …)` contribution). The expander must accept
   a macro whose output is one-or-more top-level forms. Decide: can a macro emit
   **multiple** top-level forms (splice a list of forms)? `defhazard` wants at
   least the event; `:start true` wants a second contribution.

3. **Quasiquote / unquote / unquote-splicing in templates.** The macro body
   builds the event by splicing the caller's `:unsafe?` expression and `:death`
   string into a template. Grue already has `` ` `` / `,` (used in event bodies);
   confirm/implement `,@` (splice) so a staged `:rise` list and multi-form output
   work. Templates are how the macro stays readable.

4. **Keyword-argument destructuring in `defmacro`.** `defhazard` takes keyword
   args. Either `defmacro` supports a keyword/`&key`-style parameter list, or
   `defhazard` receives its args as a form and destructures them (a helper like
   `parse-kwargs` at macro-expansion time). Pick one convention and reuse it for
   future library macros.

5. **Hygiene / `gensym` for introduced bindings.** The expansion introduces a
   temp (`?n` above). If the caller's `:unsafe?` or `:rise` references a variable
   named `?n`, naive expansion captures it. Provide `gensym` (or true hygiene) so
   introduced temporaries can't collide with caller code. Minimal but real.

6. **Where library macros live + load order.** `defhazard` itself is a library
   macro (in `builtins.grue` or a new `macros.grue`) that must be *defined and
   expanded before* any game file that uses it is form-dispatched. Decide the
   load/expansion ordering (builtins' macros available to all games, expanded in
   a single pre-pass across the loaded fileset).

### What this buys `gnusto-2q9`

The threading macros are a thin motivation (they're expression rewrites and
already work as special forms). `defhazard` forces the macro system to be
*genuinely useful*: top-level definitional expansion, multi-form output,
quasiquote-splice templates, keyword args, and `gensym` — i.e. a real Lisp macro
system, not just `defmacro` sugar over `->`. Building to satisfy `defhazard`
lands the system in the right place.

## Sequencing when we return

1. Implement the macro system (`gnusto-2q9`): `defmacro`, a top-level
   macroexpand pre-pass feeding both runtime and analyzers, quasiquote + `,@`,
   keyword-arg macros, `gensym`.
2. Add `defhazard` as the first library macro (validates the system against a
   concrete, cross-game need).
3. Retrofit `freezing`, `grue-lurks`, and `dam-flood` onto `defhazard` as the
   regression proof: identical behavior, unchanged tests, `frotz lint` still
   clean, and the expanded events indistinguishable from today's hand-written
   ones.

## Open questions

- **Auto-queue vs explicit:** `grue-lurks` is a `:start-events` hazard; `freezing`
  and `dam-flood` are queued by a triggering behavior. Keep `:start` optional and
  leave triggered hazards to `(queue …)` in the triggering behavior.
- **Reset semantics:** all three reset-to-0 when safe; keep that (no decay).
- **Counter declaration:** macro warns but doesn't auto-declare the counter
  property (keep state visible for the lint/reader) — confirm.
- **`:rise` staging:** index a list by the counter (like `freezing`), repeat a
  string, or stay silent on `nil` — support all three.
