# Spatial Control Experiment

Testing OmniGen2's ability to control viewpoint, object placement, scale, and spatial relationships in composed scenes.

## Key Findings

### What Works

| Technique | Effectiveness | Notes |
|-----------|--------------|-------|
| Explicit camera language | ✅ High | "Straight-on frontal view, eye-level, symmetrical" |
| Emphasized spatial words | ✅ High | "ON TOP of", "IMMEDIATELY TO THE RIGHT", "INSIDE" |
| Size references | ✅ Medium | "6 feet tall", "1 foot tall", "3 feet long" |
| Higher image guidance | ✅ High | 3.0 vs 2.5 improves reference fidelity |
| INSIDE relationship | ✅ High | Objects visible through glass containers |
| UNDER/BENEATH | ✅ Medium | Works but may shift to "beside" |

### What Doesn't Work

| Issue | Workaround |
|-------|------------|
| Vague viewpoint language | Use explicit camera terms |
| Generic spatial terms | Capitalize and emphasize: "ON TOP", "INSIDE" |
| Seed variance | Same prompt + different seeds = different perspectives |
| Reference object substitution | Higher image-guidance (3.0+) helps |

## Experiment Results

### Viewpoint Consistency Test

Same prompt, different seeds - shows perspective variance without explicit camera control:

| File | Seed | Perspective | Objects |
|------|------|-------------|---------|
| view_test_seed42.png | 42 | Corner angle | Case ✓, Sword ✗, Lantern ✗ |
| view_test_seed99.png | 99 | Corner angle | Case ✓, Sword ✓, Lantern ✗ |
| view_test_seed200.png | 200 | More frontal | Case ✓, Sword ✓, Lantern ? |

**Conclusion**: Without explicit camera language, viewpoint varies significantly across seeds.

### Explicit Spatial Control Test

**spatial_explicit_v1.png** - Best result with explicit language:
- "CAMERA: Straight-on frontal view, eye-level, symmetrical composition"
- Objects referenced with "ON TOP of", "IMMEDIATELY TO THE RIGHT"
- Size hints: "6 feet tall", "1 foot tall", "3 feet long"
- image-guidance: 3.0

**Result**: Trophy case centered, lantern on top (recognizable), sword to right (recognizable), frontal view ✓

### Spatial Relationship Tests

**spatial_inside_under.png** - Testing INSIDE + BENEATH:
- Sword "INSIDE the trophy case, visible through the glass doors"
- Lantern "on the floor BENEATH the trophy case"
- Result: Both relationships understood ✓

**spatial_both_inside.png** - Testing multiple objects INSIDE:
- Lantern "INSIDE the trophy case on the top shelf"
- Sword "INSIDE the trophy case on the bottom shelf"
- Result: Both objects visible through glass ✓

## Reference Objects

| File | Object | Notes |
|------|--------|-------|
| ref_trophy_case.png | Ornate display case | Glass doors, decorative molding |
| ref_lantern.png | Brass lantern | Cross-hatched ink style |
| ref_sword.png | Elvish sword | Curved blade, ornate handle |

## Recommended Prompt Structure

```
[STYLE]: Pen and ink illustration, heavy cross-hatching, bold linework.

CAMERA: [Explicit viewpoint - "Straight-on frontal view, eye-level, symmetrical"]

[OBJECT PLACEMENT]:
The [object] from <img1> is [POSITION] [relative to scene/other objects].
The [object] from <img2> [SPATIAL RELATIONSHIP] [object/location].

[SIZE HINTS - optional]:
The [object] is [X feet tall/long].

[SCENE DETAILS]:
[Background, floor, walls, etc.]
```

## Spatial Relationship Keywords

Tested and working:
- **ON TOP of** - object resting on surface of another
- **TO THE RIGHT/LEFT of** - horizontal positioning
- **INSIDE** - contained within (visible through glass)
- **BENEATH/UNDER** - below another object

## Command Reference

```bash
# Basic composition with explicit spatial control
python test_omnigen2.py --scene custom \
  --reference ref1.png --reference ref2.png \
  --prompt "CAMERA: Straight-on frontal view..." \
  --output output.png \
  --width 1024 --height 1024 --steps 30 --seed 42 \
  --taylorseer --cfg-range-end 0.7 \
  --image-guidance 3.0  # Higher = better reference fidelity
```
