# Development Philosophy

This is a single-developer research project. There are no other users of this code.
Always prefer hard cutovers to backward-compatible migrations - just change things directly.


# Issue Tracking

This project uses **bd** (beads) for issue tracking.

```bash
bd ready                              # Find available work
bd show <id>                          # View issue details
bd create --title="..." --type=task   # Create new issue
bd update <id> --status=in_progress   # Claim work
bd close <id>                         # Mark complete
bd sync                               # Sync with git remote
```

Do NOT start work on a bead without claiming it.


# CLI Tools

The project provides several CLI commands (installed via `pip install -e .`):

## gnusto - Play Games

Play a Grue game with an LLM-powered natural language agent:

```bash
gnusto games/lurkinghorror/            # Simple REPL mode
gnusto games/lurkinghorror/ --tui      # Fullscreen TUI
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

Generate illustrations using OmniGen2. Named after the Enchanter spell that
creates gratuitous fireworks:

```bash
filfre --scene white_house --output scene.png
filfre --scene custom --prompt "A troll under a bridge" --output troll.png
filfre --list-scenes
filfre --scene white_house --taylorseer --cfg-range-end 0.7  # 2.2x faster
```

**Hardware notes:**
- **CUDA GPU (17GB+ VRAM)**: Full speed with `--dtype bf16`
- **NVIDIA GB10**: Works with CUDA. Requires uninstalling triton (CLI provides instructions)
- **CPU**: Works but slow (~28s/step). Uses float32 automatically


# Converting ZIL to Grue

When converting ZIL source to Grue, make sure to remove the converted ZIL comments (once fully implemented) as you go. Make sure to add Grue tests as you go. When discovering bugs in *already converted* code, make their beads P1, so we fix them before moving on to the rest of the conversion.

As we work through converting The Lurking Horror as a starting point, we're keeping notes on what we learn in
./games/lurkinghorror/README.md.


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

We're keeping the bead "Language & runtime design tweaks" (frotzlm-ntr) around to capture language changes as we go. Always track language & runtime improvements & fixes in this epic.


# Session Completion Workflow

When ending a work session, complete ALL steps. Work is NOT complete until `git push` succeeds.

1. **File issues** for remaining work
2. **Run quality gates** if code changed (tests, linters, builds)
3. **Update issue status** - close finished work, update in-progress items
4. **Push to remote** (MANDATORY):
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # Must show "up to date with origin"
   ```
5. **Verify** all changes committed AND pushed
6. **Hand off** - provide context for next session

**Rules:**
- Work is NOT complete until `git push` succeeds
- Never stop before pushing - that leaves work stranded locally
- If push fails, resolve and retry until it succeeds
