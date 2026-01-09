# FrotzLM

Generate illustrations for text adventure games using OmniGen2.

## Quick Start

```bash
# Install dependencies
pip install -r omnigen2_repo/requirements.txt

# Generate a scene
python test_omnigen2.py --scene white_house --output scene.png

# Custom prompt
python test_omnigen2.py --scene custom --prompt "A troll under a bridge" --output troll.png

# List available scenes
python test_omnigen2.py --list-scenes
```

## Performance

For faster generation on NVIDIA GPUs:

```bash
python test_omnigen2.py --scene white_house --taylorseer --cfg-range-end 0.7
```

This achieves ~2.2x speedup. See `benchmark/RESULTS.md` for detailed benchmarks.

## Hardware

- **CUDA GPU (17GB+ VRAM)**: Full speed with `--dtype bf16`
- **NVIDIA GB10**: Works with CUDA. Flash-attn not needed (SDPA is optimal)
- **CPU**: Works but slow (~28s/step)

## Documentation

- `benchmark/RESULTS.md` - Performance benchmarks and optimization guide
- `CLAUDE.md` - Instructions for AI assistants working on this codebase
