# filfre - Scene Illustration

Named after the Enchanter spell that creates gratuitous fireworks, `filfre` generates
illustrations for interactive fiction via the NanoBanana (Google Gemini 2.5 Flash
Image) cloud backend. Requires a `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) environment
variable.

`filfre` is a standalone tool, not integrated with gnusto at runtime. Use it to
generate images for game assets.

> For how illustrations fit into the game (the static pre-generation pipeline and
> the stage-vs-subject model), see [`docs/render.md`](render.md). `filfre` is the
> generation backend that pipeline drives. The manifest-driven `brief` / `fill`
> subcommands consume the keyset enumerated by `frotz render` (see
> [`docs/frotz.md`](frotz.md)).

## Commands

### `filfre brief` - Per-Key Generation Briefs

Turn a game's render manifest into one brief per asset key — the same keyset a
frontier model would fill, but packaged so a **human artist** can fill it instead.
Each brief is the world `:visual-style` preamble (specialized for the entity's
kind via `:kinds`) followed by the entity's `:rdesc`.

```bash
# Print every brief (full composed prompt per key, style specialized by kind)
filfre brief games/lurkinghorror

# Write one <key>.txt per asset into a directory, ready to hand to an artist
filfre brief games/lurkinghorror --out briefs/

# Limit to specific keys
filfre brief games/lurkinghorror --key microwave-open --key kitchen
```

| Option | Description |
|--------|-------------|
| `game` | Path to the game directory (or `.grue` file) |
| `--out DIR` | Write one `<key>.txt` brief per asset into `DIR` (full assembled prompt) |
| `--key KEY` | Limit to specific asset key(s); repeatable |

### `filfre fill` - Generate Keyed Assets

Generate the game's keyed assets from its render manifest via NanoBanana, writing
`assets/<key>.jpg`. By default only keys **missing on disk** are generated, so it
is safe to re-run as you add entities; `--force` regenerates existing keys.

```bash
# Generate only the assets missing on disk
filfre fill games/lurkinghorror

# Preview the prompts without calling the model
filfre fill games/lurkinghorror --dry-run

# Regenerate one key
filfre fill games/lurkinghorror --key microwave-open --force
```

| Option | Description |
|--------|-------------|
| `game` | Path to the game directory (or `.grue` file) |
| `--key KEY` | Limit to specific asset key(s); repeatable |
| `--force` | Regenerate keys even if an asset already exists |
| `--aspect-ratio` | Force one aspect ratio for every key (otherwise resolved per entity kind from `:visual-style` / `:kinds` — e.g. rooms `2:1`, objects `1:1`) |
| `--seed` | Random seed (default: 0) |
| `--dry-run` | List what would be generated, with prompts, without calling the model |

Output is always normalized to **RGB JPG** (no alpha — composition is the UI
layer's job). The single-subject discipline (rooms as empty stages, objects as
single subjects) is carried by the `:rdesc` briefs themselves; see
[`docs/render.md`](render.md). Run `frotz render <game>` first to lint the specs
and check coverage.

### `filfre generate` - Direct Image Generation

Generate an image from a text prompt with optional reference images:

```bash
# Simple generation
filfre generate --prompt "A brass lantern on a stone altar" -o lantern.png

# With reference image for consistency
filfre generate --prompt "A troll under a bridge" -r troll-ref.png -o troll-scene.png

# Multi-reference composition
filfre generate --prompt "A young man at desk showing his keyring" \
    -r hacker.png -r desk.png -r keyring.png -o composed.png
```

## Generate Options

| Option | Description |
|--------|-------------|
| `--prompt`, `-p` | Text description of the image to generate |
| `--reference`, `-r` | Reference image(s) for composition (can use multiple) |
| `--output`, `-o` | Output file path (default: output.png) |
| `--aspect-ratio` | Output aspect ratio (default: 1:1) |
| `--seed` | Random seed for reproducibility (default: 0) |
| `--count`, `-n` | Number of images to generate (default: 1) |

## Implementation Notes

Previous work on hierarchical scene composition (dynamic rendering integrated with
gnusto at runtime) was retired. That code is archived for reference in
[`experiments/dynamic-composition/`](../experiments/dynamic-composition/) (with a
`README.md` post-mortem). The current direction — static pre-generation with
single-subject images composed by the UI layer — is described in
[`docs/render.md`](render.md).
