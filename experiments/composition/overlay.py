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
