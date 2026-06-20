#!/usr/bin/env python3
"""
CLI for image generation.

Uses the NanoBanana (Google Gemini 2.5 Flash Image) cloud backend. Requires a
``GEMINI_API_KEY`` (or ``GOOGLE_API_KEY``) environment variable.

Subcommands:
    brief     Emit per-key generation briefs from a game's render manifest
              (printable for a human artist, or written as <key>.txt files)
    fill      Generate a game's keyed assets from its render manifest
    generate  Generate a single image from a direct text prompt

Usage:
    # Manifest-driven (the static pre-generation pipeline)
    filfre brief games/lurkinghorror
    filfre fill games/lurkinghorror --dry-run

    # Direct generation
    filfre generate --prompt "A dragon in a cave" --output dragon.png
"""

import argparse
import sys
import time
from pathlib import Path


def timed(label: str):
    """Context manager for timing code blocks."""

    class Timer:
        def __init__(self, label):
            self.label = label

        def __enter__(self):
            self.start = time.time()
            return self

        def __exit__(self, *args):
            elapsed = time.time() - self.start
            print(f"  [{self.label}] {elapsed:.2f}s")

    return Timer(label)


def load_reference_images(
    image_paths: list[str],
    size: int | None = None,
):
    """Load and preprocess reference images.

    Args:
        image_paths: List of paths to reference images.
        size: Optional size to resize images to (square).

    Returns:
        List of PIL Images.
    """
    from PIL import Image, ImageOps

    images = []
    for path in image_paths:
        img = Image.open(path).convert("RGB")
        img = ImageOps.exif_transpose(img)  # Handle EXIF orientation
        if size:
            img = img.resize((size, size))
        images.append(img)
    return images


# Gemini model ID for NanoBanana Pro
NANOBANANA_MODEL_ID = "gemini-3-pro-image-preview"  # "gemini-2.5-flash-image"


def generate_image_nanobanana(
    prompt: str,
    reference_images=None,
    aspect_ratio: str = "1:1",
    seed: int = 0,
):
    """Generate an image using Google's NanoBanana (Gemini 2.5 Flash Image).

    Requires GEMINI_API_KEY or GOOGLE_API_KEY environment variable.

    Args:
        prompt: Text prompt describing the image.
        reference_images: Optional list of PIL Images for guided generation.
        aspect_ratio: Output aspect ratio (default "1:1").
        seed: Random seed (used in prompt for reproducibility hint).

    Returns:
        Generated PIL Image.
    """
    from google import genai
    from google.genai import types

    client = genai.Client()

    # Build contents: prompt text + optional reference images
    contents = []
    if reference_images:
        contents.append(
            f"Generate an image based on the following description, using the "
            f"provided reference images for visual consistency and composition. "
            f"Seed: {seed}.\n\n{prompt}"
        )
        for img in reference_images:
            contents.append(img)
    else:
        contents.append(f"{prompt}")

    response = client.models.generate_content(
        model=NANOBANANA_MODEL_ID,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
            ),
        ),
    )

    # Extract the generated image from response parts
    for part in response.parts:
        if part.inline_data is not None:
            return part.as_image()

    raise RuntimeError(
        f"NanoBanana returned no image. Response: {response.text if hasattr(response, 'text') else response}"
    )


# Image formats tried (in order) when resolving an extension-less asset key.
SUPPORTED_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def _assets_dir(game_path: Path) -> Path:
    """Locate the assets directory for a game path (dir or entrypoint file)."""
    base = game_path if game_path.is_dir() else game_path.parent
    return base / "assets"


def _existing_asset(assets: Path, key: str) -> Path | None:
    """Find the on-disk file for an extension-less asset key, or None."""
    if (assets / key).is_file():  # literal key already carrying an extension
        return assets / key
    for ext in SUPPORTED_IMAGE_EXTS:
        if (assets / f"{key}{ext}").is_file():
            return assets / f"{key}{ext}"
    return None


def _load_manifest(game: str):
    """Load a game world and build its render manifest + shared style.

    Returns (world, manifest_entries, style_str). Exits via SystemExit on error.
    """
    from grue import load_grue
    from grue.render import assemble_style, build_render_manifest

    game_path = Path(game)
    if not game_path.exists():
        print(f"Error: {game_path} not found", file=sys.stderr)
        raise SystemExit(1)
    try:
        world = load_grue(str(game_path))
    except Exception as e:
        print(f"Error loading game: {e}", file=sys.stderr)
        raise SystemExit(1)
    manifest = build_render_manifest(world)
    style = assemble_style(getattr(world, "visual_style", None))
    return world, manifest, style


# =============================================================================
# Subcommand: generate
# =============================================================================


def cmd_generate(args):
    """Generate an image from a text prompt via NanoBanana."""
    # Load reference images if provided
    reference_images = None
    if args.references:
        print(f"Loading {len(args.references)} reference image(s)...")
        reference_images = load_reference_images(args.references)

    print("=" * 60)
    print(f"Output: {args.output}")
    print(f"Aspect ratio: {args.aspect_ratio}")
    print(f"Seed: {args.seed}")
    if reference_images:
        print(f"References: {len(reference_images)} image(s)")
    print("=" * 60)
    print(f"\nPrompt:\n{args.prompt[:200]}{'...' if len(args.prompt) > 200 else ''}\n")
    print("=" * 60)

    total_start = time.time()

    print(f"\n--- Generating {args.count} image(s) via NanoBanana ---")
    gen_times = []
    image = None

    for i in range(args.count):
        seed = args.seed + i
        start = time.time()

        image = generate_image_nanobanana(
            prompt=args.prompt,
            reference_images=reference_images,
            aspect_ratio=args.aspect_ratio,
            seed=seed,
        )

        elapsed = time.time() - start
        gen_times.append(elapsed)
        print(f"  [image {i + 1}] {elapsed:.2f}s (seed={seed})")

    if args.count > 1:
        avg = sum(gen_times) / len(gen_times)
        print(f"  [average] {avg:.2f}s")

    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    print(f"\nSaved to {output_path}")
    print(f"Total wall time: {time.time() - total_start:.2f}s")

    # Display in terminal if supported
    try:
        from gnusto.terminal_images import display_image, is_supported

        if is_supported():
            print()
            display_image(output_path, width=60)
    except ImportError:
        pass


# =============================================================================
# Subcommand: brief
# =============================================================================


def cmd_brief(args):
    """Emit per-key generation briefs from a game's render manifest.

    The same keyset a frontier model would fill, packaged for a human artist:
    one brief per asset key, each = the shared visual-style preamble + the
    entity's :rdesc. Print to stdout, or write ``<key>.txt`` files with ``--out``.
    """
    from grue.render import assemble_brief

    world, manifest, _style = _load_manifest(args.game)
    visual_style = getattr(world, "visual_style", None)
    if args.key:
        wanted = set(args.key)
        manifest = [e for e in manifest if e.key in wanted]
        missing = wanted - {e.key for e in manifest}
        for k in sorted(missing):
            print(f"Warning: no render key '{k}'", file=sys.stderr)

    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        for e in manifest:
            prompt = assemble_brief(visual_style, e.brief, e.kind)
            (out_dir / f"{e.key}.txt").write_text(prompt + "\n")
        print(f"Wrote {len(manifest)} brief(s) to {out_dir}/")
        return

    # The style preamble is now kind-specific (rooms vs objects differ), so show
    # the full composed prompt per key rather than one hoisted header.
    for e in manifest:
        variant = f" [{e.variant}]" if e.variant else ""
        print(f"{e.key}  ({e.entity}{variant})")
        print(f"  {assemble_brief(visual_style, e.brief, e.kind)}\n")


# =============================================================================
# Subcommand: fill
# =============================================================================


def cmd_fill(args):
    """Generate the game's keyed assets from its render manifest via NanoBanana.

    Each entry's full prompt (shared style + entity :rdesc) is sent to the
    model and the result saved as ``assets/<key>.jpg``. By default only keys
    missing on disk are generated; ``--force`` regenerates, ``--key`` targets
    specific keys. Honors the single-subject discipline already encoded in the
    briefs (rooms = empty stages, objects = single subjects).
    """
    from grue.render import assemble_brief, render_aspect

    world, manifest, style = _load_manifest(args.game)
    assets = _assets_dir(Path(args.game))
    visual_style = getattr(world, "visual_style", None)

    def aspect_for(entry) -> str:
        # An explicit --aspect-ratio forces every key; otherwise resolve per the
        # entity's kind (rooms may breathe wide, objects stay square).
        return args.aspect_ratio or render_aspect(visual_style, entry.kind)

    if args.key:
        wanted = set(args.key)
        manifest = [e for e in manifest if e.key in wanted]
        for k in sorted(wanted - {e.key for e in manifest}):
            print(f"Warning: no render key '{k}'", file=sys.stderr)

    # Decide what to (re)generate.
    todo = []
    skipped = 0
    for e in manifest:
        existing = _existing_asset(assets, e.key)
        if existing and not args.force:
            skipped += 1
            continue
        todo.append((e, existing))

    print(f"Game: {world.name or args.game}")
    print(f"Assets: {assets}")
    print(f"Aspect ratio: per kind ({args.aspect_ratio or 'from :visual-style'})")
    print(f"To generate: {len(todo)}  (skipping {skipped} already on disk)\n")

    if args.dry_run:
        for e, _ in todo:
            print(f"{e.key}.jpg  [{aspect_for(e)}]")
            print(f"  {assemble_brief(visual_style, e.brief, e.kind)}\n")
        return

    if not todo:
        return

    from io import BytesIO

    from PIL import Image as PILImage

    assets.mkdir(parents=True, exist_ok=True)
    for i, (e, existing) in enumerate(todo, 1):
        prompt = assemble_brief(visual_style, e.brief, e.kind)
        entry_aspect = aspect_for(e)
        print(f"[{i}/{len(todo)}] {e.key} ({entry_aspect}) ...", flush=True)
        start = time.time()
        image = generate_image_nanobanana(
            prompt=prompt, aspect_ratio=entry_aspect, seed=args.seed
        )
        # The backend returns a genai types.Image; decode its bytes to a PIL
        # image, normalize to RGB, and write JPG (the contract: JPG everywhere,
        # no alpha).
        pil = PILImage.open(BytesIO(image.image_bytes)).convert("RGB")
        # Remove any pre-existing file under a different extension to avoid
        # ambiguous duplicate keys on disk.
        if existing and existing.suffix.lower() != ".jpg":
            existing.unlink()
        out_path = assets / f"{e.key}.jpg"
        pil.save(out_path, quality=90)
        print(f"      saved {out_path} ({time.time() - start:.1f}s)")

    print(f"\nGenerated {len(todo)} image(s).")


# =============================================================================
# Main entry point
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Generate illustrations via NanoBanana (Gemini 2.5 Flash Image)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ---------------------------------------------------------------------
    # generate subcommand
    # ---------------------------------------------------------------------
    gen_parser = subparsers.add_parser(
        "generate",
        aliases=["gen"],
        help="Generate an image from a text prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  filfre generate --prompt "A dragon in a cave" --output dragon.png

  # With reference images for composition:
  filfre generate --prompt "A brass lantern on a stone altar" \\
      --reference lantern.png --output scene.png
        """,
    )
    gen_parser.add_argument(
        "--prompt",
        "-p",
        type=str,
        required=True,
        help="Text prompt describing the image to generate",
    )
    gen_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="output.png",
        help="Output filename (default: output.png)",
    )
    gen_parser.add_argument(
        "--aspect-ratio",
        type=str,
        default="1:1",
        help="Output aspect ratio (default: 1:1)",
    )
    gen_parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for reproducibility (default: 0)",
    )
    gen_parser.add_argument(
        "--reference",
        "-r",
        type=str,
        action="append",
        dest="references",
        metavar="IMAGE",
        help="Reference image for composition (can be used multiple times)",
    )
    gen_parser.add_argument(
        "--count",
        "-n",
        type=int,
        default=1,
        help="Number of images to generate (for timing analysis)",
    )
    gen_parser.set_defaults(func=cmd_generate)

    # ---------------------------------------------------------------------
    # brief subcommand
    # ---------------------------------------------------------------------
    brief_parser = subparsers.add_parser(
        "brief",
        help="Emit per-key generation briefs from a game's render manifest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Print every brief (shared style shown once at the top)
  filfre brief games/lurkinghorror

  # Write one <key>.txt per asset for a human artist to fill
  filfre brief games/lurkinghorror --out briefs/

  # Just a couple of keys
  filfre brief games/lurkinghorror --key microwave-open --key kitchen
        """,
    )
    brief_parser.add_argument("game", help="Path to game directory or .grue file")
    brief_parser.add_argument(
        "--out",
        type=str,
        help="Write one <key>.txt brief per asset into this directory",
    )
    brief_parser.add_argument(
        "--key",
        action="append",
        metavar="KEY",
        help="Limit to specific asset key(s) (repeatable)",
    )
    brief_parser.set_defaults(func=cmd_brief)

    # ---------------------------------------------------------------------
    # fill subcommand
    # ---------------------------------------------------------------------
    fill_parser = subparsers.add_parser(
        "fill",
        help="Generate a game's keyed assets from its render manifest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Generate only the assets missing on disk
  filfre fill games/lurkinghorror

  # Preview prompts without calling the model
  filfre fill games/lurkinghorror --dry-run

  # Regenerate a specific key
  filfre fill games/lurkinghorror --key microwave-open --force
        """,
    )
    fill_parser.add_argument("game", help="Path to game directory or .grue file")
    fill_parser.add_argument(
        "--key",
        action="append",
        metavar="KEY",
        help="Limit to specific asset key(s) (repeatable)",
    )
    fill_parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate keys even if an asset already exists on disk",
    )
    fill_parser.add_argument(
        "--aspect-ratio",
        type=str,
        default=None,
        help="Override the world :visual-style aspect ratio",
    )
    fill_parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed (default: 0)",
    )
    fill_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be generated, with prompts, without calling the model",
    )
    fill_parser.set_defaults(func=cmd_fill)

    # ---------------------------------------------------------------------
    # Parse and dispatch
    # ---------------------------------------------------------------------
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
