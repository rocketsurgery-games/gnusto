---
name: grue-testing
description: How to test Grue games — choosing between grue-test, pytest, and grue-repl; writing multi-turn (until ...) tests; asserting event lifecycles; and driving the TUI/REPL for manual probing. Use when adding or debugging tests for game logic, especially timed/event-driven mechanics.
---

# Testing Grue games

Pick the right tool, and prefer tests that exercise **multiple turns** and
**event lifecycles** — single-turn assertions from hand-built state are how the
elevator soft-lock slipped past ~30 unit tests (see yak `gnusto-3306`).

## Which harness

| Tool | Use for | Command |
|------|---------|---------|
| **grue-test** | Game logic in the game's own language (`*.test.grue`). First choice for behavior/events. | `grue-test games/lurkinghorror/ -q` |
| **pytest** | Engine/runtime internals, parsing, cross-cutting invariants, Python-level end-to-end. | `python -m pytest tests -q` |
| **grue-repl** | Manual/scripted exploration with **no LLM** (deterministic). Pipe commands in. | `grue-repl games/lurkinghorror/ < script.grue` |
| **gnusto TUI** | Manual play through the real LLM parse→action loop. | `gnusto games/lurkinghorror/ --plain --debug < cmds.txt` |

Both suites must stay green: **`grue-test games/lurkinghorror/`** and
**`python -m pytest tests -q`**.

**Static lint:** run **`frotz lint <game>`** for two checks (see `docs/frotz.md`):
(1) **dropped event chains** — a self-advancing counter event queued only
finitely that forgets to re-queue itself (the `compulsion` bug class); and
(2) **undeclared property writes** — a `set`/`inc`/`dec` to a property the target
never declares, which raises at runtime but only on the path that executes
(the endgame `hacker-returns` bug). Both are asserted clean for LH in pytest, so
a regression fails CI. Lint before you trust a green suite: it catches
cold-path bugs the tests never exercised.

**Engine errors fail loudly.** An action or event that errors (`outcome=error`
— undeclared property, uncaught exception, redirect loop) now **fails the test**
(you'll see `engine error: …`), and its effects **roll back atomically** (no
partial state). `error` is a bug, never an intended outcome — fix it, don't
assert around it; intended refusals are `blocked`, not `error`. (yak gnusto-160b)

## grue-test DSL

```grue
(test-group "name"
  :setup ((move @player @room) (set @obj :prop val) (queue evt 0))  ; run as effects
  (test "does the thing"
    :setup (...)                 ; optional per-test setup, overrides group
    (do @obj :verb)              ; actions: (do @o :verb [@arg]), (go :direction south), (wait)
    (advance 5)                  ; (wait N)/(advance N): pass N turns at once
    (until PRED (wait))          ; loop BODY until PRED is true (max 100 iterations)
    (assert (outcome? success))
    (assert (loc? @player @room))))
```

**Assertion predicates** (`(assert (PRED ...))`):
`outcome?`, `context?`, `output?` (substring of emitted text), `death?`,
`victory?`, `player-at?`, `loc?`, `prop?`, `has-flag?`, `no-flag?`, `not-flag?`,
`queued?`, `not-queued?`, `queue-countdown?` (`(queue-countdown? EVENT N)`;
`N = nil` asserts an indefinite queue).

**Setup effects** run as real mutations: `move`, `set`, `inc`, `queue`,
`dequeue`, `take`. Use them to reconstruct precise state deterministically.

## Multi-turn: use `(until PRED (wait))`, not fixed wait counts

Timed mechanics have fragile turn counts (elevator scan, cook timers, cutscene
delays). Loop with `until` instead of guessing:

```grue
(test "ride the elevator to the basement"
  (do @down-button :push)
  (until (:open @elevator-door-2) (wait))      ; car arrives, doors open
  (go :direction south)                         ; board
  (do @basement-button :push)
  (until (= (:floor @cs-elevator-room) 0) (wait))
  (assert (prop? @cs-elevator-room stopped true))
  (assert (not-queued? elevator-moves)))        ; car idle, not spinning
```

**Gotcha:** the `until` predicate is a *general expression* (evaluated by the
normal evaluator), **not** an assertion predicate. `prop?`/`loc?`/`queued?` only
work inside `(assert ...)`. Inside `until`, use raw forms:
`(= (:floor @x) 0)`, `(:open @door)`, `(queued? evt)` works as a builtin, but
prefer explicit reads.

## Assert event lifecycles

Queue bugs hide unless you check them. Given the ZIL-faithful contract
(one-shot finite countdowns auto-dequeue; `nil`/negative is indefinite — see
`docs/grue.md` and the `translate-zil` skill):

- **One-shot fired → gone:** after the fire turn, `(assert (not-queued? X))`.
  This is the single assertion that would have caught the elevator/compulsion
  bugs directly.
- **Countdown ticks as expected:** `(assert (queue-countdown? X 2))` right after
  queuing, then `(advance 1)` and `(assert (queue-countdown? X 1))`.
- **Chain keeps running:** for an event that re-queues itself, `(assert (queued? X))`
  still holds across turns; assert the per-turn effect advances.
- **Indefinite stops on dequeue:** drive it to its terminal branch, then
  `(assert (not-queued? X))`.

## Manual / semi-automated probing

Deterministic (no LLM), great for isolating a game bug:

```bash
printf '(go south)\n(do @down-button :push)\n(wait)\n(wait)\n' > /tmp/probe.grue
grue-repl games/lurkinghorror/ < /tmp/probe.grue 2>&1 | grep -nE '===|Effect:|EVENT'
```

In the REPL, **`(queues)`** dumps the live event queue with countdowns and
**`(wait N)` / `(advance N)`** passes N turns at once — the fast way to watch a
timed mechanic settle without diving into source.

**Checkpointing:** `(save [slot])` / `(load [slot])` / `(saves)` persist and
restore runtime state (to `~/.gnusto/saves/<game>/`), so you can drive a game to
an interesting state once, save it, and re-load it at the top of later probe
scripts instead of replaying the whole sequence. The same slots are shared with
the LLM CLI's `/save` and `/load`, so you can even hand a REPL-built checkpoint
to a `gnusto` session (and vice-versa).

Through the real LLM loop (parse-only is the default; engine emits the text):

```bash
printf 'go south\ncall the elevator\nget in\npress the basement button\n' > /tmp/cmds.txt
gnusto games/lurkinghorror/ --plain --debug < /tmp/cmds.txt 2>&1
```

`--debug` shows the parsed `(do ...)` actions and the Grue effects per turn.
Clean up any probe files you create.

## Reproduce, then assert

When a manual probe reveals a bug: (1) reproduce it deterministically in
`grue-repl` to confirm it's engine/game (not the LLM), (2) encode it as a
`*.test.grue` (or pytest) regression using `until` + a lifecycle assertion,
(3) fix, (4) confirm both suites green.
