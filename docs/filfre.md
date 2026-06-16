# filfre - Scene Illustration

Named after the Enchanter spell that creates gratuitous fireworks, `filfre` generates
illustrations for interactive fiction via the NanoBanana (Google Gemini 2.5 Flash
Image) cloud backend. Requires a `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) environment
variable.

`filfre` is a standalone tool, not integrated with gnusto at runtime. Use it to
generate images for game assets.

> For how illustrations fit into the game (the static pre-generation pipeline and
> the stage-vs-subject model), see [`docs/render.md`](render.md). `filfre` is the
> generation backend that pipeline drives; the manifest-driven `brief`/`fill`
> subcommands are not built yet (`gnusto-eaec.4`).

## Commands

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
