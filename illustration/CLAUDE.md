# Project Overview

FrotzLM generates illustrations for text adventure games (like Zork) using OmniGen2, a unified diffusion model that handles text-to-image generation with multi-modal conditioning.

# Architecture

- `test_omnigen2.py` - Main script with predefined Zork scene prompts and OmniGen2 pipeline wrapper
- `omnigen2_repo/` - Cloned OmniGen2 repository (added to sys.path at runtime)
- `benchmark/` - Performance benchmarks and optimization results
- Model weights from HuggingFace (`OmniGen2/OmniGen2`, ~14GB)

# Commands

```bash
# Generate an image
python test_omnigen2.py --scene hades_entrance --output hades.png

# With optimizations (2.2x faster)
python test_omnigen2.py --scene white_house --taylorseer --cfg-range-end 0.7

# Custom prompt
python test_omnigen2.py --scene custom --prompt "A troll under a bridge" --output troll.png

# Low VRAM options
python test_omnigen2.py --scene hades_entrance --cpu-offload          # ~50% VRAM reduction
python test_omnigen2.py --scene hades_entrance --sequential-offload   # <3GB VRAM, slower
```

# Hardware Notes

- **NVIDIA GB10**: Works with CUDA. Requires uninstalling triton (incompatible with sm_121). Run tests serially, not in parallel. Flash-attn not beneficial (SDPA is optimal).
- **Apple Silicon (MPS)**: Defaults to CPU due to attention issues. Use `--force-mps` to try anyway.
- **CPU**: Works but slow (~28s/step). Uses float32 automatically.

