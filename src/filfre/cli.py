#!/usr/bin/env python3
"""
CLI for image generation.

Uses the NanoBanana (Google Gemini 2.5 Flash Image) cloud backend. Requires a
``GEMINI_API_KEY`` (or ``GOOGLE_API_KEY``) environment variable.

Usage:
    # Direct generation
    filfre generate --prompt "A dragon in a cave" --output dragon.png

    # With reference images for composition
    filfre generate --prompt "A brass lantern on a stone altar" \
        --reference lantern.png --output scene.png
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


# Gemini model ID for NanoBanana
NANOBANANA_MODEL_ID = "gemini-2.5-flash-image"


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
    # Parse and dispatch
    # ---------------------------------------------------------------------
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
