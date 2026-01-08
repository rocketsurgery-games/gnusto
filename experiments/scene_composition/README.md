# Scene Composition Experiment

Testing OmniGen2's ability to compose multiple objects into a scene using in-context generation with reference images.

## Experiment Goals

1. Generate isolated object references at 256x256 (efficient for composition)
2. Compose objects into a larger scene (flood control dam)
3. Maintain consistent pen/ink illustration style throughout

## Object Reference Images

### test_isolated_lantern.png ✅ GOOD

![](./test_isolated_lantern.png]

```bash
python test_omnigen2.py --scene custom \
  --prompt "A detailed pen and ink drawing of an old brass lantern, crisp linework, cross-hatching for shadows, isolated subject" \
  --output test_isolated_lantern.png \
  --width 256 --height 256 --steps 25 --seed 42 \
  --taylorseer --cfg-range-end 0.7
```

**Assessment**: Excellent. Clean pen/ink style with cross-hatching. Good isolated subject on white background.

### test_isolated_wrench.png ✅ GOOD

```bash
python test_omnigen2.py --scene custom \
  --prompt "A detailed pen and ink drawing of a heavy iron wrench, crisp linework, cross-hatching for shadows and metal texture, isolated subject" \
  --output test_isolated_wrench.png \
  --width 256 --height 256 --steps 25 --seed 42 \
  --taylorseer --cfg-range-end 0.7
```

**Assessment**: Excellent. Strong cross-hatching, clear metal texture, good isolation.

### test_isolated_lever.png ⚠️ MEDIOCRE

```bash
python test_omnigen2.py --scene custom \
  --prompt "A detailed pen and ink drawing of an industrial control lever on a panel, crisp linework, cross-hatching for metal, isolated subject" \
  --output test_isolated_lever.png \
  --width 256 --height 256 --steps 25 --seed 42 \
  --taylorseer --cfg-range-end 0.7
```

**Assessment**: Came out as a control panel/box rather than a lever. Prompt needs refinement.

### test_isolated_boat.png ⚠️ STYLE MISMATCH

```bash
python test_omnigen2.py --scene custom \
  --prompt "A detailed pen and ink drawing of a small yellow inflatable raft with oars, crisp linework, cross-hatching for shadows, isolated subject" \
  --output test_isolated_boat.png \
  --width 256 --height 256 --steps 25 --seed 42 \
  --taylorseer --cfg-range-end 0.7
```

**Assessment**: Generated a yellow-colored boat instead of B&W ink. The "yellow" in prompt overrode the ink style. Caused style drift when used in composition.

### test_isolated_boat_bw.png ❌ FAILED

```bash
python test_omnigen2.py --scene custom \
  --prompt "A detailed pen and ink drawing of a small inflatable raft with oars, crisp linework, cross-hatching for rubber texture and shadows, isolated subject, black and white" \
  --output test_isolated_boat_bw.png \
  --width 256 --height 256 --steps 25 --seed 43 \
  --taylorseer --cfg-range-end 0.7
```

**Assessment**: Nearly blank output. The phrase "black and white" at 256x256 triggers the same blank-output issue as "blank background".

### test_isolated_boat_ink.png ✅ GOOD

```bash
python test_omnigen2.py --scene custom \
  --prompt "A detailed ink illustration of a small rubber dinghy with wooden oars, heavy cross-hatching, bold pen strokes, strong contrast, isolated subject" \
  --output test_isolated_boat_ink.png \
  --width 256 --height 256 --steps 25 --seed 44 \
  --taylorseer --cfg-range-end 0.7
```

**Assessment**: Excellent. Proper B&W ink with cross-hatching. Using "bold pen strokes, strong contrast" instead of "black and white" avoids the blank output issue.

## Scene Compositions

### test_dam_composed.png ✅ GOOD (2 objects)

```bash
python test_omnigen2.py --scene custom \
  --reference test_isolated_lantern.png \
  --reference test_isolated_wrench.png \
  --prompt "A detailed pen and ink illustration of a massive concrete flood control dam stretching across a river gorge, brutalist industrial architecture. Cross-hatching for shadows and textures.

On the walkway atop the dam, the brass lantern from <img1> sits on the concrete railing, casting a warm glow. Near the control room entrance, the heavy wrench from <img2> lies abandoned on the ground.

Water cascades down the spillway. Mist rises from the churning waters below. Warning signs posted near metal doors. The scene conveys overwhelming scale and industrial power.

Crisp linework, detailed pen strokes, high contrast black and white with selective shading." \
  --output test_dam_composed.png \
  --width 1024 --height 1024 --steps 30 --seed 42 \
  --taylorseer --cfg-range-end 0.7 --image-guidance 2.5
```

**Assessment**: Excellent composition. Both objects placed appropriately (lantern on railing, wrench at base). Consistent pen/ink style throughout. Good scene detail with dam architecture, water, and warning signs.

### test_dam_3objects.png ⚠️ STYLE DRIFT (3 objects, colored ref)

```bash
python test_omnigen2.py --scene custom \
  --reference test_isolated_lantern.png \
  --reference test_isolated_wrench.png \
  --reference test_isolated_boat.png \
  --prompt "A detailed pen and ink illustration of a massive concrete flood control dam, brutalist industrial architecture. Cross-hatching for shadows and textures.

The brass lantern from <img1> sits on the walkway railing at the top of the dam.
The heavy wrench from <img2> lies on the concrete near the control room door.
Below, the yellow inflatable boat from <img3> floats in the churning water at the base of the dam, tethered to a post.

Water cascades down the spillway creating mist. Warning signs near metal doors. Overwhelming industrial scale.

Detailed pen strokes, crisp linework, high contrast." \
  --output test_dam_3objects.png \
  --width 1024 --height 1024 --steps 30 --seed 42 \
  --taylorseer --cfg-range-end 0.7 --image-guidance 2.5
```

**Assessment**: Style drifted from pure pen/ink to mixed-media colored illustration. The yellow boat reference "leaked" color into the entire scene. Objects placed correctly, but style consistency lost.

### test_dam_3objects_bw.png ✅ BEST (3 objects, all B&W refs)

```bash
python test_omnigen2.py --scene custom \
  --reference test_isolated_lantern.png \
  --reference test_isolated_wrench.png \
  --reference test_isolated_boat_ink.png \
  --prompt "A detailed pen and ink illustration of a massive concrete flood control dam, brutalist industrial architecture. Heavy cross-hatching for shadows and textures, bold linework, high contrast.

The brass lantern from <img1> sits on the walkway railing at the top of the dam, its glow suggested by radiating lines.
The heavy wrench from <img2> lies on the concrete near the control room door at the top.
Below at the base, the wooden boat from <img3> floats in the churning water, tethered to a post near the spillway.

Water cascades down creating mist rendered in fine pen strokes. Warning signs near metal doors. Overwhelming industrial scale.

Bold ink illustration style, crisp linework, no color." \
  --output test_dam_3objects_bw.png \
  --width 1024 --height 1024 --steps 30 --seed 42 \
  --taylorseer --cfg-range-end 0.7 --image-guidance 2.5
```

**Assessment**: Best result. Consistent pen/ink style throughout. Lantern visible on railing, boat in water. Wrench not clearly visible (may need stronger placement cues). All B&W references maintained style coherence.

## Key Findings

### Style Consistency

| Reference Style | Output Style |
|-----------------|--------------|
| All B&W ink | Consistent B&W ink |
| Mixed (colored + B&W) | Color bleeds into scene |

### Prompt Patterns at 256x256

| Pattern | Result |
|---------|--------|
| "isolated subject" | ✅ Works |
| "blank background" | ❌ Blank output |
| "black and white" | ❌ Blank output |
| "bold pen strokes, strong contrast" | ✅ Works |

### Object Placement

- Objects generally placed according to prompt descriptions
- 2 objects: reliable placement
- 3+ objects: some may be omitted if not prominent in prompt

## Recommended Workflow

1. **Object references**: Generate at 256x256 with:
   ```
   "detailed ink illustration of [OBJECT], heavy cross-hatching, bold pen strokes, strong contrast, isolated subject"
   ```

2. **Scene composition**: Generate at 1024x1024 with:
   - All references in same style family
   - Explicit placement descriptions for each object
   - Style reinforcement: "pen and ink, cross-hatching, bold linework"

3. **Avoid**: Color words in B&W prompts, "black and white" or "blank background" at small sizes
