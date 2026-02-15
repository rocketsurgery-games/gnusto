#!/usr/bin/env python3
"""Transparent overlay composition experiment.

Hypothesis: Giving a diffusion model a rough spatial prior via transparent
overlays produces more controllable compositions than passing separate
reference images. The model receives a single image with the background
at full opacity and foreground elements at reduced opacity, positioned
at roughly correct locations and scales.

Usage:
    python overlay.py                     # Run all trials
    python overlay.py --trial hacker-at-desk
    python overlay.py --build-only        # Just build overlays, don't generate
    python overlay.py --baseline          # Also generate baseline (separate refs)
"""

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

REFS = Path(__file__).parent / "refs"
OUTPUT = Path(__file__).parent / "output"


# ---------------------------------------------------------------------------
# Image utilities
# ---------------------------------------------------------------------------

def load_ref(name: str) -> Image.Image:
    """Load a reference image by short name (e.g., 'hacker')."""
    for ext in (".jpg", ".png"):
        path = REFS / f"{name}{ext}"
        if path.exists():
            img = Image.open(path).convert("RGBA")
            transposed = ImageOps.exif_transpose(img)
            if transposed is not None:
                img = transposed
            return img
    raise FileNotFoundError(f"No ref found for '{name}' in {REFS}")


def remove_white_bg(img: Image.Image, threshold: int = 240) -> Image.Image:
    """Replace near-white pixels with transparency."""
    img = img.convert("RGBA")
    data = img.getdata()
    new_data = []
    for r, g, b, a in data:
        if r > threshold and g > threshold and b > threshold:
            new_data.append((r, g, b, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    return img


def set_opacity(img: Image.Image, opacity: float) -> Image.Image:
    """Scale the alpha channel of an RGBA image."""
    img = img.convert("RGBA")
    r, g, b, a = img.split()
    a = a.point(lambda x: int(x * opacity))
    return Image.merge("RGBA", (r, g, b, a))


def resize_to_height(img: Image.Image, height: int) -> Image.Image:
    """Resize preserving aspect ratio to target height."""
    w, h = img.size
    ratio = height / h
    return img.resize((int(w * ratio), height), Image.LANCZOS)


def resize_to_width(img: Image.Image, width: int) -> Image.Image:
    """Resize preserving aspect ratio to target width."""
    w, h = img.size
    ratio = width / w
    return img.resize((width, int(h * ratio)), Image.LANCZOS)


def flip_horizontal(img: Image.Image) -> Image.Image:
    """Mirror an image horizontally."""
    return img.transpose(Image.FLIP_LEFT_RIGHT)


# ---------------------------------------------------------------------------
# Overlay placement
# ---------------------------------------------------------------------------

@dataclass
class Placement:
    """Where and how to place a foreground element."""
    ref: str                    # Reference image name
    x: int                     # Left edge position on canvas
    y: int                     # Top edge position on canvas
    height: int | None = None  # Target height (preserves aspect ratio)
    width: int | None = None   # Target width (alternative to height)
    opacity: float = 0.5       # Alpha multiplier
    flip: bool = False         # Mirror horizontally
    remove_bg: bool = True     # Remove white background
    bg_threshold: int = 240    # White threshold for bg removal


@dataclass
class Trial:
    """A composition trial: background + overlays + text prompt."""
    name: str
    background: str             # Background ref name
    placements: list[Placement]
    prompt: str                 # Text conditioning for the model
    canvas_size: tuple[int, int] = (1024, 1024)
    notes: str = ""


def build_overlay(trial: Trial) -> Image.Image:
    """Build the transparent overlay composite for a trial."""
    # Start with background at full size
    bg = load_ref(trial.background).convert("RGBA")
    bg = bg.resize(trial.canvas_size, Image.LANCZOS)

    # Create canvas
    canvas = bg.copy()

    for p in trial.placements:
        fg = load_ref(p.ref)

        # Remove white background
        if p.remove_bg:
            fg = remove_white_bg(fg, p.bg_threshold)

        # Flip if needed
        if p.flip:
            fg = flip_horizontal(fg)

        # Resize
        if p.height:
            fg = resize_to_height(fg, p.height)
        elif p.width:
            fg = resize_to_width(fg, p.width)

        # Apply opacity
        fg = set_opacity(fg, p.opacity)

        # Paste onto canvas (alpha composite)
        canvas.paste(fg, (p.x, p.y), fg)

    return canvas


# ---------------------------------------------------------------------------
# Multi-step composition
# ---------------------------------------------------------------------------

@dataclass
class Step:
    """One step in a multi-step composition pipeline."""
    name: str                   # Step name for output files
    placements: list[Placement] # What to overlay on the *previous step's result*
    prompt: str                 # Text conditioning for this step
    seed: int = 42


@dataclass
class MultiTrial:
    """A multi-step composition trial: iteratively build up a scene."""
    name: str
    background: str
    steps: list[Step]
    canvas_size: tuple[int, int] = (1024, 1024)
    notes: str = ""


MULTI_TRIALS: dict[str, MultiTrial] = {}


def multi_trial(t: MultiTrial):
    MULTI_TRIALS[t.name] = t
    return t


def build_step_overlay(
    base: Image.Image,
    placements: list[Placement],
    canvas_size: tuple[int, int],
) -> Image.Image:
    """Overlay placements onto an existing base image (RGB or RGBA)."""
    canvas = base.convert("RGBA").resize(canvas_size, Image.LANCZOS)

    for p in placements:
        fg = load_ref(p.ref)
        if p.remove_bg:
            fg = remove_white_bg(fg, p.bg_threshold)
        if p.flip:
            fg = flip_horizontal(fg)
        if p.height:
            fg = resize_to_height(fg, p.height)
        elif p.width:
            fg = resize_to_width(fg, p.width)
        fg = set_opacity(fg, p.opacity)
        canvas.paste(fg, (p.x, p.y), fg)

    return canvas


def run_multi_trial(mt: MultiTrial, build_only: bool = False):
    """Run a multi-step composition trial."""
    from filfre.cli import generate_image_nanobanana

    print(f"\n{'='*60}")
    print(f"Multi-step trial: {mt.name}")
    print(f"  {mt.notes}")
    print(f"  Steps: {len(mt.steps)}")
    print(f"{'='*60}")

    trial_dir = OUTPUT / mt.name
    trial_dir.mkdir(parents=True, exist_ok=True)

    # Start with the background
    current = load_ref(mt.background).convert("RGBA")
    current = current.resize(mt.canvas_size, Image.LANCZOS)

    for i, step in enumerate(mt.steps):
        print(f"\n  --- Step {i+1}: {step.name} ---")
        print(f"  Placements: {len(step.placements)}")
        print(f"  Prompt: {step.prompt[:80]}...")

        # Build overlay on current result
        overlay = build_step_overlay(current, step.placements, mt.canvas_size)

        # Save overlay for inspection
        overlay_rgb = Image.new("RGB", overlay.size, (255, 255, 255))
        overlay_rgb.paste(overlay, mask=overlay.split()[3])
        overlay_path = trial_dir / f"step{i+1}-{step.name}-overlay.png"
        overlay_rgb.save(str(overlay_path))
        print(f"  Overlay: {overlay_path.name}")

        if build_only:
            # Use overlay as current for next step preview
            current = overlay
            continue

        # Generate
        start = time.time()
        result = generate_image_nanobanana(
            prompt=step.prompt,
            reference_images=[overlay_rgb],
            aspect_ratio="1:1",
            seed=step.seed,
        )
        elapsed = time.time() - start

        result_path = trial_dir / f"step{i+1}-{step.name}-result.png"
        result.save(str(result_path))
        print(f"  Result: {result_path.name} ({elapsed:.1f}s)")

        # Use this result as the base for the next step
        # NanoBanana returns google.genai.types.Image; reload as PIL
        current = Image.open(str(result_path)).convert("RGBA")

    # Save metadata
    meta = {
        "name": mt.name,
        "notes": mt.notes,
        "steps": [
            {
                "name": s.name,
                "prompt": s.prompt,
                "seed": s.seed,
                "placements": [
                    {"ref": p.ref, "x": p.x, "y": p.y,
                     "height": p.height, "width": p.width,
                     "opacity": p.opacity, "flip": p.flip}
                    for p in s.placements
                ],
            }
            for s in mt.steps
        ],
    }
    (trial_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Trial definitions
# ---------------------------------------------------------------------------

TRIALS: dict[str, Trial] = {}


def trial(t: Trial):
    TRIALS[t.name] = t
    return t


# Trial 1: Hacker sitting at desk - basic overlay
trial(Trial(
    name="hacker-at-desk",
    background="terminal-room",
    placements=[
        Placement(
            ref="hacker",
            x=280, y=180,
            height=700,
            opacity=0.5,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. Interior of a 1980s computer lab "
        "at night. A young man in a green work shirt and jeans sits typing "
        "at a terminal. CRT monitors glow in the background."
    ),
    notes="Single character overlay at 50% opacity",
))

# Trial 2: Hacker + chair, positioned together
trial(Trial(
    name="hacker-chair-composed",
    background="terminal-room",
    placements=[
        Placement(
            ref="chair",
            x=350, y=500,
            height=350,
            opacity=0.5,
        ),
        Placement(
            ref="hacker",
            x=250, y=150,
            height=700,
            opacity=0.5,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. Interior of a 1980s computer lab "
        "at night. A young man in a green work shirt and jeans sits in a "
        "battered office chair, typing furiously at a terminal."
    ),
    notes="Character + furniture, layered back-to-front",
))

# Trial 3: Hacker + PC, foreground focus
trial(Trial(
    name="hacker-pc-foreground",
    background="terminal-room",
    placements=[
        Placement(
            ref="hacker",
            x=100, y=150,
            height=700,
            opacity=0.5,
        ),
        Placement(
            ref="pc",
            x=550, y=350,
            height=450,
            opacity=0.5,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. A young hacker sits at a desk "
        "in a dark computer lab. In the foreground, a PC displays garbled "
        "characters on its CRT monitor. Late night atmosphere."
    ),
    notes="Two subjects at different depths",
))

# Trial 4: Same as trial 1 but vary opacity
trial(Trial(
    name="hacker-low-opacity",
    background="terminal-room",
    placements=[
        Placement(
            ref="hacker",
            x=280, y=180,
            height=700,
            opacity=0.3,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. Interior of a 1980s computer lab "
        "at night. A young man in a green work shirt and jeans sits typing "
        "at a terminal. CRT monitors glow in the background."
    ),
    notes="Lower opacity (0.3) - does model still pick up the spatial hint?",
))

trial(Trial(
    name="hacker-high-opacity",
    background="terminal-room",
    placements=[
        Placement(
            ref="hacker",
            x=280, y=180,
            height=700,
            opacity=0.7,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. Interior of a 1980s computer lab "
        "at night. A young man in a green work shirt and jeans sits typing "
        "at a terminal. CRT monitors glow in the background."
    ),
    notes="Higher opacity (0.7) - does it over-constrain the model?",
))

# --- Round 2: Explicit chair reference, multi-overlay opacity ---

# Trial 6: Hacker in the blue chair - chair visible and properly scaled
# Position chair slightly behind/below hacker so both are visible
trial(Trial(
    name="chair-explicit",
    background="terminal-room",
    placements=[
        Placement(
            ref="chair",
            x=330, y=480,
            height=420,
            opacity=0.5,
        ),
        Placement(
            ref="hacker",
            x=220, y=100,
            height=780,
            opacity=0.5,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. Interior of a 1980s computer lab "
        "at night. A young man in a green work shirt and jeans sits in a "
        "blue plastic armchair at a terminal, typing furiously."
    ),
    notes="Chair explicitly overlaid and visible, text mentions 'blue plastic armchair'",
))

# Trial 7: Three overlays, uniform 0.5 opacity
trial(Trial(
    name="three-uniform",
    background="terminal-room",
    placements=[
        Placement(
            ref="chair",
            x=330, y=480,
            height=420,
            opacity=0.5,
        ),
        Placement(
            ref="hacker",
            x=220, y=100,
            height=780,
            opacity=0.5,
        ),
        Placement(
            ref="pc",
            x=550, y=280,
            height=500,
            opacity=0.5,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. A 1980s computer lab at night. "
        "A young man in a green work shirt sits in a blue plastic armchair, "
        "typing at a nearby PC with a CRT monitor showing garbled characters."
    ),
    notes="Three overlays (chair+hacker+PC) all at 0.5",
))

# Trial 8: Three overlays, weighted - foreground elements stronger
trial(Trial(
    name="three-weighted-fg",
    background="terminal-room",
    placements=[
        Placement(
            ref="chair",
            x=330, y=480,
            height=420,
            opacity=0.3,
        ),
        Placement(
            ref="hacker",
            x=220, y=100,
            height=780,
            opacity=0.6,
        ),
        Placement(
            ref="pc",
            x=550, y=280,
            height=500,
            opacity=0.6,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. A 1980s computer lab at night. "
        "A young man in a green work shirt sits in a blue plastic armchair, "
        "typing at a nearby PC with a CRT monitor showing garbled characters."
    ),
    notes="Three overlays: hacker+PC at 0.6, chair at 0.3 (importance weighting)",
))

# Trial 9: Three overlays, weighted - chair strongest to test identity transfer
trial(Trial(
    name="three-weighted-chair",
    background="terminal-room",
    placements=[
        Placement(
            ref="chair",
            x=330, y=480,
            height=420,
            opacity=0.7,
        ),
        Placement(
            ref="hacker",
            x=220, y=100,
            height=780,
            opacity=0.4,
        ),
        Placement(
            ref="pc",
            x=550, y=280,
            height=500,
            opacity=0.4,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. A 1980s computer lab at night. "
        "A young man in a green work shirt sits in a distinctive blue plastic "
        "armchair, typing at a PC. The blue chair stands out in the room."
    ),
    notes="Three overlays: chair at 0.7, hacker+PC at 0.4 (does opacity = attention?)",
))

# --- Multi-step trials ---

# Multi 1: (bg + chair) → then + hacker
multi_trial(MultiTrial(
    name="stepwise-chair-then-hacker",
    background="terminal-room",
    steps=[
        Step(
            name="chair",
            placements=[
                Placement(
                    ref="chair",
                    x=330, y=480,
                    height=420,
                    opacity=0.5,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. Interior of a 1980s computer "
                "lab at night. A distinctive blue plastic armchair sits at one of "
                "the terminal desks. CRT monitors glow in the background."
            ),
        ),
        Step(
            name="hacker",
            placements=[
                Placement(
                    ref="hacker",
                    x=220, y=100,
                    height=780,
                    opacity=0.5,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. A young man in a green work "
                "shirt and jeans sits in the blue armchair, typing furiously at "
                "the terminal. 1980s computer lab at night."
            ),
            seed=43,
        ),
    ],
    notes="Stepwise: integrate chair first, then add hacker on top",
))

# Multi 2: (bg + chair) → then + hacker + PC
multi_trial(MultiTrial(
    name="stepwise-three-element",
    background="terminal-room",
    steps=[
        Step(
            name="chair",
            placements=[
                Placement(
                    ref="chair",
                    x=330, y=480,
                    height=420,
                    opacity=0.5,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. Interior of a 1980s computer "
                "lab at night. A distinctive blue plastic armchair sits at one of "
                "the terminal desks. CRT monitors glow in the background."
            ),
        ),
        Step(
            name="hacker-and-pc",
            placements=[
                Placement(
                    ref="hacker",
                    x=220, y=100,
                    height=780,
                    opacity=0.5,
                ),
                Placement(
                    ref="pc",
                    x=550, y=280,
                    height=500,
                    opacity=0.4,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. A young man in a green work "
                "shirt and jeans sits in the blue armchair, typing at a PC with "
                "a CRT monitor showing garbled characters. 1980s computer lab."
            ),
            seed=43,
        ),
    ],
    notes="Stepwise: chair first, then hacker+PC together",
))

# Multi 3: Three fully separate steps
multi_trial(MultiTrial(
    name="stepwise-all-separate",
    background="terminal-room",
    steps=[
        Step(
            name="chair",
            placements=[
                Placement(
                    ref="chair",
                    x=330, y=480,
                    height=420,
                    opacity=0.5,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. Interior of a 1980s computer "
                "lab at night. A distinctive blue plastic armchair sits at one of "
                "the terminal desks."
            ),
        ),
        Step(
            name="hacker",
            placements=[
                Placement(
                    ref="hacker",
                    x=220, y=100,
                    height=780,
                    opacity=0.5,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. A young man in a green work "
                "shirt and jeans sits in the blue armchair at the terminal, "
                "typing furiously."
            ),
            seed=43,
        ),
        Step(
            name="pc",
            placements=[
                Placement(
                    ref="pc",
                    x=550, y=280,
                    height=500,
                    opacity=0.4,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. The hacker types at a PC "
                "with a CRT monitor showing garbled characters. A blue armchair, "
                "1980s computer lab at night."
            ),
            seed=44,
        ),
    ],
    notes="Fully stepwise: chair → hacker → PC, each integrated separately",
))


# --- Kitchen empty-stage trials ---

# Single-shot: add closed fridge to empty kitchen
trial(Trial(
    name="empty-kitchen-fridge",
    background="kitchen-empty",
    placements=[
        Placement(
            ref="refrigerator",
            x=580, y=80,
            height=780,
            opacity=0.5,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. A dingy institutional kitchen "
        "in a university basement. A refrigerator covered in notes, clippings, "
        "and magnets stands in the corner. Fluorescent lights, stained counter."
    ),
    notes="Empty stage + closed fridge (pure addition)",
))

# Single-shot: add open fridge to empty kitchen
trial(Trial(
    name="empty-kitchen-fridge-open",
    background="kitchen-empty",
    placements=[
        Placement(
            ref="refrigerator-open",
            x=530, y=80,
            height=780,
            opacity=0.5,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. A dingy institutional kitchen. "
        "The refrigerator door is wide open, revealing shelves crammed with "
        "old takeout containers and brown bags. Notes cover the door."
    ),
    notes="Empty stage + open fridge (pure addition, no replacement)",
))

# Single-shot: add microwave to empty kitchen
trial(Trial(
    name="empty-kitchen-microwave",
    background="kitchen-empty",
    placements=[
        Placement(
            ref="microwave",
            x=20, y=320,
            width=300,
            opacity=0.5,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. A dingy institutional kitchen. "
        "A white microwave oven sits on the counter on the left side. "
        "Fluorescent lights, stained countertop."
    ),
    notes="Empty stage + closed microwave (pure addition)",
))

# Stepwise: build up full kitchen from empty stage
multi_trial(MultiTrial(
    name="empty-kitchen-full-build",
    background="kitchen-empty",
    steps=[
        Step(
            name="fridge",
            placements=[
                Placement(
                    ref="refrigerator",
                    x=580, y=80,
                    height=780,
                    opacity=0.5,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. A dingy institutional "
                "kitchen. A refrigerator covered in notes, clippings, and "
                "magnets stands in the corner by the counter."
            ),
        ),
        Step(
            name="microwave",
            placements=[
                Placement(
                    ref="microwave",
                    x=20, y=320,
                    width=300,
                    opacity=0.5,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. A dingy institutional "
                "kitchen with a note-covered refrigerator. A white microwave "
                "oven sits on the counter on the left."
            ),
            seed=43,
        ),
    ],
    notes="Stepwise build from empty: fridge then microwave",
))

# Stepwise: open fridge with carton (from empty stage)
multi_trial(MultiTrial(
    name="empty-kitchen-fridge-carton",
    background="kitchen-empty",
    steps=[
        Step(
            name="open-fridge",
            placements=[
                Placement(
                    ref="refrigerator-open",
                    x=530, y=80,
                    height=780,
                    opacity=0.5,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. A dingy institutional "
                "kitchen. The refrigerator door is wide open, showing shelves "
                "packed with old takeout containers. Notes on the door."
            ),
        ),
        Step(
            name="carton",
            placements=[
                Placement(
                    ref="carton",
                    x=620, y=280,
                    height=180,
                    opacity=0.5,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. The open refrigerator "
                "in a dingy kitchen. A distinctive red and white striped "
                "Chinese takeout carton with an occult symbol sits on a shelf "
                "among the other containers."
            ),
            seed=43,
        ),
    ],
    notes="Empty stage → open fridge → carton inside (pure addition chain)",
))


# --- v2: improved positioning, opacity, and text ---
# Fixes from v1:
#   - Microwave: lowered to sit ON counter surface (~y=400), not floating above it
#   - Fridge: shorter (perspective-corrected), positioned in right corner on floor
#   - Step-2 opacity bumped to 0.7 so model commits to the addition
#   - Text conditioning specifies exact spatial relationships

# v2 single-shot: microwave on counter (fixed position)
# At width=240, visible content spans y_local=67..188, body bottom ~164
# Counter surface at ~y=440. body_bottom on counter: y+164=440 → y=276
trial(Trial(
    name="v2-kitchen-microwave",
    background="kitchen-empty",
    placements=[
        Placement(
            ref="microwave",
            x=30, y=280,
            width=240,
            opacity=0.6,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. A dingy institutional kitchen "
        "in a university basement. A white microwave oven sits on the left "
        "end of the countertop, pushed against the tile backsplash. "
        "Fluorescent lights, stained counter, coffee maker nearby."
    ),
    notes="v2: microwave body bottom aligned to counter surface (y=280)",
))

# v2 single-shot: fridge in right corner (perspective-corrected)
# At height=580, visible content bbox ~(157,43,432,527) → body is 275px wide
# Floor on right side ~y=600. Grounded: y+527=600 → y=73
# Fridge right edge: x+432. Fully visible at x <= 592. Use x=570.
trial(Trial(
    name="v2-kitchen-fridge",
    background="kitchen-empty",
    placements=[
        Placement(
            ref="refrigerator",
            x=570, y=73,
            height=580,
            opacity=0.6,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. A dingy institutional kitchen. "
        "A refrigerator covered in notes, clippings, and magnets stands on "
        "the floor in the far-right corner, next to the end of the counter. "
        "Fluorescent lights, stained countertop."
    ),
    notes="v2: fridge grounded on floor (y=73), fully on canvas (x=570)",
))

# v2 stepwise: fridge then microwave, with corrected positions
multi_trial(MultiTrial(
    name="v2-kitchen-full-build",
    background="kitchen-empty",
    steps=[
        Step(
            name="fridge",
            placements=[
                Placement(
                    ref="refrigerator",
                    x=570, y=73,
                    height=580,
                    opacity=0.6,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. A dingy institutional "
                "kitchen. A refrigerator covered in notes, clippings, and "
                "magnets stands on the floor in the far-right corner of the "
                "room, next to the end of the counter."
            ),
        ),
        Step(
            name="microwave",
            placements=[
                Placement(
                    ref="microwave",
                    x=30, y=280,
                    width=240,
                    opacity=0.7,   # Higher opacity for step 2
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. A dingy institutional "
                "kitchen with a note-covered refrigerator in the right corner. "
                "A white microwave oven sits on the left end of the countertop, "
                "pushed against the tile backsplash."
            ),
            seed=43,
        ),
    ],
    notes="v2: corrected positions, higher step-2 opacity (0.7)",
))

# v2 stepwise: microwave FIRST, then fridge (reverse order to see if it matters)
multi_trial(MultiTrial(
    name="v2-kitchen-micro-first",
    background="kitchen-empty",
    steps=[
        Step(
            name="microwave",
            placements=[
                Placement(
                    ref="microwave",
                    x=30, y=280,
                    width=240,
                    opacity=0.6,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. A dingy institutional "
                "kitchen. A white microwave oven sits on the left end of the "
                "countertop, pushed against the tile backsplash. Fluorescent "
                "lights, stained counter."
            ),
        ),
        Step(
            name="fridge",
            placements=[
                Placement(
                    ref="refrigerator",
                    x=570, y=73,
                    height=580,
                    opacity=0.7,   # Higher opacity for step 2
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. A dingy institutional "
                "kitchen with a microwave on the left counter. A refrigerator "
                "covered in notes and clippings stands on the floor in the "
                "far-right corner, next to the counter."
            ),
            seed=43,
        ),
    ],
    notes="v2: reverse order (microwave first) to test step-order sensitivity",
))

# v2 microwave variations: try different opacity/size/position combos
# to find what makes the microwave solid (not translucent)
for label, mw_y, mw_w, mw_op in [
    ("v2-mw-big-opaque",   280, 300, 0.85),  # Bigger + nearly opaque
    ("v2-mw-lower",        320, 280, 0.8),   # Lower on counter + bigger
    ("v2-mw-max-opacity",  280, 260, 0.95),  # Near-full opacity, medium size
]:
    trial(Trial(
        name=label,
        background="kitchen-empty",
        placements=[
            Placement(
                ref="microwave",
                x=20, y=mw_y,
                width=mw_w,
                opacity=mw_op,
            ),
        ],
        prompt=(
            "Comic book art, bold ink outlines. A dingy institutional kitchen "
            "in a university basement. A white microwave oven sits on the left "
            "end of the countertop, pushed against the tile backsplash. "
            "Fluorescent lights, stained counter, coffee maker nearby."
        ),
        notes=f"microwave variation: y={mw_y} w={mw_w} opacity={mw_op}",
    ))


# --- v2 state matrix: appliance open/closed combinations ---
# Placement constants (derived from bounding box analysis):
#   Fridge closed: x=570, y=63, h=580  (body 286px wide, fits canvas)
#   Fridge open:   x=500, y=49, h=580  (body 431px wide, shifted left to fit)
#   Microwave *:   x=20,  y=280, w=300 (all states same bbox)
# Opacity: 0.85 step-1, 0.9 step-2 (near-full, preserves bg hints)

_FRIDGE_CLOSED = Placement(ref="refrigerator",      x=570, y=63,  height=580, opacity=0.85)
_FRIDGE_OPEN   = Placement(ref="refrigerator-open",  x=500, y=49,  height=580, opacity=0.85)

_MW_CLOSED  = Placement(ref="microwave",         x=20, y=280, width=300, opacity=0.85)
_MW_OPEN    = Placement(ref="microwave-open",     x=20, y=280, width=300, opacity=0.85)
_MW_RUNNING = Placement(ref="microwave-running",  x=20, y=280, width=300, opacity=0.85)

_FRIDGE_CLOSED_S2 = Placement(ref="refrigerator",      x=570, y=63,  height=580, opacity=0.9)
_FRIDGE_OPEN_S2   = Placement(ref="refrigerator-open",  x=500, y=49,  height=580, opacity=0.9)

_MW_CLOSED_S2  = Placement(ref="microwave",         x=20, y=280, width=300, opacity=0.9)
_MW_OPEN_S2    = Placement(ref="microwave-open",     x=20, y=280, width=300, opacity=0.9)
_MW_RUNNING_S2 = Placement(ref="microwave-running",  x=20, y=280, width=300, opacity=0.9)

_states = [
    # (name, fridge_step1, fridge_desc, mw_step2, mw_desc)
    ("v2-states-default",
     _FRIDGE_CLOSED, "A closed refrigerator covered in notes and magnets",
     _MW_CLOSED_S2, "A white microwave oven sits closed"),
    ("v2-states-fridge-open",
     _FRIDGE_OPEN, "The refrigerator door is wide open, revealing shelves of old takeout",
     _MW_CLOSED_S2, "A white microwave oven sits closed"),
    ("v2-states-micro-open",
     _FRIDGE_CLOSED, "A closed refrigerator covered in notes and magnets",
     _MW_OPEN_S2, "The microwave door hangs open, showing the empty turntable inside"),
    ("v2-states-both-open",
     _FRIDGE_OPEN, "The refrigerator door is wide open, revealing shelves of old takeout",
     _MW_OPEN_S2, "The microwave door hangs open, showing the empty turntable inside"),
    ("v2-states-micro-running",
     _FRIDGE_CLOSED, "A closed refrigerator covered in notes and magnets",
     _MW_RUNNING_S2, "The microwave is running, its interior glowing bright yellow-white"),
]

for name, fridge_p, fridge_desc, mw_p, mw_desc in _states:
    multi_trial(MultiTrial(
        name=name,
        background="kitchen-empty",
        steps=[
            Step(
                name="fridge",
                placements=[fridge_p],
                prompt=(
                    f"Comic book art, bold ink outlines. A dingy institutional "
                    f"kitchen. {fridge_desc} stands on the floor in the far-right "
                    f"corner, next to the end of the counter."
                ),
            ),
            Step(
                name="microwave",
                placements=[mw_p],
                prompt=(
                    f"Comic book art, bold ink outlines. A dingy institutional "
                    f"kitchen with a refrigerator in the right corner. "
                    f"{mw_desc} on the left end of the countertop, pushed "
                    f"against the tile backsplash."
                ),
                seed=43,
            ),
        ],
        notes=f"State combo: fridge={'open' if 'open' in fridge_p.ref else 'closed'}, "
              f"microwave={'open' if 'open' in mw_p.ref else 'running' if 'running' in mw_p.ref else 'closed'}",
    ))


# --- v3: minimal text conditioning ---
# Hypothesis: detailed text fights the overlay. Let the spatial prior
# do the heavy lifting, text just sets style + bare-minimum semantics.

_text_levels = {
    # Level 0: style only — let the overlay speak for itself
    "style-only": (
        "Comic book art, bold ink outlines.",
        "Comic book art, bold ink outlines.",
    ),
    # Level 1: style + bare keywords
    "keywords": (
        "Comic book art. Kitchen, {fridge_word}, fluorescent lights.",
        "Comic book art. Kitchen, {fridge_word}, {mw_word}, fluorescent lights.",
    ),
    # Level 2: style + one-sentence spatial hint
    "spatial": (
        "Comic book art. Kitchen with {fridge_word} in the corner.",
        "Comic book art. Kitchen with {fridge_word} in the corner, {mw_word} on the counter.",
    ),
}

_v3_combos = [
    # (suffix, fridge_placement, fridge_word, mw_placement, mw_word)
    ("closed-closed", _FRIDGE_CLOSED, "closed refrigerator", _MW_CLOSED_S2, "microwave"),
    ("fridge-open",   _FRIDGE_OPEN,   "open refrigerator",   _MW_CLOSED_S2, "microwave"),
    ("micro-open",    _FRIDGE_CLOSED, "closed refrigerator", _MW_OPEN_S2,   "open microwave"),
    ("micro-running", _FRIDGE_CLOSED, "closed refrigerator", _MW_RUNNING_S2, "glowing microwave"),
]

for text_level, (step1_tmpl, step2_tmpl) in _text_levels.items():
    for suffix, fridge_p, fridge_word, mw_p, mw_word in _v3_combos:
        name = f"v3-{text_level}-{suffix}"
        step1_prompt = step1_tmpl.format(fridge_word=fridge_word, mw_word=mw_word)
        step2_prompt = step2_tmpl.format(fridge_word=fridge_word, mw_word=mw_word)
        multi_trial(MultiTrial(
            name=name,
            background="kitchen-empty",
            steps=[
                Step(name="fridge", placements=[fridge_p], prompt=step1_prompt),
                Step(name="microwave", placements=[mw_p], prompt=step2_prompt, seed=43),
            ],
            notes=f"v3 {text_level}: {suffix}",
        ))


# --- Kitchen scene trials (original bg with appliances) ---

# Kitchen: basic scene with fridge and microwave at their existing positions
trial(Trial(
    name="kitchen-base",
    background="kitchen",
    placements=[],
    prompt=(
        "Comic book art, bold ink outlines. A dingy institutional kitchen "
        "in a university basement. Fluorescent lights, stained countertop, "
        "a microwave and coffee maker on the counter, a refrigerator covered "
        "in notes and clippings. Late night, slightly creepy."
    ),
    notes="Kitchen baseline - just background + text, no overlays",
))

# Kitchen: open microwave overlaid at the correct position
# The microwave in the bg is at roughly x=80,y=380 at about 200px wide
trial(Trial(
    name="kitchen-microwave-open",
    background="kitchen",
    placements=[
        Placement(
            ref="microwave-open",
            x=30, y=340,
            width=320,
            opacity=0.6,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. A dingy institutional kitchen. "
        "The microwave on the counter is open, its door hanging to the right, "
        "revealing the empty turntable inside. Fluorescent lights overhead."
    ),
    notes="State swap: overlay open microwave over the closed one in bg",
))

# Kitchen: microwave running (glowing)
trial(Trial(
    name="kitchen-microwave-running",
    background="kitchen",
    placements=[
        Placement(
            ref="microwave-running",
            x=30, y=340,
            width=320,
            opacity=0.6,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. A dingy institutional kitchen. "
        "The microwave on the counter is running, its interior glowing bright "
        "yellow-white, timer counting down. Fluorescent lights overhead."
    ),
    notes="State swap: overlay running microwave over the closed one",
))

# Kitchen stepwise: open fridge, then put carton inside
multi_trial(MultiTrial(
    name="kitchen-fridge-carton",
    background="kitchen",
    steps=[
        Step(
            name="open-fridge",
            placements=[
                Placement(
                    ref="refrigerator-open",
                    x=560, y=100,
                    height=750,
                    opacity=0.6,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. A dingy institutional "
                "kitchen. The refrigerator door is wide open, revealing "
                "shelves packed with old takeout containers and brown bags. "
                "Notes and clippings cover the fridge door."
            ),
        ),
        Step(
            name="carton-in-fridge",
            placements=[
                Placement(
                    ref="carton",
                    x=640, y=320,
                    height=180,
                    opacity=0.5,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. The open refrigerator "
                "in a dingy kitchen. A red and white striped Chinese takeout "
                "carton with an occult symbol sits on one of the shelves "
                "among the other containers."
            ),
            seed=43,
        ),
    ],
    notes="Stepwise: open fridge, then place the carton inside it",
))

# Kitchen stepwise: full scene - open microwave, then carton on counter
multi_trial(MultiTrial(
    name="kitchen-carton-in-microwave",
    background="kitchen",
    steps=[
        Step(
            name="open-microwave",
            placements=[
                Placement(
                    ref="microwave-open",
                    x=30, y=340,
                    width=320,
                    opacity=0.6,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. A dingy institutional "
                "kitchen. The microwave on the counter stands open, door "
                "hanging to the right, empty turntable visible inside."
            ),
        ),
        Step(
            name="carton-in-microwave",
            placements=[
                Placement(
                    ref="carton",
                    x=100, y=380,
                    height=130,
                    opacity=0.5,
                ),
            ],
            prompt=(
                "Comic book art, bold ink outlines. A dingy institutional "
                "kitchen. A red and white striped Chinese takeout carton "
                "with an occult symbol sits inside the open microwave."
            ),
            seed=43,
        ),
    ],
    notes="Stepwise: open microwave, then place carton inside it",
))


# Trial 5: Flipped hacker facing the other direction
trial(Trial(
    name="hacker-flipped",
    background="terminal-room",
    placements=[
        Placement(
            ref="hacker",
            x=380, y=180,
            height=700,
            opacity=0.5,
            flip=True,
        ),
    ],
    prompt=(
        "Comic book art, bold ink outlines. Interior of a 1980s computer lab "
        "at night. A young man in a green work shirt and jeans sits typing "
        "at a terminal on the right side of the room."
    ),
    notes="Flipped orientation - does it respect facing direction?",
))


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate_from_overlay(overlay: Image.Image, prompt: str, seed: int = 42) -> Image.Image:
    """Feed the overlay composite to NanoBanana as a single reference."""
    from filfre.cli import generate_image_nanobanana

    # Convert RGBA overlay to RGB for the model
    rgb_overlay = Image.new("RGB", overlay.size, (255, 255, 255))
    rgb_overlay.paste(overlay, mask=overlay.split()[3])

    return generate_image_nanobanana(
        prompt=prompt,
        reference_images=[rgb_overlay],
        aspect_ratio="1:1",
        seed=seed,
    )


def generate_baseline(trial: Trial, seed: int = 42) -> Image.Image:
    """Generate using separate references (current approach) for comparison."""
    from filfre.cli import generate_image_nanobanana

    refs = [load_ref(trial.background).convert("RGB")]
    for p in trial.placements:
        refs.append(load_ref(p.ref).convert("RGB"))

    return generate_image_nanobanana(
        prompt=trial.prompt,
        reference_images=refs,
        aspect_ratio="1:1",
        seed=seed,
    )


def run_trial(trial: Trial, baseline: bool = False, build_only: bool = False):
    """Run a single trial: build overlay, generate, save results."""
    print(f"\n{'='*60}")
    print(f"Trial: {trial.name}")
    print(f"  {trial.notes}")
    print(f"  Placements: {len(trial.placements)}")
    print(f"  Prompt: {trial.prompt[:80]}...")
    print(f"{'='*60}")

    trial_dir = OUTPUT / trial.name
    trial_dir.mkdir(parents=True, exist_ok=True)

    # Build overlay
    print("\n  Building overlay...")
    overlay = build_overlay(trial)
    overlay_path = trial_dir / "overlay.png"
    overlay.save(str(overlay_path))
    print(f"  Saved: {overlay_path}")

    # Also save the overlay flattened to RGB for inspection
    flat = Image.new("RGB", overlay.size, (128, 128, 128))  # grey bg to see transparency
    flat.paste(overlay, mask=overlay.split()[3])
    flat_path = trial_dir / "overlay-flat.png"
    flat.save(str(flat_path))

    if build_only:
        print("  (build-only mode, skipping generation)")
        return

    # Generate from overlay
    print("\n  Generating from overlay...")
    start = time.time()
    result = generate_from_overlay(overlay, trial.prompt)
    elapsed = time.time() - start
    result_path = trial_dir / "result-overlay.png"
    result.save(str(result_path))
    print(f"  Generated in {elapsed:.1f}s → {result_path}")

    # Baseline comparison
    if baseline:
        print("\n  Generating baseline (separate refs)...")
        start = time.time()
        base_result = generate_baseline(trial)
        elapsed = time.time() - start
        base_path = trial_dir / "result-baseline.png"
        base_result.save(str(base_path))
        print(f"  Generated in {elapsed:.1f}s → {base_path}")

    # Save trial metadata
    meta = {
        "name": trial.name,
        "prompt": trial.prompt,
        "notes": trial.notes,
        "placements": [
            {
                "ref": p.ref,
                "x": p.x, "y": p.y,
                "height": p.height, "width": p.width,
                "opacity": p.opacity,
                "flip": p.flip,
            }
            for p in trial.placements
        ],
    }
    meta_path = trial_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Transparent overlay composition experiment")
    parser.add_argument("--trial", help="Run specific trial by name")
    parser.add_argument("--build-only", action="store_true", help="Only build overlays")
    parser.add_argument("--baseline", action="store_true", help="Also generate baseline")
    parser.add_argument("--list", action="store_true", help="List available trials")
    args = parser.parse_args()

    OUTPUT.mkdir(parents=True, exist_ok=True)

    if args.list:
        print("  Single-shot trials:")
        for name, t in TRIALS.items():
            placements = ", ".join(f"{p.ref}@{p.opacity}" for p in t.placements)
            print(f"    {name:30s} [{placements}]  {t.notes}")
        print("  Multi-step trials:")
        for name, mt in MULTI_TRIALS.items():
            steps = " → ".join(s.name for s in mt.steps)
            print(f"    {name:30s} [{steps}]  {mt.notes}")
        return

    all_names = {**TRIALS, **MULTI_TRIALS}
    if args.trial:
        if args.trial not in all_names:
            print(f"Unknown trial: {args.trial}")
            print(f"Available: {', '.join(all_names.keys())}")
            return

        if args.trial in MULTI_TRIALS:
            run_multi_trial(MULTI_TRIALS[args.trial], build_only=args.build_only)
        else:
            run_trial(TRIALS[args.trial], baseline=args.baseline, build_only=args.build_only)
    else:
        for name, t in TRIALS.items():
            run_trial(t, baseline=args.baseline, build_only=args.build_only)
        for name, mt in MULTI_TRIALS.items():
            run_multi_trial(mt, build_only=args.build_only)

    print(f"\nDone. Results in {OUTPUT}/")


if __name__ == "__main__":
    main()
