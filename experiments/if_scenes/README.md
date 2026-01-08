# Interactive Fiction Scene Experiments

Testing OmniGen2's ability to generate classic interactive fiction scenes with multiple objects and spatial relationships.

## Scenes Generated

### 1. Wizard's Study (4 objects)

![](./wizard_study.png)

**Objects**: Cauldron, spellbook, potion, skull with candle

| Object | Spatial Relationship | Result |
|--------|---------------------|--------|
| Cauldron | ON FLOOR, foreground | ✓ |
| Spellbook | OPEN on workbench | ✓ |
| Potion | ON bench, RIGHT of book | ✓ |
| Skull/candle | High shelf ABOVE bench | ✓ |

**Prompt highlights**:
- "sits ON THE FLOOR in the center foreground"
- "lies OPEN on the wooden workbench"
- "stands ON the workbench TO THE RIGHT of the spellbook"
- "sits on a high shelf ABOVE the workbench"

---

### 2. Treasure Hoard (3 objects)

![](./treasure_hoard.png)

**Objects**: Treasure chest, crown, lantern

| Object | Spatial Relationship | Result |
|--------|---------------------|--------|
| Chest | CENTER of scene | ✓ |
| Crown | ON TOP of coins INSIDE chest | ✓ |
| Lantern | TO THE LEFT of chest | ✓ |
| Scattered coins | AROUND chest | ✓ |

**Prompt highlights**:
- "sits in the CENTER of the scene"
- "rests ON TOP of the pile of coins INSIDE the chest"
- "sits on the floor TO THE LEFT of the chest"
- "Scattered coins on the floor AROUND the chest"

---

### 3. Dark Passage / Grue Scene (3 objects)

![](./dark_passage.png)

**Objects**: Lantern (held), key, grue

| Object | Spatial Relationship | Result |
|--------|---------------------|--------|
| Lantern | HELD IN FOREGROUND | ✓ Hand holding it! |
| Circle of light | Illuminated area | ✓ |
| Grue eyes | IN DARKNESS at far end | ✓ |
| Key | IN CENTER of lit area | ✗ Not visible |

**Prompt highlights**:
- "is held IN THE FOREGROUND at the bottom of the image"
- "lies on the stone floor IN THE CENTER of the lit area"
- "BEYOND the circle of light, IN THE DARKNESS... PARTIALLY HIDDEN by shadow"

**Note**: First-person perspective with held object worked! The key was likely too small.

---

### 4. Locked Door Puzzle (3 objects)

![](./locked_door_puzzle.png)

**Objects**: Door, key, scroll

| Object | Spatial Relationship | Result |
|--------|---------------------|--------|
| Door | CENTER of far wall | ✓ |
| Key | ON hook on LEFT wall | ✓ |
| Scroll | ON table in RIGHT foreground | ✓ |

**Prompt highlights**:
- "dominates the CENTER of the far wall"
- "hangs on a hook on the LEFT wall"
- "lies unrolled on a small wooden table in the RIGHT foreground"

---

## Reference Objects Generated

| File | Object | Quality |
|------|--------|---------|
| ref_cauldron.png | Bubbling cauldron | ✓ Good |
| ref_spellbook.png | Leather-bound spellbook | ✓ Good |
| ref_potion.png | Glass potion bottle | ✓ Good |
| ref_skull_candle.png | Skull with candle | ✓ Good |
| ref_crown.png | Ornate crown | ✓ Good |
| ref_chest.png | Open treasure chest | ✓ Good |
| ref_gem.png | Cut diamond | ⚠️ Too faint |
| ref_key.png | Skeleton key | ✓ Good |
| ref_grue.png | Glowing eyes in dark | ✓ Perfect |
| ref_door.png | Heavy wooden door | ✓ Good |
| ref_scroll.png | Unrolled parchment | ✓ Good |

## Key Findings

### Spatial Relationships That Work

| Relationship | Success Rate | Notes |
|--------------|--------------|-------|
| ON TOP of | High | Clear stacking |
| INSIDE | High | Visible through containers |
| TO THE LEFT/RIGHT of | High | Clear lateral placement |
| IN FOREGROUND | High | First-person works! |
| ABOVE | High | Vertical positioning |
| IN DARKNESS / HIDDEN | Medium | Works for contrast |
| Small objects on floor | Low | May be omitted |

### Prompt Structure for Multi-Object Scenes

```
[STYLE]: Pen and ink illustration, heavy cross-hatching, bold linework.

CAMERA: [Explicit viewpoint description]

SCENE LAYOUT:
The [object] from <img1> [SPATIAL RELATIONSHIP] [location].
The [object] from <img2> [SPATIAL RELATIONSHIP] [location].
...

ENVIRONMENT:
[Background details, atmosphere]

[SIZE HINTS - optional]:
The [object] is [X feet/inches tall/wide].
```

### What Works Well

1. **4 objects in one scene** - Successfully placed all 4 in wizard's study
2. **Multiple spatial relationships** - ON, INSIDE, ABOVE, LEFT/RIGHT all work
3. **First-person perspective** - Hand holding object works beautifully
4. **Light/dark contrast** - Grue scene captured perfectly
5. **Classic IF tropes** - All translate well to visual form

### Challenges

1. **Small objects** - May be omitted or hard to see (key in dark passage)
2. **Faint objects** - Some refs come out too light (gem, anything "sparkling")
3. **Complex occlusion** - "BEHIND" and "PARTIALLY HIDDEN" less reliable

## Command Reference

```bash
# Generate reference object
python test_omnigen2.py --scene custom \
  --prompt "A detailed ink illustration of [OBJECT], heavy cross-hatching, bold pen strokes, strong contrast, isolated subject" \
  --output ref_[name].png \
  --width 256 --height 256 --steps 25 --seed [N] \
  --taylorseer --cfg-range-end 0.7

# Compose scene with 3-4 objects
python test_omnigen2.py --scene custom \
  --reference ref1.png --reference ref2.png --reference ref3.png \
  --prompt "[STRUCTURED PROMPT]" \
  --output scene.png \
  --width 1024 --height 1024 --steps 30 --seed 42 \
  --taylorseer --cfg-range-end 0.7 --image-guidance 3.0
```
