#!/usr/bin/env python3
"""
CLI for FLUX.2 Klein text-to-image generation.

Generates illustrations for text adventure game scenes.

Usage:
    filfre --prompt "A dragon in a cave" --output dragon.png

With reference images:
    filfre --prompt "A brass lantern on a stone altar in a dark cave" \
        --reference lantern.png --output scene.png

Multi-reference composition:
    filfre --prompt "A young man at desk showing his keyring" \
        --reference hacker.png --reference desk.png --reference keyring.png
"""

import argparse
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


def get_pipeline(dtype: str = "bf16", verbose: bool = False):
    """Load the FLUX.2 Klein pipeline.

    Args:
        dtype: Data type for model weights ("bf16", "fp16", or "fp32").
        verbose: If True, print detailed timing information.

    Returns:
        Tuple of (pipeline, device).
    """
    with timed("import torch"):
        import torch
    with timed("import diffusers"):
        from diffusers import Flux2KleinPipeline

    # Determine device
    if torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
        print("WARNING: No CUDA GPU detected. Running on CPU will be slow.")

    # Determine weight dtype
    if device == "cpu":
        weight_dtype = torch.float32
        print("NOTE: Using float32 on CPU")
    elif dtype == "fp16":
        weight_dtype = torch.float16
    elif dtype == "bf16":
        weight_dtype = torch.bfloat16
    else:
        weight_dtype = torch.float32

    print(f"Loading FLUX.2 Klein 4B...")
    print(f"Device: {device}, dtype: {weight_dtype}")

    # Load pipeline to CPU first
    with timed("from_pretrained (CPU)"):
        pipeline = Flux2KleinPipeline.from_pretrained(
            "black-forest-labs/FLUX.2-klein-4B",
            torch_dtype=weight_dtype,
        )

    if device == "cuda":
        # Fast CUDA transfer: clone parameters first to break mmap links
        # mmap'd tensors transfer to CUDA ~100x slower than regular tensors
        with timed("clone parameters"):
            for name, component in pipeline.components.items():
                if hasattr(component, 'parameters'):
                    clone_parameters_in_place(component)

        with timed("pipeline.to(cuda)"):
            pipeline = pipeline.to(device)
            torch.cuda.synchronize()

    if verbose:
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


def main():
    parser = argparse.ArgumentParser(
        description="Generate illustrations using FLUX.2 Klein",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  filfre --prompt "A dragon in a cave" --seed 42 --output dragon.png

  # With reference images for composition:
  filfre --prompt "A brass lantern on a stone altar" \\
      --reference lantern.png --output scene.png

  # Multi-reference composition:
  filfre --prompt "A young man at desk holding a keyring" \\
      --reference hacker.png --reference desk.png --reference keyring.png \\
      --output composed.png
        """,
    )
    parser.add_argument(
        "--prompt",
        type=str,
        required=True,
        help="Text prompt describing the image to generate",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="output.png",
        help="Output filename (default: output.png)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=512,
        help="Image width (default: 512)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=512,
        help="Image height (default: 512)",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=4,
        help="Number of inference steps (default: 4)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for reproducibility (default: 0)",
    )
    parser.add_argument(
        "--guidance",
        type=float,
        default=2.0,
        help="Guidance scale - higher values follow prompt more closely (default: 2.0)",
    )
    parser.add_argument(
        "--dtype",
        type=str,
        default="bf16",
        choices=["fp32", "fp16", "bf16"],
        help="Data type for model weights (default: bf16)",
    )
    parser.add_argument(
        "--reference",
        "-r",
        type=str,
        action="append",
        dest="references",
        metavar="IMAGE",
        help="Reference image for composition (can be used multiple times)",
    )
    parser.add_argument(
        "--ref-size",
        type=int,
        default=256,
        help="Size to resize reference images to (default: 256). "
             "Smaller = faster, larger = more detail preserved.",
    )
    parser.add_argument(
        "--count",
        "-n",
        type=int,
        default=1,
        help="Number of images to generate (for timing analysis)",
    )
    parser.add_argument(
        "--no-warmup",
        action="store_true",
        help="Skip warmup run",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print detailed timing information",
    )

    args = parser.parse_args()

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


if __name__ == "__main__":
    main()
