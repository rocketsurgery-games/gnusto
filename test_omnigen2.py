#!/usr/bin/env python3
"""
Test script for OmniGen2 text-to-image generation.

This script tests OmniGen2's ability to generate consistent illustrations
for text adventure game scenes like Zork.

Setup:
    cd omnigen2_repo
    pip install -r requirements.txt
    # Optional but recommended:
    pip install flash-attn==2.7.4.post1 --no-build-isolation
    cd ..
    python test_omnigen2.py --scene hades_entrance

For lower VRAM (< 17GB), use:
    python test_omnigen2.py --scene hades_entrance --cpu-offload

In-context generation with reference images:
    python test_omnigen2.py --scene custom \\
        --reference lantern.png \\
        --prompt "A dungeon scene with the brass lantern from <img1> illuminating ancient stone walls"
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Add the omnigen2_repo to path so we can import from it
REPO_PATH = Path(__file__).parent / "omnigen2_repo"
sys.path.insert(0, str(REPO_PATH))

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
        cfg_range=(0.0, 1.0),
        negative_prompt=negative_prompt,
        num_images_per_prompt=1,
        generator=generator,
        output_type="pil",
    )

    return results.images


# Example Zork-style scene descriptions
ZORK_SCENES = {
    "hades_entrance": """A dark fantasy illustration in a detailed painterly style.

A massive ancient stone gateway dominates the scene, weathered and imposing. Above the gateway arch, carved deeply into the stone, reads the inscription: "Abandon every hope all ye who enter here!"

The gate stands open, revealing a desolate hellscape beyond. In the far right corner of the scene, a gruesome pile of mangled bodies lies in shadow.

Translucent evil spirits hover menacingly in the gateway opening, their ghostly forms blocking passage. They leer with malevolent grins.

In the foreground near the viewer's feet, a small exquisite jade figurine rests on the rocky ground, its green surface catching what little light exists.

The atmosphere is oppressive and foreboding, with a sickly greenish pallor to the lighting.""",

    "white_house": """A nostalgic illustration in a detailed painterly style.

A small white colonial house stands in a forest clearing. The house has a boarded front door and small windows.

To the west, a dense forest of tall deciduous trees. To the east, an overgrown path leads away into darkness.

A small mailbox stands near the path, slightly rusted but still functional.

The scene is lit by late afternoon sunlight filtering through the trees, casting long shadows across the clearing.

The atmosphere is mysterious but not threatening, with a sense of adventure and discovery.""",

    "trophy_case": """A warm interior illustration in a detailed painterly style.

An elegant living room in an old house. Dark wood paneling on the walls. A large ornate trophy case dominates one wall, its glass doors reflecting candlelight.

On the mantelpiece above a cold fireplace, a brass lantern sits unlit. Nearby, an ancient elvish sword hangs on the wall, its blade glinting.

A worn oriental rug covers the wooden floor. Dust motes float in shafts of light from a small window.

The atmosphere is one of faded grandeur, a place that was once important but has been long abandoned.""",

    "flood_control_dam": """A dramatic illustration in a detailed painterly style.

A massive concrete dam stretches across a river gorge. The structure is immense, industrial, brutalist architecture from another era.

Water cascades down the spillway with tremendous force. Mist rises from the churning waters below.

A control room building sits atop the dam, with metal doors and small windows. Warning signs are posted near the entrance.

The scene is lit by overcast daylight, giving everything a grey, imposing quality. The atmosphere conveys the overwhelming scale of human engineering.""",

    "maze": """A claustrophobic illustration in a detailed painterly style.

A twisting underground passage carved from rough stone. The walls are close, the ceiling low. Shadows pool in every corner.

Multiple passages branch off in different directions, each looking identical to the others. The geometry is disorienting.

A single flickering torch provides the only light, casting dancing shadows that make the walls seem to move.

The atmosphere is oppressive and confusing, a place where one could easily become lost forever.""",
}


def main():
    parser = argparse.ArgumentParser(
        description="Test OmniGen2 with Zork scenes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_omnigen2.py --scene hades_entrance
  python test_omnigen2.py --scene white_house --seed 42
  python test_omnigen2.py --scene custom --prompt "A dragon in a cave"
  python test_omnigen2.py --list-scenes

For low VRAM systems:
  python test_omnigen2.py --scene hades_entrance --cpu-offload
  python test_omnigen2.py --scene hades_entrance --sequential-offload  # < 3GB VRAM
        """,
    )
    parser.add_argument(
        "--scene",
        choices=list(ZORK_SCENES.keys()) + ["custom"],
        default="hades_entrance",
        help="Which scene to generate",
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

    args = parser.parse_args()

    if args.list_scenes:
        print("Available scenes:\n")
        for name, desc in ZORK_SCENES.items():
            first_line = desc.strip().split("\n")[0]
            print(f"  {name}:")
            print(f"    {first_line}\n")
        return

    # Determine prompt
    if args.scene == "custom":
        if not args.prompt:
            print("Error: --prompt required when using --scene custom")
            sys.exit(1)
        prompt = args.prompt
    else:
        prompt = ZORK_SCENES[args.scene]

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
    print(f"Scene: {args.scene}")
    print(f"Output: {args.output}")
    print(f"Size: {args.width}x{args.height}")
    print(f"Steps: {args.steps}")
    print(f"Seed: {args.seed}")
    print(f"Text guidance: {args.text_guidance}")
    if input_images:
        print(f"Reference images: {len(input_images)}")
        print(f"Image guidance: {args.image_guidance}")
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
    )

    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(output_path)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
