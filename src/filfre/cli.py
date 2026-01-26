#!/usr/bin/env python3
"""
CLI for OmniGen2 text-to-image generation.

Generates illustrations for text adventure game scenes like Zork.

Setup:
    git submodule update --init  # clones vendor/omnigen2
    pip install -r vendor/omnigen2/requirements.txt

Usage:
    filfre --prompt "A dragon in a cave" --output dragon.png

For lower VRAM (< 17GB), use:
    filfre --prompt "A dragon in a cave" --cpu-offload

In-context generation with reference images:
    filfre --reference lantern.png \\
        --prompt "A dungeon scene with the brass lantern from <img1> illuminating ancient stone walls"
"""

import argparse
import importlib.util
import os
import re
import sys
from pathlib import Path


def check_triton_compatibility():
    """Check for triton incompatibility with certain GPUs and warn/exit.

    NVIDIA GB10 (sm_121) is not supported by triton's ptxas.
    """
    try:
        import torch
        if not torch.cuda.is_available():
            return  # No GPU, no problem

        # Check GPU compute capability
        capability = torch.cuda.get_device_capability(0)
        major, minor = capability

        # sm_121 (compute capability 12.1) is GB10, not supported by triton
        if major >= 12:
            if importlib.util.find_spec("triton") is not None:
                gpu_name = torch.cuda.get_device_name(0)
                print(f"ERROR: triton is installed but incompatible with {gpu_name} (sm_{major}{minor}).")
                print("       triton's ptxas does not support this architecture.")
                print()
                print("To fix, uninstall triton:")
                print("    uv pip uninstall triton")
                print("    # or: pip uninstall triton")
                print()
                print("OmniGen2 will use PyTorch's native implementations instead (no performance loss).")
                sys.exit(1)
    except Exception:
        pass  # Don't fail on detection errors


def find_omnigen2_repo() -> Path:
    """Locate the omnigen2 vendor directory.

    Checks in order:
    1. OMNIGEN2_PATH environment variable
    2. ./vendor/omnigen2 (relative to CWD)
    3. Relative to project root (look for pyproject.toml)

    Returns:
        Path to omnigen2 directory.

    Raises:
        RuntimeError: If omnigen2 cannot be found.
    """
    # Check environment variable first
    if env_path := os.environ.get("OMNIGEN2_PATH"):
        path = Path(env_path)
        if path.exists():
            return path

    # Check relative to CWD (typical usage)
    cwd_path = Path.cwd() / "vendor" / "omnigen2"
    if cwd_path.exists():
        return cwd_path

    # Check relative to project root (look for pyproject.toml)
    current = Path.cwd()
    for _ in range(5):  # Don't go too far up
        if (current / "pyproject.toml").exists():
            project_path = current / "vendor" / "omnigen2"
            if project_path.exists():
                return project_path
        parent = current.parent
        if parent == current:
            break
        current = parent

    raise RuntimeError(
        "Could not find vendor/omnigen2. Either:\n"
        "  1. Run from the project root directory, or\n"
        "  2. Set OMNIGEN2_PATH environment variable, or\n"
        "  3. Run: git submodule update --init"
    )


def setup_omnigen2_imports():
    """Add omnigen2_repo to sys.path for imports."""
    repo_path = find_omnigen2_repo()
    if str(repo_path) not in sys.path:
        sys.path.insert(0, str(repo_path))


# Set up imports before importing OmniGen2 modules
setup_omnigen2_imports()

import torch
from PIL import Image, ImageOps
from accelerate import Accelerator

from omnigen2.pipelines.omnigen2.pipeline_omnigen2 import OmniGen2Pipeline
from omnigen2.models.transformers.transformer_omnigen2 import OmniGen2Transformer2DModel


def load_reference_images(image_paths: list[str]) -> list[Image.Image]:
    """Load and preprocess reference images for in-context generation.

    Args:
        image_paths: List of paths to reference images.

    Returns:
        List of PIL Images ready for use with OmniGen2.
    """
    images = []
    for path in image_paths:
        img = Image.open(path).convert("RGB")
        img = ImageOps.exif_transpose(img)  # Handle EXIF orientation
        images.append(img)
    return images


def get_pipeline(
    model_path: str = "OmniGen2/OmniGen2",
    cpu_offload: bool = False,
    sequential_offload: bool = False,
    dtype: str = "bf16",
    force_mps: bool = False,
    enable_taylorseer: bool = False,
    enable_teacache: bool = False,
    teacache_thresh: float = 0.05,
):
    """Load the OmniGen2 pipeline."""
    # Determine device - MPS has issues with scaled_dot_product_attention
    # so we default to CPU on macOS unless CUDA is available
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available() and force_mps:
        # MPS has bugs with empty tensors in attention, only use if forced
        print("WARNING: Using MPS despite known compatibility issues.")
        device = "mps"
    elif torch.backends.mps.is_available():
        print("WARNING: MPS detected but has compatibility issues with OmniGen2.")
        print("         Falling back to CPU. Use --force-mps to try MPS anyway.")
        device = "cpu"
    else:
        device = "cpu"

    # Determine weight dtype - CPU doesn't support bfloat16 well on all systems
    if device == "cpu":
        # Use float32 on CPU for compatibility
        weight_dtype = torch.float32
        mixed_precision = "no"
        print("NOTE: Using float32 on CPU (slower but compatible)")
    elif dtype == "fp16":
        weight_dtype = torch.float16
        mixed_precision = "fp16"
    elif dtype == "bf16":
        weight_dtype = torch.bfloat16
        mixed_precision = "bf16"
    else:
        weight_dtype = torch.float32
        mixed_precision = "no"

    # Initialize accelerator
    accelerator = Accelerator(mixed_precision=mixed_precision)

    print(f"Loading OmniGen2 from {model_path}...")
    print(f"Device: {device}, dtype: {weight_dtype}")

    pipeline = OmniGen2Pipeline.from_pretrained(
        model_path,
        torch_dtype=weight_dtype,
        trust_remote_code=True,
    )

    # Load transformer explicitly
    pipeline.transformer = OmniGen2Transformer2DModel.from_pretrained(
        model_path,
        subfolder="transformer",
        torch_dtype=weight_dtype,
    )

    # Apply optimizations
    if enable_taylorseer:
        pipeline.enable_taylorseer = True
        print("TaylorSeer optimization enabled")

    if enable_teacache:
        pipeline.transformer.enable_teacache = True
        pipeline.transformer.teacache_rel_l1_thresh = teacache_thresh
        print(f"TeaCache optimization enabled (threshold: {teacache_thresh})")

    # Handle memory optimization
    if sequential_offload:
        print("Enabling sequential CPU offload (< 3GB VRAM, slower)...")
        pipeline.enable_sequential_cpu_offload()
    elif cpu_offload:
        print("Enabling CPU offload (~50% VRAM reduction)...")
        pipeline.enable_model_cpu_offload()
    else:
        pipeline = pipeline.to(device)

    return pipeline, accelerator, device


def generate_image(
    pipeline,
    device: str,
    prompt: str,
    input_images: list[Image.Image] | None = None,
    width: int = 1024,
    height: int = 1024,
    num_steps: int = 50,
    text_guidance_scale: float = 5.0,
    image_guidance_scale: float = 2.0,
    negative_prompt: str = "(((deformed))), blurry, over saturation, bad anatomy, disfigured, poorly drawn face, mutation, mutated, extra_limb, ugly, poorly drawn hands, fused fingers, messy drawing, broken legs",
    seed: int = 0,
    cfg_range_end: float = 1.0,
) -> list[Image.Image]:
    """Generate an image from a prompt."""
    generator = torch.Generator(device=device).manual_seed(seed)

    results = pipeline(
        prompt=prompt,
        input_images=input_images,
        width=width,
        height=height,
        num_inference_steps=num_steps,
        max_sequence_length=1024,
        text_guidance_scale=text_guidance_scale,
        image_guidance_scale=image_guidance_scale,
        cfg_range=(0.0, cfg_range_end),
        negative_prompt=negative_prompt,
        num_images_per_prompt=1,
        generator=generator,
        output_type="pil",
    )

    return results.images


def main():
    parser = argparse.ArgumentParser(
        description="Generate illustrations for text adventure scenes using OmniGen2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  filfre --prompt "A dragon in a cave" --seed 42

For low VRAM systems:
  filfre --prompt "A dragon in a cave" --cpu-offload
  filfre --prompt "A dragon in a cave" --sequential-offload  # < 3GB VRAM
        """,
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Custom prompt (use with --scene custom)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output.png",
        help="Output filename",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1024,
        help="Image width",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=1024,
        help="Image height",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=50,
        help="Number of inference steps",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--cpu-offload",
        action="store_true",
        help="Enable CPU offload (~50%% VRAM reduction)",
    )
    parser.add_argument(
        "--sequential-offload",
        action="store_true",
        help="Enable sequential CPU offload (< 3GB VRAM, much slower)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="OmniGen2/OmniGen2",
        help="Model path or HuggingFace repo",
    )
    parser.add_argument(
        "--dtype",
        type=str,
        default="bf16",
        choices=["fp32", "fp16", "bf16"],
        help="Data type for model weights",
    )
    parser.add_argument(
        "--text-guidance",
        type=float,
        default=5.0,
        help="Text guidance scale (higher = more prompt adherence)",
    )
    parser.add_argument(
        "--list-scenes",
        action="store_true",
        help="List available scenes and exit",
    )
    parser.add_argument(
        "--force-mps",
        action="store_true",
        help="Force MPS (Apple Silicon) even though it has compatibility issues",
    )
    parser.add_argument(
        "--reference",
        "-r",
        type=str,
        action="append",
        dest="references",
        metavar="IMAGE",
        help="Reference image for in-context generation (can be used multiple times). "
        "Use <img1>, <img2>, etc. in your prompt to reference them.",
    )
    parser.add_argument(
        "--image-guidance",
        type=float,
        default=2.0,
        help="Image guidance scale for reference images (higher = more adherence to references)",
    )

    # Optimization flags
    parser.add_argument(
        "--taylorseer",
        action="store_true",
        help="Enable TaylorSeer optimization (~2x speedup, may affect quality)",
    )
    parser.add_argument(
        "--teacache",
        action="store_true",
        help="Enable TeaCache optimization (~30%% speedup, may affect quality)",
    )
    parser.add_argument(
        "--teacache-thresh",
        type=float,
        default=0.05,
        help="TeaCache L1 threshold (lower = higher quality, slower). Default: 0.05",
    )
    # Note: Other schedulers (heun, DPMSolver++) are not compatible with OmniGen2's pipeline
    # which passes custom kwargs like num_tokens. Keeping euler only for now.
    parser.add_argument(
        "--cfg-range-end",
        type=float,
        default=1.0,
        help="CFG range end (0.0-1.0). Lower values skip CFG in later steps. Default: 1.0",
    )

    args = parser.parse_args()

    # Check for triton incompatibility before doing anything heavy
    check_triton_compatibility()

    # Validate mutually exclusive options
    if args.taylorseer and args.teacache:
        print("Error: --taylorseer and --teacache are mutually exclusive")
        print("       The pipeline only supports one caching strategy at a time.")
        sys.exit(1)

    if args.list_scenes:
        print("Available scenes:\n")
        for name, desc in ZORK_SCENES.items():
            first_line = desc.strip().split("\n")[0]
            print(f"  {name}:")
            print(f"    {first_line}\n")
        return

    # Determine prompt
    if not args.prompt:
        print("Error: --prompt required")
        sys.exit(1)
    prompt = args.prompt

    # Load reference images if provided
    input_images = None
    if args.references:
        print(f"Loading {len(args.references)} reference image(s)...")
        input_images = load_reference_images(args.references)
        # Validate that prompt contains <img> references if images provided
        img_refs = re.findall(r"<img(\d+)>", prompt)
        if not img_refs:
            print("WARNING: Reference images provided but no <img1>, <img2>, etc. found in prompt.")
            print("         Add references like 'the lantern from <img1>' to use them.")
        else:
            max_ref = max(int(r) for r in img_refs)
            if max_ref > len(input_images):
                print(f"WARNING: Prompt references <img{max_ref}> but only {len(input_images)} image(s) provided.")

    print("=" * 60)
    print(f"Output: {args.output}")
    print(f"Size: {args.width}x{args.height}")
    print(f"Steps: {args.steps}")
    print(f"Seed: {args.seed}")
    print(f"Text guidance: {args.text_guidance}")
    if input_images:
        print(f"Reference images: {len(input_images)}")
        print(f"Image guidance: {args.image_guidance}")
    # Show optimization settings
    optimizations = []
    if args.taylorseer:
        optimizations.append("TaylorSeer")
    if args.teacache:
        optimizations.append(f"TeaCache(thresh={args.teacache_thresh})")
    if args.cfg_range_end < 1.0:
        optimizations.append(f"cfg_range_end={args.cfg_range_end}")
    if optimizations:
        print(f"Optimizations: {', '.join(optimizations)}")
    print("=" * 60)
    print(f"\nPrompt:\n{prompt[:200]}{'...' if len(prompt) > 200 else ''}\n")
    print("=" * 60)

    # Load pipeline
    pipeline, accelerator, device = get_pipeline(
        args.model,
        cpu_offload=args.cpu_offload,
        sequential_offload=args.sequential_offload,
        dtype=args.dtype,
        force_mps=args.force_mps,
        enable_taylorseer=args.taylorseer,
        enable_teacache=args.teacache,
        teacache_thresh=args.teacache_thresh,
    )

    # Generate image
    print("\nGenerating image...")
    images = generate_image(
        pipeline,
        device,
        prompt=prompt,
        input_images=input_images,
        width=args.width,
        height=args.height,
        num_steps=args.steps,
        text_guidance_scale=args.text_guidance,
        image_guidance_scale=args.image_guidance,
        seed=args.seed,
        cfg_range_end=args.cfg_range_end,
    )

    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(output_path)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
