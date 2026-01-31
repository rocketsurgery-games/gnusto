#!/usr/bin/env python3
"""
CLI for FLUX.2 Klein text-to-image generation and game asset management.

Generates illustrations for text adventure game scenes.

Usage:
    # Direct generation
    filfre generate --prompt "A dragon in a cave" --output dragon.png

    # With reference images
    filfre generate --prompt "A brass lantern on a stone altar" \
        --reference lantern.png --output scene.png

    # Render a game entity (uses initial game state)
    filfre render games/lurkinghorror @terminal-room

    # List renders in cache
    filfre list games/lurkinghorror

    # Show render log
    filfre log games/lurkinghorror
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Any


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


# =============================================================================
# Subcommand: generate
# =============================================================================

def cmd_generate(args):
    """Generate an image from a text prompt."""
    # Load reference images if provided
    reference_images = None
    if args.references:
        print(f"Loading {len(args.references)} reference image(s) at {args.ref_size}x{args.ref_size}...")
        reference_images = load_reference_images(args.references, size=args.ref_size)

    print("=" * 60)
    print(f"Output: {args.output}")
    print(f"Size: {args.width}x{args.height}")
    print(f"Steps: {args.steps}")
    print(f"Seed: {args.seed}")
    print(f"Guidance: {args.guidance}")
    if reference_images:
        print(f"References: {len(reference_images)} image(s) at {args.ref_size}x{args.ref_size}")
    print("=" * 60)
    print(f"\nPrompt:\n{args.prompt[:200]}{'...' if len(args.prompt) > 200 else ''}\n")
    print("=" * 60)

    # Load pipeline
    print("\n--- Loading Pipeline ---")
    total_start = time.time()
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
    from gnusto.terminal_images import display_image, is_supported
    if is_supported():
        print()
        display_image(output_path, width=60)


# =============================================================================
# Subcommand: render
# =============================================================================

def parse_set_arg(set_arg: str) -> tuple[str, str, Any]:
    """Parse a --set argument using Grue syntax: '@entity :prop value'.

    Examples:
        --set '@refrigerator :open true'
        --set '@microwave :timer 120'
        --set '@player :score 100'

    Returns:
        Tuple of (entity_id, property_name, value)
    """
    from grue.sexpr import parse_all, Symbol, Keyword
    from grue.expr import quote_to_data

    try:
        parts = parse_all(set_arg)
    except Exception as e:
        raise ValueError(f"Invalid --set syntax: '{set_arg}'. Error: {e}")

    if len(parts) != 3:
        raise ValueError(
            f"Invalid --set format: '{set_arg}'. "
            f"Expected '@entity :prop value' (got {len(parts)} parts)"
        )

    entity_expr, prop_expr, value_expr = parts

    # Entity must be a symbol starting with @
    if not isinstance(entity_expr, Symbol) or not entity_expr.name.startswith('@'):
        raise ValueError(f"First argument must be an entity (@symbol), got: {entity_expr}")
    entity_id = entity_expr.name

    # Property must be a keyword
    if not isinstance(prop_expr, Keyword):
        raise ValueError(f"Second argument must be a keyword (:prop), got: {prop_expr}")
    prop = prop_expr.name  # Keyword.name is without the colon

    # Value is converted via quote_to_data (handles bools, numbers, strings, etc.)
    value = quote_to_data(value_expr)

    return entity_id, prop, value


def cmd_render(args):
    """Render an entity from a game using the scene renderer.

    Note: This renders the entity in its initial game state. For dynamic
    state rendering during gameplay, use gnusto's built-in scene renderer.
    """
    from gnusto.scene_renderer import SceneRenderer
    from grue.parser import load_grue
    from grue.runtime import GrueRuntime

    game_dir, renders_dir, assets_dir = get_game_dirs(args.game_path)
    entity_id = args.entity_id

    # Ensure entity_id starts with @
    if not entity_id.startswith("@"):
        entity_id = f"@{entity_id}"

    print(f"Loading game: {game_dir}")
    world = load_grue(game_dir)
    runtime = GrueRuntime(world)

    # Apply --set overrides to state
    if args.set_props:
        print("State overrides:")
        for set_arg in args.set_props:
            try:
                target_entity, prop, value = parse_set_arg(set_arg)
                runtime.set_object_property(target_entity, prop, value)
                print(f"  {target_entity}:{prop} = {value!r}")
            except ValueError as e:
                print(f"Error: {e}")
                sys.exit(1)
            except Exception as e:
                print(f"Error setting {set_arg}: {e}")
                sys.exit(1)

    print(f"Renders directory: {renders_dir}")
    print(f"Entity: {entity_id}")
    if args.set_props:
        print("Note: Rendering with modified state")
    else:
        print("Note: Rendering with initial game state")

    # Initialize renderer
    print("\n--- Initializing Scene Renderer ---")
    renderer = SceneRenderer(
        runtime=runtime,
        renders_dir=renders_dir,
        assets_dir=assets_dir,
        verbose=args.verbose,
    )

    # Determine if it's a room, object, or reference
    is_room = entity_id in runtime.world.rooms
    is_object = entity_id in runtime.world.objects
    is_reference = entity_id in runtime.world.references

    if not is_room and not is_object and not is_reference:
        print(f"Error: Entity '{entity_id}' not found in game")
        sys.exit(1)

    # Check for render spec
    entity = (
        runtime.world.rooms.get(entity_id) or
        runtime.world.objects.get(entity_id) or
        runtime.world.references.get(entity_id)
    )
    if not entity.render:
        print(f"Error: Entity '{entity_id}' has no render spec")
        sys.exit(1)

    entity_type = "room" if is_room else "reference" if is_reference else "object"
    print(f"\n--- Rendering {entity_id} ({entity_type}) ---")
    start = time.time()

    if is_room:
        result = renderer.render_room(entity_id)
    elif is_reference:
        result = renderer.render_reference(entity_id)
    else:
        result = renderer.render_object(entity_id)

    if result:
        print(f"\nGenerated: {result}")
        print(f"Time: {time.time() - start:.2f}s")

        # Display in terminal if supported
        from gnusto.terminal_images import display_image, is_supported
        if is_supported():
            print()
            display_image(result, width=60)
    else:
        print(f"\nFailed to render {entity_id}")
        sys.exit(1)


# =============================================================================
# Subcommand: list
# =============================================================================

def cmd_list(args):
    """List renders in the cache/frozen directories."""
    from grue.render_cache import RenderCache

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
    from grue.render_cache import RenderCache

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
    from grue.render_cache import RenderCache

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
        description="Generate illustrations using FLUX.2 Klein and manage game renders",
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
  filfre generate --prompt "A dragon in a cave" --seed 42 --output dragon.png

  # With reference images for composition:
  filfre generate --prompt "A brass lantern on a stone altar" \\
      --reference lantern.png --output scene.png
        """,
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
        "--steps",
        type=int,
        default=4,
        help="Number of inference steps (default: 4)",
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
    # render subcommand
    # ---------------------------------------------------------------------
    render_parser = subparsers.add_parser(
        "render",
        help="Render an entity from a game (initial state)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Renders an entity using its render spec in the initial game state.
Useful for testing render specs and pre-caching initial images.

For dynamic state rendering during gameplay, use gnusto's built-in
scene renderer which has access to live game state.

Examples:
  filfre render games/lurkinghorror @terminal-room
  filfre render games/lurkinghorror @brass-lantern

  # Render with modified state (uses Grue syntax):
  filfre render games/lurkinghorror @refrigerator --set '@refrigerator :open true'
  filfre render games/lurkinghorror @kitchen -s '@microwave :timer 120'
        """,
    )
    render_parser.add_argument(
        "game_path",
        type=str,
        help="Path to the game directory",
    )
    render_parser.add_argument(
        "entity_id",
        type=str,
        help="Entity ID to render (e.g., @terminal-room, @brass-lantern)",
    )
    render_parser.add_argument(
        "--set", "-s",
        type=str,
        action="append",
        dest="set_props",
        metavar="'@ENTITY :PROP VALUE'",
        help="Set object property before rendering using Grue syntax (can be repeated)",
    )
    render_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show full prompt and render parameters",
    )
    render_parser.set_defaults(func=cmd_render)

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
