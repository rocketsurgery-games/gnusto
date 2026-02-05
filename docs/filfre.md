# filfre - Scene Illustration

Named after the Enchanter spell that creates gratuitous fireworks, `filfre` generates
illustrations for interactive fiction using FLUX.2 Klein 4B.

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

### `filfre render` - Render Game Entities

Render an entity (room or object) from a game using its render spec.
**Note:** This renders the entity in its initial game state, useful for testing
render specs and pre-caching initial images. For dynamic state rendering during
gameplay, gnusto's built-in scene renderer handles this automatically.

```bash
filfre render games/lurkinghorror @terminal-room
filfre render games/lurkinghorror @brass-lantern
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

---

# Hierarchical Scene Composition (Design)

This section describes the planned system for generating consistent illustrations
across an entire game, from atomic objects to full scene renders.

## Overview

The composition system has three layers:

1. **Atomic**: Base reference images for objects, characters, rooms
   - Hand-drawn or carefully generated
   - Neutral backgrounds/lighting
   - Multiple views if needed for consistency

2. **Composite**: Combinations of atomics
   - PC = tower + monitor + keyboard + mouse
   - Janitor on floor waxer
   - Chinese food in microwave

3. **Scene**: Full runtime composition
   - Room + contained objects + characters
   - Dynamic based on game state (lighting, object positions, etc.)

## Render Specs in Grue

Render specifications live alongside textual descriptions in game definitions.

### Render Spec Elements

A render spec is a list containing:
- **Strings**: Concatenated to form the prompt
- **Object/room refs** (`@foo`): Contribute `:description` to prompt + rendered image as reference
- **Reference refs** (`@ref`): Contribute only rendered image (no text) - caller wraps with text
- **Expressions**: Evaluated with `self` bound to the entity being rendered
- **Keywords**:
  - `:ref "path"` - Static file reference image (path relative to assets dir)
  - `:contents` - Include rendered images of objects at this location
  - `:ref-size N` - Override reference size for this render
  - `:anchor @obj` - Re-include atomic ref to reduce drift
  - `:through @portal @target` - Include target room when portal is open

### References (Named Render Specs)

References are reusable "render bags" - named render specs that contribute only their
image (no text) when used in other render specs. The caller provides descriptive text.

```grue
;; Reference with generated image
(reference @terminal-room-bg
  :render "A large 1980s computer lab with CRT monitors, empty of people")

;; Reference with static image (path relative to assets dir)
(reference @hacker-portrait
  :render (:ref "refs/hacker.jpg"))

;; Room composing references - note how text wraps the reference
(room @terminal-room
  :render ("In the" @terminal-room-bg "with:" :contents))
```

### Objects with Render Specs

```grue
;; Object with generated render
(object @brass-lantern
  :description "A battery-powered lantern."
  :render "A brass lantern with glass panels and a metal handle")

;; Object with static image
(object @hacker
  :description "hacker"
  :render (:ref "refs/hacker.jpg"))

;; State-dependent render
(object @microwave
  :render (fn ()
    (if (:open ?self)
      "An institutional white microwave, door open"
      "An institutional white microwave, door closed")))

;; Composite with other object references
(object @desk-setup
  :render ("A cluttered computer desk with "
           @pc-tower " tower underneath, "
           @monitor " on top"))
```

### Scene Composition

```grue
;; Room with dynamic contents
(room @terminal-room
  :render (@terminal-room-bg
           "with the following objects:"
           :contents
           "The hacker is typing furiously"))

;; Room with cross-room visibility through portal
(room @cs-2nd
  :render (fn ()
    (if (:open @elevator-door-2)
      '(@cs-2nd-bg
        "visible to the north is" @terminal-room
        :contents
        (:through @elevator-door-2 @cs-elevator-room))
      '(@cs-2nd-bg
        "visible to the north is" @terminal-room
        :contents))))
```

## Render Resolution

```
render(entity, game-state) → image:
  1. Evaluate render spec with self=entity
  2. Collect prompt (concatenated strings from text + object/room descriptions)
     - Objects/rooms contribute their :rdesc (or :description as fallback)
     - References contribute no text (caller wraps with descriptive text)
  3. Collect reference images:
     - :ref paths → load static file from assets dir
     - @object/@room refs → render recursively, use rendered image
     - @reference refs → render recursively, use rendered image
     - :contents → render each object at entity's location
     - :through @portal @target → if portal open, render target room
  4. For pure :ref specs (no prompt): return static file directly (no generation)
  5. Compute cache key = hash(prompt, sorted(ref-hashes))
  6. If cached, return cached image
  7. Call filfre with prompt + ref images
  8. Cache result and return
```

## Caching Strategy

Images are cached by content hash:
- **Key**: hash(canonical_prompt, sorted([hash(ref_image) for ref in refs]))
- **Storage**: `cache/renders/<hash>.png`
- **Pre-caching**: Commit known-good renders to repo for deterministic builds

Cache invalidation:
- Prompt changes → new key
- Reference image changes → new key (content-addressed)
- Model version changes → clear cache (or version in key)

## Consistency Strategies

### Reference Degradation

Each composition layer introduces drift from original references. Mitigation:

1. **Anchoring**: Re-include atomic refs at deeper layers
   ```grue
   :render ("Scene with " @composite-obj
            :anchor @atomic-obj)  ; re-anchor to original
   ```

2. **Ref-size scaling**: Use larger ref-size for important/early refs
   ```grue
   :render (@important-char :ref-size 384
            @background-obj :ref-size 128)
   ```

3. **Layer limits**: Keep composition depth ≤ 3 layers where possible

### State-Aware Descriptions (`:rdesc`)

When composing scenes, the text prompt must describe the current visual state of objects.
The `:rdesc` field on entities provides this - separate from the player-facing `:description`.

For example, a microwave's `:description` might be "microwave oven" for all states, but
its `:rdesc` can be:
- `"open microwave oven"` when open
- `"running microwave oven with turntable spinning"` when running
- `"closed microwave oven"` otherwise

This ensures the generated image matches the game state, even when reference images
(which provide visual consistency) might show a different state.

See [grue.md](grue.md#render-descriptions-rdesc) for syntax details.

### Lighting Consistency

- Atomics should use flat/ambient lighting (no strong directional shadows)
- Scene-layer prompts specify lighting; FLUX adapts refs accordingly
- Test: Generate same object with different scene lighting, verify consistency

### Scale Consistency

- Establish relative scales in composite prompts ("small lantern on large table")
- Consider explicit scale hints in render specs (future work)

## Experimental Validation

Before finalizing the system, validate with experiments:

### Experiment 1: Reference Degradation
```bash
# Layer 0: Atomic
filfre -p "A brass lantern" -r lantern-base.png -o L0.png

# Layer 1: Composite
filfre -p "Brass lantern on wooden table" -r L0.png -r table-base.png -o L1.png

# Layer 2: Scene (no anchoring)
filfre -p "Wooden table with lantern in stone cellar" \
  -r L1.png -r cellar-base.png -o L2-no-anchor.png

# Layer 2: Scene (with anchoring)
filfre -p "Wooden table with lantern in stone cellar" \
  -r lantern-base.png -r L1.png -r cellar-base.png -o L2-anchored.png
```
Compare L2 variants for lantern fidelity to original.

### Experiment 2: Ref-Size Impact
```bash
for size in 128 256 384 512; do
  filfre -p "Lantern on table in cellar" \
    -r lantern.png --ref-size $size -r table.png -r cellar.png \
    -o "refsize-$size.png"
done
```

### Experiment 3: Lighting Adaptation
```bash
# Same object, different scene lighting
filfre -p "Brass lantern in bright sunlit room" -r lantern.png -o sunny.png
filfre -p "Brass lantern in dark candlelit dungeon" -r lantern.png -o dark.png
```
Verify object maintains identity across lighting conditions.

## Future Work

- [ ] Scale hints in render specs
- [ ] Weighted reference importance
- [ ] Automatic quality gates (detect bad compositions)
- [ ] Render preview mode for iteration
- [ ] Batch pre-rendering for game builds
