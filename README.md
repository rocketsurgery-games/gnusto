# Gnusto - Illustration

Generate illustrations for text adventure games using OmniGen2.

## Setup

```bash
# Initialize submodules
git submodule update --init

# Install OmniGen2 dependencies
pip install -r vendor/omnigen2/requirements.txt

# Install gnusto (includes filfre CLI)
pip install -e .
```

## Quick Start

```bash
# Generate a scene
filfre --scene white_house --output scene.png

# Custom prompt
filfre --scene custom --prompt "A troll under a bridge" --output troll.png

# List available scenes
filfre --list-scenes

# In-context generation with reference images
filfre --scene custom \
    --reference lantern.png \
    --prompt "A dungeon with the brass lantern from <img1> illuminating stone walls"
```

## Performance

For faster generation on NVIDIA GPUs:

```bash
filfre --scene white_house --taylorseer --cfg-range-end 0.7
```

This achieves ~2.2x speedup. See `illustration/benchmark/RESULTS.md` for detailed benchmarks.

## Hardware

- **CUDA GPU (17GB+ VRAM)**: Full speed with `--dtype bf16`
- **NVIDIA GB10**: Works with CUDA. Requires uninstalling triton (`pip uninstall triton`) due to sm_121 incompatibility. The CLI will detect this and provide instructions.
- **CPU**: Works but slow (~28s/step). Use `--dtype fp32`.

## Documentation

- `illustration/benchmark/RESULTS.md` - Performance benchmarks and optimization guide
- `CLAUDE.md` - Instructions for AI assistants (includes illustration section)
