# Transparent Overlay Composition Experiments

## Hypothesis

Giving a generative image model a single pre-composited reference image — background at full opacity with foreground elements overlaid at reduced opacity — produces more controllable compositions than passing multiple separate reference images. The overlay encodes spatial priors (position, scale, orientation) that text conditioning alone cannot express.

## Setup

- **Model**: NanoBanana (Gemini 2.5 Flash Image) via filfre API
- **Output**: 1024x1024 comic book art style
- **Scenes**: Terminal room (1980s computer lab) and kitchen (institutional basement)
- **References**: Room backgrounds + isolated object/character refs on white backgrounds
- **Pipeline**: `overlay.py` — builds RGBA overlays, feeds as single reference to model

## Round 1: Basic overlay approach (terminal room)

**Trials**: Hacker character overlaid on terminal room background at various positions, scales, and opacities.

### What worked

- **Position/scale transfer**: The model reliably places objects where the overlay puts them, at roughly the right scale. This works across opacity levels 0.3-0.7.
- **Character identity**: Clothing, build, and general appearance transfer well from the reference.
- **Orientation**: Flipping the overlay horizontally produces a flipped character in the output.
- **Text can override pose**: Describing "sitting" produces a seated character even when the ref shows standing. The overlay provides WHERE, the text provides WHAT.

### What didn't work

- **Small object identity**: A blue armchair was consistently lost — the model defaulted to a contextually-appropriate generic office chair. The object was too small relative to the scene to preserve its specific identity.

## Round 2: Multi-subject composition (terminal room)

**Problem**: When compositing 3+ objects in a single overlay, small object identity is lost regardless of opacity weighting (uniform 0.5, foreground-weighted 0.7/0.3, object-weighted).

### Stepwise composition

Chaining multiple generation steps — `(bg + chair) → result + hacker → final` — solved this dramatically. Each step integrates one element with full model attention.

- **2 steps**: Sweet spot. Each object gets properly integrated.
- **3 steps**: Diminishing returns. New overlays start conflicting with elements the model already committed to in earlier steps.

## Round 3: State-dependent rendering (kitchen)

Attempted to render different appliance states (microwave open/closed/running, fridge open/closed) by overlaying state-specific references onto the kitchen background.

### Key finding: Addition, not replacement

Overlaying an open microwave on top of an existing closed microwave in the background produced double-exposure artifacts — ghostly mixtures of both states. The model cannot cleanly replace an object that's already in the background.

**Solution: Empty stages.** Room backgrounds should be rendered without stateful/movable objects. Objects are then added via overlay steps onto the empty background. This produced dramatically cleaner results.

## Round 4: Positioning and opacity (v2 trials)

The initial kitchen placements had spatial errors that the model faithfully reproduced:
- Microwave floating above the counter (y too high)
- Fridge clipped off the right edge of the canvas (x too far right)

### Bounding box alignment

Used PIL to measure visible (non-transparent) pixel bounds after white-background removal and resizing. Aligned object bottoms to scene geometry:
- Microwave body bottom → counter surface (~y=440)
- Fridge body bottom → floor line (~y=600)

### Opacity for step-2 additions

| Step-2 opacity | Result |
|:---:|---|
| 0.5 | Ghostly/translucent — model doesn't commit to the addition |
| 0.7 | Better but still slightly transparent |
| 0.85 | Solid objects, background hints still visible through edges |
| 0.9 | Best for step-2 — strong signal, slight bleed-through for consistency |
| 0.95 | Nearly opaque, works well for single-shot but may obscure context |

**Recommendation**: 0.85 for step 1 (on empty background), 0.9 for step 2 (on already-generated scene).

## Round 5: Text conditioning levels (v3 trials)

Tested three levels of text conditioning with the same high-opacity overlays:

### Style-only: `"Comic book art, bold ink outlines."`

No semantic guidance. The model hallucinated wildly — the semi-transparent fridge overlay was interpreted as an exploding/toppling fridge. Demonstrates that SOME text grounding is necessary.

### Keywords: `"Comic book art. Kitchen, closed refrigerator, fluorescent lights."`

The model overrode the overlay with its own interpretation of the keywords. "Closed refrigerator" somehow produced dark moody lighting and a glowing open fridge. Keywords without spatial context can fight the visual reference.

### Spatial (one-sentence): `"Comic book art. Kitchen with closed refrigerator in the corner."`

Best results across the board. The overlay handles position/scale/identity, while the text provides just enough semantic framing. The model respects both signals without either dominating.

**Spatial text produced the first correct closed-fridge rendering** in the entire experiment series. Detailed descriptions in earlier rounds had consistently caused the model to open the fridge.

## High-level takeaways

### 1. Overlay value scales with reference clarity

| Reference type | Overlay strategy |
|---|---|
| Visually unambiguous (open fridge, open microwave — you can see what it IS) | High opacity (0.85-0.9), minimal text |
| Visually ambiguous (closed fridge covered in notes — could be open with contents) | Low or no overlay, rely on text for state |

When the reference image clearly communicates its state, the overlay is the primary signal. When it's ambiguous, the overlay actively hurts by introducing visual noise that the model misinterprets.

### 2. Empty stages are essential

Room backgrounds must be rendered WITHOUT stateful objects. Adding objects to empty space works; replacing objects in occupied space does not. This has architectural implications for the render pipeline — we need "base room" renders separate from object placement.

### 3. Stepwise > single-shot for multi-object scenes

For 2+ objects, chain generation steps rather than compositing everything into one overlay. 2 steps is the sweet spot. Each step should add one object or a tightly-coupled group.

### 4. Text should frame, not describe

Minimal spatial text (`"Kitchen with X in the corner, Y on the counter"`) outperforms detailed narrative descriptions (`"A dingy institutional kitchen in a university basement with fluorescent lights..."`). The overlay already encodes the visual detail; verbose text competes with it and can override the model's interpretation of the reference.

### 5. Position accuracy matters more than you'd think

The model is surprisingly literal about overlay placement. A microwave 60px above the counter surface will render floating. Bounding-box analysis of the reference (after bg removal + resize) and alignment to scene geometry is worth the effort.

## Open questions

- **Adaptive opacity**: Can we formalize the "ambiguous reference" detection and automatically reduce overlay weight?
- **Seed sensitivity**: How much do results vary across seeds? We used fixed seeds (42, 43) — a sweep would reveal robustness.
- **3+ step chains**: Are there scene configurations where 3 steps work if objects are ordered carefully (back-to-front)?
- **Reference style matching**: The object refs are isolated on white backgrounds in a slightly different art style than the backgrounds. Would style-matched refs improve integration?
- **Pipeline integration**: How does this translate into the automated `compose.py` pipeline for the layout experiment? The stepwise approach needs scene-graph-aware ordering.
