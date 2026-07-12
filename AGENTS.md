# Development Philosophy

This is a single-developer research project. There are no other users of this code.
Always prefer hard cutovers to backward-compatible migrations - just change things directly.


# CLI Tools

The project provides several CLI commands (installed via `pip install -e .`):

## gnusto - Play Games

Play a Grue game with an LLM-powered natural language agent:

```bash
gnusto games/lurkinghorror/            # Play a game
gnusto games/lurkinghorror/ --debug    # Show agent tool calls
```

## grue-test - Run Tests

Run Grue-native tests for game validation:

```bash
grue-test games/testgame/              # Test a game
grue-test games/lurkinghorror/ -v      # Verbose output
grue-test . -q                         # Quiet, summary only
```

## grue-repl - Interactive REPL

Interactive REPL for exploring Grue games directly (without LLM):

```bash
grue-repl games/testgame/
```

## frotz - Design Tools

Static analysis tools for game design validation. See `docs/frotz.md` for detailed documentation.

```bash
# Check if a state is reachable
frotz reach --to "@key@player" games/testgame
frotz reach --to "(= (:location @player) @lair)" games/lurkinghorror

# Generate DOT graph of reachability
frotz reach --to "@key@player" games/testgame --dot reach.dot

# Full state space analysis with victory path
frotz analyze games/testgame --walkthrough
frotz analyze games/testgame --fast --dot states.dot
```

**State specification syntax:**

| Format | Meaning |
|--------|---------|
| `@obj@room` | `(= (:location @obj) @room)` |
| `@obj@player` | Object held by player |
| `@obj:prop=value` | `(= (:prop @obj) value)` |

## zilch - ZIL Converter

Convert ZIL source code to Grue format (ZIL-changer):

```bash
zilch path/to/zil-game/ -d output/   # Multi-file output
zilch path/to/zil-game/ --stdout     # Print to stdout
```

## filfre - Scene Generation

Generate illustrations using the NanoBanana (Google Gemini 2.5 Flash Image) cloud
backend. Named after the Enchanter spell that creates gratuitous fireworks. See
`docs/render.md` for the pipeline/visual-style design and `docs/filfre.md` for the CLI.

```bash
# Direct image generation (requires GEMINI_API_KEY)
filfre generate --prompt "A troll under a bridge" --output troll.png
filfre generate --prompt "A scene" -r lantern.png -r table.png -o scene.png
```


# Skills

Project-local skills live in `.agents/skills/<name>/SKILL.md`. Reach for them by name:

- **`translate-zil`** — converting ZIL/MDL source to Grue (vocabulary, event-queue contract, truthiness gotchas).
- **`grue-testing`** — how to test games: `grue-test` vs `pytest` vs `grue-repl`, multi-turn `(until ...)` tests, event-lifecycle assertions, and manual TUI/REPL probing.


# Converting ZIL to Grue

When converting ZIL source to Grue, make sure to remove the converted ZIL comments (once fully implemented) as you go. Make sure to add Grue tests as you go. When discovering bugs in *already converted* code, make their yaks P1, so we fix them before moving on to the rest of the conversion.

See the `translate-zil` skill for the full mapping (ZIL-flag → property reference, output vocabulary, and conversion pitfalls). Three hard-won gotchas worth repeating here:

- **Event queue is ZIL-`CLOCKER`-faithful.** `(queue X N)` with a finite `N` is a **one-shot** that auto-dequeues when it fires; to keep firing, the `:on-turn` body must re-queue itself (the chain idiom, e.g. `(queue X 1)`). `(queue X)` / `nil` / negative is **indefinite** (fires every turn until `(dequeue X)`). See `docs/grue.md`.
- **Truthiness is LISP/Clojure-faithful:** only `nil` and `false` are falsy; `0`, `""`, `[]`, `{}` are all **truthy** (like ZIL's `<>`-only-false). So `(and ?floor ...)` is safe when `?floor` is `0`. To test emptiness/zero use `(empty? x)` / `(= n 0)` / `(nil? x)`, not raw truthiness. See `docs/grue.md`. Also note `and`/`or` return the **deciding operand's value** (Clojure-faithful), not a coerced bool: `(or x default)` and `(and a b)` are value-select idioms. `(not ...)` stays a strict bool.

- **Declare every property you touch.** Grue is strict: reading or writing an undeclared property raises at runtime, but only on the path that executes — so a stray write in a cold branch passes the tests and crashes only in real play. Run **`frotz lint <game>`** to catch undeclared-property writes (and dropped event chains) statically, and treat an `error` outcome as a bug to fix (never `blocked`). Engine errors are atomic (roll back) and fail tests loudly.

Generalized ZIL→Grue lessons now live in the **`translate-zil` skill** (the source of truth). The Lurking Horror is the canonical reference conversion; its `README.md` keeps only LH-specific notes.


# The Grue Language

Remember that we're building a language in the spirit of LISP/Scheme/Clojure, so use those idioms to add language
features that support Interactive Fiction development.

**Standard library:** Add Scheme/Clojure stdlib functions as needed (e.g., `str`, `nth`, `first`, `rest`). Default to
Clojure style, but fall back to Scheme/Racket when Clojure depends on syntax we don't have (like `[vectors]`).
No need to ask permission for obvious stdlib additions.

**Purity:** Keep functions pure. All side-effects must go through the formal effects system (quoted effect lists).
This enables future state-space exploration for winnability analysis.

**LLM interface:** The game will be played via an LLM, so prefer explicit formal action interfaces like
`(do @hacker :ask @master-key)` over fiddly parser-dependent constructs. Don't rely on adjectives or other
parser-level distinctions.

IMPORTANT: As you convert to Grue, always look for opportunities to improve the language design for flexibility and expressiveness. If you see such an opportunity, or any language construct that isn't generalized, or doesn't behave as an experienced Scheme/Clojure developer might expect, stop and initiate a discussion with the user.

Always track language & runtime improvements and fixes as yaks (label them `lang` / `runtime`) so design decisions and their rationale are captured.

**Documentation:** When adding new language features, entity fields, or changing behavior, update the relevant docs:
- `docs/grue.md` - Language reference (syntax, semantics, entity fields)
- `docs/filfre.md` - Scene rendering and illustration
- `docs/frotz.md` - Static analysis tools
- `docs/gnusto.md` - Game runtime and LLM interface


## Task tracking

This project uses Yaks to track its own work. Every piece of work must be bracketed: shave a yak before coding, shear it right after committing. Follow the **`yak`** skill for the full workflow.

