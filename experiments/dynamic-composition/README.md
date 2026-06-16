# filfre Implementation Notes

Notes on the dynamic composition system that was integrated into gnusto for
real-time scene rendering during gameplay. This was retired from gnusto in favor
of keeping filfre as a standalone tool. Preserved here for future reference.

## What We Built

### Hierarchical Composition

Three-layer approach for generating consistent illustrations:

1. **Atomic** - Base reference images (hand-drawn or carefully generated).
   Neutral backgrounds, flat lighting. These are the ground truth.

2. **Composite** - Combinations of atomics using FLUX.2 Klein's reference
   image conditioning. E.g., `@pc = tower + monitor + keyboard`.

3. **Scene** - Full runtime composition. Room background + contained objects +
   characters, assembled dynamically based on game state.

### Render Spec Composition Features

The Grue `:render` spec supported rich composition via these constructs:

- **`ObjectRef`** (`@entity` in render spec) - Recursively render another
  entity, use its image as a reference, and contribute its `:description`
  (or `:rdesc`) to the prompt text.

- **`ContentsMarker`** (`:contents`) - Automatically include all objects at
  a location. Each contributes its description and rendered image.

- **`ThroughMarker`** (`(:through @portal @room)`) - When a door/portal is
  open, include the target room's rendered image as a reference.

- **Anchoring** (`:anchor @obj`) - Re-include an atomic reference image at
  deeper composition layers to reduce visual drift.

- **`:ref-size N`** - Control reference image resolution per-entity. Higher
  for important foreground objects, lower for backgrounds.

- **`:rdesc`** - Separate "render description" field on entities, distinct
  from player-facing `:description`. State-aware (could be a function).

- **`:render-style`** on `(world ...)` - Global style prefix prepended to
  all generation prompts (e.g., "Color graphic novel style.").

- **`(reference ...)` form** - Named render specs with no runtime state.
  Pure visual assets that could be composed into scenes.

### SceneRenderer's Recursive Resolution

`SceneRenderer._render_entity()` worked as follows:

1. Evaluate the render spec with `self` bound to the entity
2. `_build_request()` walks `RenderResult.prompt_parts`:
   - Strings -> concatenated into prompt text
   - `ObjectRef` -> get entity description for prompt + recursively render
     for reference image
   - `ContentsMarker` -> find objects at location, get descriptions + render
   - `ThroughMarker` -> check portal state, conditionally include target room
3. Resolve `:anchor` references (re-include atomic images)
4. Prepend world `:render-style` if configured
5. Compute content-addressed cache key from prompt + reference image hashes
6. Check two-tier cache (frozen / working) before generating
7. Generate via FLUX.2 Klein (local CUDA) or NanoBanana (Gemini cloud API)
8. Cache result and return path

Recursion depth was capped at 5 layers.

### Two-Tier Caching (RenderCache)

- **Frozen** renders (`assets/renders/*.png`) - checked into git, used as
  ground truth for deterministic builds
- **Working cache** (`assets/renders/cache/*.png`) - gitignored, generated
  during play
- **Render log** (`render-log.jsonl`) - append-only audit trail of all
  generations with prompt, refs, hashes, timestamps
- Content-addressed keys: `SHA256(model_version + prompt + sorted(ref_hashes))`

### Integration Points

- **gnusto TUI** (`tui.py`) - `_init_scene_renderer()` loaded the pipeline,
  `_render_room_image()` generated on room entry, `_render_object_image()`
  for inline object images
- **gnusto web** (`web.py`) - Same via `_create_scene_renderer()`, served
  rendered images at `/renders/{path}`
- **gnusto agent** (`agent.py`) - `images.py` provided `ImageInfo` catalog
  to LLM context so it knew which entities were renderable
- **filfre CLI** - `render` subcommand used `SceneRenderer` directly for
  testing render specs and pre-caching

## What Worked

- **Simple text prompts** with no references produced good standalone images
- **Caching** was essential - same room/object rendered identically on replay
- **NanoBanana (Gemini)** was more reliable than FLUX for composition quality
- **`:rdesc`** was a good design - separating visual from textual descriptions
- **Two-tier cache** (frozen + working) was a good workflow - freeze good
  renders, iterate on working cache

## What Didn't Work

- **Composition drift** - Each layer of reference-conditioned generation
  degraded fidelity to the original atomic images. By layer 3, objects
  could be unrecognizable.
- **Anchoring helped but wasn't enough** - Re-including atomic refs reduced
  drift but didn't eliminate it, and added more refs (slower generation).
- **FLUX.2 Klein** struggled with multi-reference composition. It could
  handle 1-2 refs well but 3+ became unreliable.
- **State-dependent rendering** was hard to cache effectively - many
  combinations of object states.
- **Startup cost** - Loading the FLUX pipeline added ~6s to game launch.
  NanoBanana avoided this but required network + API key.

## How to Resurrect This

If composition quality improves (better models, better conditioning):

1. The `RenderCache` is preserved in `src/filfre/render_cache.py`
2. The `SceneRenderer` is preserved in `src/filfre/scene_renderer.py`
3. The render spec evaluation (`ObjectRef`, `ContentsMarker`, etc.) would
   need to be restored in `grue/render.py` (currently simplified to strings)
4. The `GrueReference` form, `:rdesc`, and `:render-style` would need to be
   added back to `grue/forms.py`
5. Re-integrate into gnusto's TUI/web by adding back `--model` flag and
   scene renderer initialization

The key insight: the *architecture* was sound (hierarchical composition with
content-addressed caching). The *execution* was limited by current model
capabilities for multi-reference image conditioning.
