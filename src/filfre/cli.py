#!/usr/bin/env python3
"""
CLI for image generation and game asset management.

Supports multiple backends:
  - flux: FLUX.2 Klein 4B (local, requires CUDA GPU)
  - nanobanana: Google Gemini 2.5 Flash Image (cloud API, requires GEMINI_API_KEY)

Usage:
    # Direct generation
    filfre generate --model nanobanana --prompt "A dragon in a cave" --output dragon.png

    # With reference images
    filfre generate --model flux --prompt "A brass lantern on a stone altar" \
        --reference lantern.png --output scene.png

    # List renders in cache
    filfre list games/lurkinghorror

    # Show render log
    filfre log games/lurkinghorror
"""

import argparse
import sys
import time
from pathlib import Path


def get_game_dirs(game_path: str | Path) -> tuple[Path, Path, Path]:
    """Get standard directories for a game.

    Args:
        game_path: Path to game directory or .grue file

    Returns:
        Tuple of (game_dir, renders_dir, assets_dir)
    """
    game_dir = Path(game_path)
    if game_dir.is_file():
        game_dir = game_dir.parent
    renders_dir = game_dir / "assets" / "renders"
    assets_dir = game_dir / "assets"
    return game_dir, renders_dir, assets_dir


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


def clone_parameters_in_place(module):
    """Clone all parameters in-place to break mmap links.

    After loading from safetensors, parameters are mmap'd and transfer
    to CUDA ~100x slower than regular tensors. This clones them in-place
    to enable fast CUDA transfer.
    """
    for name, param in module.named_parameters():
        param.data = param.data.clone()
    for name, buf in module.named_buffers():
        buf.data = buf.data.clone()


def get_pipeline(dtype: str = "bf16", verbose: bool = False, quiet: bool = False):
    """Load the FLUX.2 Klein pipeline.

    Args:
        dtype: Data type for model weights ("bf16", "fp16", or "fp32").
        verbose: If True, print detailed timing information.
        quiet: If True, suppress all output (for embedding in TUI).

    Returns:
        Tuple of (pipeline, device).
    """
    import torch
    from diffusers import Flux2KleinPipeline

    # Determine device
    if torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
        if not quiet:
            print("WARNING: No CUDA GPU detected. Running on CPU will be slow.")

    # Determine weight dtype
    if device == "cpu":
        weight_dtype = torch.float32
        if not quiet:
            print("NOTE: Using float32 on CPU")
    elif dtype == "fp16":
        weight_dtype = torch.float16
    elif dtype == "bf16":
        weight_dtype = torch.bfloat16
    else:
        weight_dtype = torch.float32

    if not quiet:
        print(f"Loading FLUX.2 Klein 4B...")
        print(f"Device: {device}, dtype: {weight_dtype}")

    # Load pipeline to CPU first
    if not quiet:
        with timed("from_pretrained (CPU)"):
            pipeline = Flux2KleinPipeline.from_pretrained(
                "black-forest-labs/FLUX.2-klein-4B",
                torch_dtype=weight_dtype,
            )
    else:
        pipeline = Flux2KleinPipeline.from_pretrained(
            "black-forest-labs/FLUX.2-klein-4B",
            torch_dtype=weight_dtype,
        )

    if device == "cuda":
        # Fast CUDA transfer: clone parameters first to break mmap links
        # mmap'd tensors transfer to CUDA ~100x slower than regular tensors
        if not quiet:
            with timed("clone parameters"):
                for name, component in pipeline.components.items():
                    if hasattr(component, 'parameters'):
                        clone_parameters_in_place(component)

            with timed("pipeline.to(cuda)"):
                pipeline = pipeline.to(device)
                torch.cuda.synchronize()
        else:
            for name, component in pipeline.components.items():
                if hasattr(component, 'parameters'):
                    clone_parameters_in_place(component)
            pipeline = pipeline.to(device)
            torch.cuda.synchronize()

    if verbose and not quiet:
        with timed("torch.cuda.synchronize"):
            torch.cuda.synchronize()

    return pipeline, device


def load_reference_images(
    image_paths: list[str],
    size: int | None = None,
):
    """Load and preprocess reference images.

    Args:
        image_paths: List of paths to reference images.
        size: Optional size to resize images to (square).

    Returns:
        List of PIL Images ready for use with FLUX.2.
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


def generate_image(
    pipeline,
    device: str,
    prompt: str,
    reference_images=None,
    width: int = 512,
    height: int = 512,
    num_steps: int = 4,
    guidance_scale: float = 2.0,
    seed: int = 0,
):
    """Generate an image from a prompt and optional references.

    Args:
        pipeline: The FLUX.2 pipeline.
        device: Device to use for generation.
        prompt: Text prompt describing the image.
        reference_images: Optional list of reference images for composition.
        width: Output image width.
        height: Output image height.
        num_steps: Number of inference steps.
        guidance_scale: Guidance scale (higher = more prompt adherence).
        seed: Random seed for reproducibility.

    Returns:
        Generated PIL Image.
    """
    import torch

    generator = torch.Generator(device=device).manual_seed(seed)

    kwargs = {
        "prompt": prompt,
        "height": height,
        "width": width,
        "num_inference_steps": num_steps,
        "guidance_scale": guidance_scale,
        "generator": generator,
    }

    if reference_images:
        kwargs["image"] = reference_images if len(reference_images) > 1 else reference_images[0]

    result = pipeline(**kwargs)
    return result.images[0]


# Model name constants
MODEL_FLUX = "flux"
MODEL_NANOBANANA = "nanobanana"
VALID_MODELS = [MODEL_FLUX, MODEL_NANOBANANA]

# Map model names to cache version strings
MODEL_VERSIONS = {
    MODEL_FLUX: "flux2-klein-4b",
    MODEL_NANOBANANA: "nanobanana-gemini-2.5-flash",
}

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
    """Generate an image from a text prompt."""
    model = args.model

    # Load reference images if provided
    reference_images = None
    if args.references:
        ref_size = args.ref_size if model == MODEL_FLUX else None
        size_info = f" at {args.ref_size}x{args.ref_size}" if ref_size else ""
        print(f"Loading {len(args.references)} reference image(s){size_info}...")
        reference_images = load_reference_images(args.references, size=ref_size)

    print("=" * 60)
    print(f"Model: {model}")
    print(f"Output: {args.output}")
    if model == MODEL_FLUX:
        print(f"Size: {args.width}x{args.height}")
        print(f"Steps: {args.steps}")
        print(f"Guidance: {args.guidance}")
    else:
        print(f"Aspect ratio: {args.aspect_ratio}")
    print(f"Seed: {args.seed}")
    if reference_images:
        print(f"References: {len(reference_images)} image(s)")
    print("=" * 60)
    print(f"\nPrompt:\n{args.prompt[:200]}{'...' if len(args.prompt) > 200 else ''}\n")
    print("=" * 60)

    total_start = time.time()

    if model == MODEL_NANOBANANA:
        # NanoBanana: cloud API, no pipeline to load
        print(f"\n--- Generating {args.count} image(s) via NanoBanana ---")
        gen_times = []

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
            print(f"  [image {i+1}] {elapsed:.2f}s (seed={seed})")

    else:
        # Flux: local pipeline
        print("\n--- Loading Pipeline ---")
        pipeline, device = get_pipeline(dtype=args.dtype, verbose=args.verbose)
        print(f"  [total load] {time.time() - total_start:.2f}s")

        import torch

        # Warmup run for consistent timing
        if not args.no_warmup:
            print("\n--- Warmup ---")
            with timed("warmup generation"):
                _ = pipeline(
                    prompt="test",
                    height=256,
                    width=256,
                    num_inference_steps=1,
                    generator=torch.Generator(device=device).manual_seed(0),
                )
            if args.verbose:
                with timed("cuda.synchronize after warmup"):
                    torch.cuda.synchronize()

        # Generate image(s)
        print(f"\n--- Generating {args.count} image(s) ---")
        gen_times = []

        for i in range(args.count):
            seed = args.seed + i
            start = time.time()

            image = generate_image(
                pipeline,
                device,
                prompt=args.prompt,
                reference_images=reference_images,
                width=args.width,
                height=args.height,
                num_steps=args.steps,
                guidance_scale=args.guidance,
                seed=seed,
            )

            if args.verbose:
                torch.cuda.synchronize()

            elapsed = time.time() - start
            gen_times.append(elapsed)
            print(f"  [image {i+1}] {elapsed:.2f}s (seed={seed})")

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
# Subcommand: list
# =============================================================================

def cmd_list(args):
    """List renders in the cache/frozen directories."""
    from .render_cache import RenderCache

    game_dir, renders_dir, _ = get_game_dirs(args.game_path)
    cache = RenderCache(renders_dir)

    stats = cache.stats()

    print(f"Game: {game_dir}")
    print(f"Renders: {renders_dir}")
    print()

    # List frozen renders
    if renders_dir.exists():
        frozen_files = sorted(renders_dir.glob("*.png"))
        if frozen_files:
            print(f"Frozen renders ({len(frozen_files)}):")
            for f in frozen_files:
                size_kb = f.stat().st_size / 1024
                print(f"  {f.name:40} {size_kb:6.1f} KB")
            print()

    # List cached renders
    cache_dir = renders_dir / "cache"
    if cache_dir.exists():
        cache_files = sorted(cache_dir.glob("*.png"))
        if cache_files:
            print(f"Cached renders ({len(cache_files)}):")
            for f in cache_files:
                size_kb = f.stat().st_size / 1024
                print(f"  {f.name:40} {size_kb:6.1f} KB")
            print()

    # Summary
    print("Summary:")
    print(f"  Frozen: {stats['frozen_count']} files, {stats['frozen_size_bytes'] / 1024:.1f} KB")
    print(f"  Cached: {stats['cache_count']} files, {stats['cache_size_bytes'] / 1024:.1f} KB")


# =============================================================================
# Subcommand: log
# =============================================================================

def cmd_log(args):
    """Show the render log."""
    from .render_cache import RenderCache

    game_dir, renders_dir, _ = get_game_dirs(args.game_path)
    cache = RenderCache(renders_dir)

    entries = cache.read_log(limit=args.limit)

    if not entries:
        print(f"No render log entries found in {renders_dir}")
        return

    print(f"Game: {game_dir}")
    print(f"Recent renders ({len(entries)} entries):")
    print()

    for entry in entries:
        timestamp = entry.get("timestamp", "unknown")
        entity = entry.get("entity", "unknown")
        hash_key = entry.get("hash", "unknown")
        prompt = entry.get("prompt", "")

        # Truncate prompt for display
        if len(prompt) > 60:
            prompt = prompt[:57] + "..."

        print(f"  {timestamp[:19]}  {entity:20}  {hash_key[:8]}")
        print(f"    Prompt: {prompt}")

        refs = entry.get("refs", [])
        if refs:
            print(f"    Refs: {', '.join(refs)}")

        print()


# =============================================================================
# Subcommand: clear
# =============================================================================

def cmd_clear(args):
    """Clear the render cache (preserves frozen renders)."""
    from .render_cache import RenderCache

    game_dir, renders_dir, _ = get_game_dirs(args.game_path)
    cache = RenderCache(renders_dir)

    if not args.yes:
        stats = cache.stats()
        print(f"Game: {game_dir}")
        print(f"This will delete {stats['cache_count']} cached render(s) from {renders_dir / 'cache'}")
        print("Frozen renders will be preserved.")
        response = input("Continue? [y/N] ")
        if response.lower() != "y":
            print("Aborted.")
            return

    count = cache.clear_cache()
    print(f"Cleared {count} cached render(s).")


# =============================================================================
# Main entry point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate illustrations and manage game renders (supports flux and nanobanana models)",
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
  filfre generate --model nanobanana --prompt "A dragon in a cave" --output dragon.png
  filfre generate --model flux --prompt "A brass lantern" --output lantern.png

  # With reference images for composition:
  filfre generate --model nanobanana --prompt "A brass lantern on a stone altar" \\
      --reference lantern.png --output scene.png
        """,
    )
    gen_parser.add_argument(
        "--model", "-m",
        type=str,
        required=True,
        choices=VALID_MODELS,
        help="Image generation model: flux (local CUDA) or nanobanana (Google cloud API)",
    )
    gen_parser.add_argument(
        "--prompt", "-p",
        type=str,
        required=True,
        help="Text prompt describing the image to generate",
    )
    gen_parser.add_argument(
        "--output", "-o",
        type=str,
        default="output.png",
        help="Output filename (default: output.png)",
    )
    gen_parser.add_argument(
        "--width",
        type=int,
        default=512,
        help="Image width (default: 512)",
    )
    gen_parser.add_argument(
        "--height",
        type=int,
        default=512,
        help="Image height (default: 512)",
    )
    gen_parser.add_argument(
        "--aspect-ratio",
        type=str,
        default="1:1",
        help="Aspect ratio for nanobanana model (default: 1:1)",
    )
    gen_parser.add_argument(
        "--steps",
        type=int,
        default=4,
        help="Number of inference steps for flux model (default: 4)",
    )
    gen_parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for reproducibility (default: 0)",
    )
    gen_parser.add_argument(
        "--guidance",
        type=float,
        default=2.0,
        help="Guidance scale - higher values follow prompt more closely (default: 2.0)",
    )
    gen_parser.add_argument(
        "--dtype",
        type=str,
        default="bf16",
        choices=["fp32", "fp16", "bf16"],
        help="Data type for model weights (default: bf16)",
    )
    gen_parser.add_argument(
        "--reference", "-r",
        type=str,
        action="append",
        dest="references",
        metavar="IMAGE",
        help="Reference image for composition (can be used multiple times)",
    )
    gen_parser.add_argument(
        "--ref-size",
        type=int,
        default=256,
        help="Size to resize reference images to (default: 256)",
    )
    gen_parser.add_argument(
        "--count", "-n",
        type=int,
        default=1,
        help="Number of images to generate (for timing analysis)",
    )
    gen_parser.add_argument(
        "--no-warmup",
        action="store_true",
        help="Skip warmup run",
    )
    gen_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print detailed timing information",
    )
    gen_parser.set_defaults(func=cmd_generate)

    # ---------------------------------------------------------------------
    # list subcommand
    # ---------------------------------------------------------------------
    list_parser = subparsers.add_parser(
        "list",
        aliases=["ls"],
        help="List renders in cache and frozen directories",
    )
    list_parser.add_argument(
        "game_path",
        type=str,
        help="Path to the game directory",
    )
    list_parser.set_defaults(func=cmd_list)

    # ---------------------------------------------------------------------
    # log subcommand
    # ---------------------------------------------------------------------
    log_parser = subparsers.add_parser(
        "log",
        help="Show the render log",
    )
    log_parser.add_argument(
        "game_path",
        type=str,
        help="Path to the game directory",
    )
    log_parser.add_argument(
        "-n", "--limit",
        type=int,
        default=20,
        help="Maximum number of entries to show (default: 20)",
    )
    log_parser.set_defaults(func=cmd_log)

    # ---------------------------------------------------------------------
    # clear subcommand
    # ---------------------------------------------------------------------
    clear_parser = subparsers.add_parser(
        "clear",
        help="Clear the render cache (preserves frozen renders)",
    )
    clear_parser.add_argument(
        "game_path",
        type=str,
        help="Path to the game directory",
    )
    clear_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    clear_parser.set_defaults(func=cmd_clear)

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
