# filfre - Scene Illustration

Named after the Enchanter spell that creates gratuitous fireworks, `filfre` generates
illustrations for interactive fiction using FLUX.2 Klein 4B.

`filfre` is a standalone tool, not integrated with gnusto at runtime. Use it to
generate and manage images for game assets.

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

### `filfre list` - List Renders

List frozen and cached renders for a game:

```bash
filfre list games/lurkinghorror
```

### `filfre log` - Show Render Log

View the render log showing recent generations:

```bash
filfre log games/lurkinghorror
filfre log games/lurkinghorror -n 50  # Show last 50 entries
```

### `filfre clear` - Clear Cache

Clear the render cache (preserves frozen renders):

```bash
filfre clear games/lurkinghorror
filfre clear games/lurkinghorror -y  # Skip confirmation
```

## Generate Options

| Option | Description |
|--------|-------------|
| `--prompt`, `-p` | Text description of the image to generate |
| `--reference`, `-r` | Reference image(s) for composition (can use multiple) |
| `--output`, `-o` | Output file path (default: output.png) |
| `--width` | Image width (default: 512) |
| `--height` | Image height (default: 512) |
| `--ref-size` | Resize references to this dimension (default: 256) |
| `--steps` | Inference steps (default: 4) |
| `--guidance` | Guidance scale (default: 2.0) |
| `--seed` | Random seed for reproducibility (default: 0) |
| `--dtype` | Weight dtype: bf16, fp16, or fp32 (default: bf16) |
| `-v`, `--verbose` | Print detailed timing information |

## Performance

On NVIDIA GB10 (Grace Hopper) with CUDA 13:
- Model load: ~5-6s (with mmap clone optimization)
- Generation: ~3-4s for 512x512 at 4 steps
- VRAM: ~15 GB allocated, ~15.5 GB peak

## Implementation Notes

Previous work on hierarchical scene composition (dynamic rendering integrated with
gnusto at runtime) is documented in `src/filfre/IMPLEMENTATION-NOTES.md`. The
`scene_renderer.py` and `render_cache.py` modules in filfre preserve that code
for future reference.
