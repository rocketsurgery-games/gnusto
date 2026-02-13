#!/usr/bin/env python3
"""Compose images for layout experiment scenarios using filfre.

Reads scenario JSON files and generates composed images:
  - Scene headers: room + characters + key objects → full scene illustration
  - Focus panels: entity close-ups in context
  - Moment illustrations: specific narrative beats

Uses NanoBanana (Gemini 2.5 Flash Image) backend via filfre API.
Generated images are written to assets/composed/ (gitignored).

Usage:
    python compose.py                          # Compose all scenarios
    python compose.py room-entry               # Compose one scenario
    python compose.py room-entry --only scene  # Just the scene header
    python compose.py --list                   # Show what would be generated
"""

import argparse
import json
import time
from pathlib import Path

from PIL import Image, ImageOps

# filfre API
from filfre.cli import generate_image_nanobanana

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
ASSETS_DIR = Path(__file__).parent / "assets"
COMPOSED_DIR = ASSETS_DIR / "composed"

# Comic book art style prefix for all prompts
STYLE = (
    "Comic book art style, bold ink outlines, flat cel-shading, "
    "muted color palette with dramatic lighting. "
)


def load_scenario(name: str) -> dict:
    path = SCENARIOS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Scenario not found: {path}")
    return json.loads(path.read_text())


def load_ref(path_str: str, max_size: int = 512) -> Image.Image | None:
    """Load a reference image, resolving relative to assets dir."""
    path = ASSETS_DIR / path_str.removeprefix("assets/")
    if not path.exists():
        print(f"  [skip ref] {path} not found")
        return None
    img: Image.Image = Image.open(path).convert("RGB")
    transposed = ImageOps.exif_transpose(img)
    if transposed is not None:
        img = transposed
    # Resize to keep things manageable
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size))
    return img


def collect_refs(scene: dict) -> list[Image.Image]:
    """Collect all available reference images from a scene."""
    refs = []

    # Room background
    if scene.get("room_image"):
        img = load_ref(scene["room_image"])
        if img:
            refs.append(img)

    # Character images
    for char in scene.get("characters", []):
        if char.get("image"):
            img = load_ref(char["image"])
            if img:
                refs.append(img)

    # Object images (limit to first 3 to avoid overwhelming the model)
    for obj in scene.get("objects", [])[:3]:
        if obj.get("image"):
            img = load_ref(obj["image"])
            if img:
                refs.append(img)

    return refs


def compose_scene_header(scenario: dict, name: str) -> Path | None:
    """Compose a scene overview image for the scene header.

    Combines room description + character/object context into a single
    atmospheric illustration.
    """
    scene = scenario.get("scene", {})
    blocks = scenario.get("blocks", [])

    # Get the richest description available
    scene_block = next((b for b in blocks if b["type"] == "scene"), None)
    description = (
        scene_block["description"]
        if scene_block
        else scene.get("room_description", "")
    )
    if not description:
        print(f"  [skip] no description for scene header")
        return None

    # Build prompt
    room_name = scene.get("room_name", "a room")
    characters = ", ".join(c["name"] for c in scene.get("characters", []))
    objects = ", ".join(o["name"] for o in scene.get("objects", [])[:3])

    prompt_parts = [STYLE, f"Wide establishing shot of {room_name}. {description}"]
    if characters:
        prompt_parts.append(f"Present: {characters}.")
    if objects:
        prompt_parts.append(f"Visible: {objects}.")

    prompt = " ".join(prompt_parts)

    # Collect reference images
    refs = collect_refs(scene)
    ref_info = f" with {len(refs)} refs" if refs else ""

    print(f"  [scene] {room_name}{ref_info}")
    print(f"    prompt: {prompt[:120]}...")

    start = time.time()
    image = generate_image_nanobanana(
        prompt=prompt,
        reference_images=refs if refs else None,
        aspect_ratio="16:9",  # wide for scene header
        seed=42,
    )
    elapsed = time.time() - start
    print(f"    generated in {elapsed:.1f}s")

    out_path = COMPOSED_DIR / f"{name}-scene.png"
    image.save(str(out_path))
    return out_path


def compose_focus(
    scenario: dict, name: str, block: dict, index: int
) -> Path | None:
    """Compose a focus panel image — entity close-up in context."""
    scene = scenario.get("scene", {})
    entity_id = block.get("entity")
    text = block.get("text", "")

    if not text:
        return None

    # Find entity info
    entity_name = entity_id.replace("@", "") if entity_id else "detail"
    char = next(
        (c for c in scene.get("characters", []) if c.get("id") == entity_id), None
    )
    obj = next(
        (o for o in scene.get("objects", []) if o.get("id") == entity_id), None
    )

    display_name = (char or obj or {}).get("name", entity_name)

    # Build prompt: focus on this entity with the descriptive text
    prompt = f"{STYLE}Close-up panel focusing on {display_name}. {text}"

    # Collect refs: prioritize the entity's own image, then room for context
    refs = []
    entity_image_path = block.get("image") or (char or obj or {}).get("image")
    if entity_image_path:
        img = load_ref(entity_image_path)
        if img:
            refs.append(img)

    # Add room background for context
    if scene.get("room_image"):
        img = load_ref(scene["room_image"])
        if img:
            refs.append(img)

    ref_info = f" with {len(refs)} refs" if refs else ""
    print(f"  [focus:{index}] {display_name}{ref_info}")

    start = time.time()
    image = generate_image_nanobanana(
        prompt=prompt,
        reference_images=refs if refs else None,
        aspect_ratio="1:1",
        seed=42 + index,
    )
    elapsed = time.time() - start
    print(f"    generated in {elapsed:.1f}s")

    out_path = COMPOSED_DIR / f"{name}-focus-{index}-{entity_name}.png"
    image.save(str(out_path))
    return out_path


def compose_moment(
    scenario: dict, name: str, block: dict, index: int
) -> Path | None:
    """Compose an illustration for a dramatic narrative moment."""
    scene = scenario.get("scene", {})
    text = block.get("text", "")
    block_type = block.get("type")

    if not text:
        return None

    # Build prompt based on block type
    if block_type == "reveal":
        prompt = f"{STYLE}Dramatic reveal panel. {text}"
    elif block_type == "speak":
        speaker_id = block.get("speaker")
        char = next(
            (c for c in scene.get("characters", []) if c.get("id") == speaker_id),
            None,
        )
        speaker_name = (char or {}).get("name", speaker_id)
        manner = block.get("manner", "")
        manner_text = f", {manner}" if manner else ""
        prompt = (
            f"{STYLE}Character panel: {speaker_name} speaking{manner_text}. "
            f'Says: "{text}"'
        )
    else:
        prompt = f"{STYLE}Narrative panel. {text}"

    # Collect scene refs
    refs = collect_refs(scene)
    ref_info = f" with {len(refs)} refs" if refs else ""
    print(f"  [moment:{index}] {block_type}{ref_info}")

    start = time.time()
    image = generate_image_nanobanana(
        prompt=prompt,
        reference_images=refs if refs else None,
        aspect_ratio="3:4",  # portrait for panels
        seed=100 + index,
    )
    elapsed = time.time() - start
    print(f"    generated in {elapsed:.1f}s")

    out_path = COMPOSED_DIR / f"{name}-moment-{index}.png"
    image.save(str(out_path))
    return out_path


def plan_compositions(scenario: dict, name: str) -> list[dict]:
    """Plan what compositions to generate for a scenario."""
    blocks = scenario.get("blocks", [])
    plan = []

    # Always compose a scene header
    plan.append({"type": "scene", "name": name})

    # Compose focus blocks that have images or entities
    for i, block in enumerate(blocks):
        if block.get("type") == "focus":
            plan.append({"type": "focus", "name": name, "block": block, "index": i})

    # Pick the most dramatic moments for illustration
    # (reveal blocks, climactic narrate blocks, first speak with manner)
    for i, block in enumerate(blocks):
        if block.get("type") == "reveal":
            plan.append({"type": "moment", "name": name, "block": block, "index": i})

    return plan


def compose_scenario(scenario: dict, name: str, only: str | None = None):
    """Generate all compositions for a scenario."""
    plan = plan_compositions(scenario, name)

    if only:
        plan = [p for p in plan if p["type"] == only]

    if not plan:
        print(f"  nothing to compose")
        return

    results = {}
    for item in plan:
        if item["type"] == "scene":
            path = compose_scene_header(scenario, name)
            if path:
                results["scene"] = str(path.relative_to(ASSETS_DIR.parent))
        elif item["type"] == "focus":
            path = compose_focus(scenario, name, item["block"], item["index"])
            if path:
                results[f"focus-{item['index']}"] = str(
                    path.relative_to(ASSETS_DIR.parent)
                )
        elif item["type"] == "moment":
            path = compose_moment(scenario, name, item["block"], item["index"])
            if path:
                results[f"moment-{item['index']}"] = str(
                    path.relative_to(ASSETS_DIR.parent)
                )

    # Merge with existing manifest (don't clobber previous runs)
    manifest_path = COMPOSED_DIR / f"{name}.json"
    existing = {}
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text())
    existing.update(results)
    manifest_path.write_text(json.dumps(existing, indent=2) + "\n")
    print(f"  manifest: {manifest_path.relative_to(Path(__file__).parent)}")


def main():
    parser = argparse.ArgumentParser(description="Compose images for layout scenarios")
    parser.add_argument("scenario", nargs="?", help="Scenario name (omit for all)")
    parser.add_argument("--only", choices=["scene", "focus", "moment"])
    parser.add_argument("--list", action="store_true", help="Show plan without generating")
    args = parser.parse_args()

    # Ensure output directory exists
    COMPOSED_DIR.mkdir(parents=True, exist_ok=True)

    # Find scenarios
    if args.scenario:
        names = [args.scenario]
    else:
        names = sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))

    for name in names:
        print(f"\n=== {name} ===")
        scenario = load_scenario(name)

        if args.list:
            plan = plan_compositions(scenario, name)
            for item in plan:
                print(f"  [{item['type']}] {item.get('block', {}).get('entity', '')}")
        else:
            compose_scenario(scenario, name, only=args.only)

    print("\nDone.")


if __name__ == "__main__":
    main()
