# Gnusto - Illustration

Generate illustrations for text adventure games using OmniGen2.

## Setup

```bash
# Clone OmniGen2 repo (if not already done)
cd illustration
git clone https://github.com/OmniGen2/OmniGen2.git omnigen2_repo
pip install -r omnigen2_repo/requirements.txt
cd ..

# Install gnusto (includes illustration CLI)
pip install -e .
```

## Quick Start

```bash
# Generate a scene
illustration --scene white_house --output scene.png

# Custom prompt
illustration --scene custom --prompt "A troll under a bridge" --output troll.png

# List available scenes
illustration --list-scenes

# In-context generation with reference images
illustration --scene custom \
    --reference lantern.png \
    --prompt "A dungeon with the brass lantern from <img1> illuminating stone walls"
```

## Performance

For faster generation on NVIDIA GPUs:

```bash
illustration --scene white_house --taylorseer --cfg-range-end 0.7
```

This achieves ~2.2x speedup. See `illustration/benchmark/RESULTS.md` for detailed benchmarks.

## Hardware

- **CUDA GPU (17GB+ VRAM)**: Full speed with `--dtype bf16`
- **NVIDIA GB10**: Works with CUDA. Requires uninstalling triton (`pip uninstall triton`) due to sm_121 incompatibility. The CLI will detect this and provide instructions.
- **CPU**: Works but slow (~28s/step). Use `--dtype fp32`.

## Documentation

- `illustration/benchmark/RESULTS.md` - Performance benchmarks and optimization guide
- `CLAUDE.md` - Instructions for AI assistants (includes illustration section)
