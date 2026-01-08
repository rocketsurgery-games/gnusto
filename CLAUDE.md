# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FrotzLM generates illustrations for text adventure games (like Zork) using OmniGen2, a unified diffusion model that handles text-to-image generation with multi-modal conditioning.

## Commands

```bash
# Install dependencies
pip install -r omnigen2_repo/requirements.txt

# Generate an image from a predefined Zork scene
python test_omnigen2.py --scene hades_entrance --output hades.png

# List available scenes
python test_omnigen2.py --list-scenes

# Custom prompt
python test_omnigen2.py --scene custom --prompt "A troll under a bridge" --output troll.png

# Low VRAM options
python test_omnigen2.py --scene hades_entrance --cpu-offload          # ~50% VRAM reduction
python test_omnigen2.py --scene hades_entrance --sequential-offload   # <3GB VRAM, much slower

# Fewer steps for faster iteration (quality tradeoff)
python test_omnigen2.py --scene hades_entrance --steps 10
```

## Architecture

- `test_omnigen2.py` - Main test script with predefined Zork scene prompts and OmniGen2 pipeline wrapper
- `omnigen2_repo/` - Cloned OmniGen2 repository (added to sys.path at runtime)
- Model weights downloaded from HuggingFace (`OmniGen2/OmniGen2`, ~14GB)

## Hardware Notes

- **CUDA GPU (17GB+ VRAM)**: Full speed, use `--dtype bf16`
- **Apple Silicon (MPS)**: Has compatibility issues with OmniGen2's attention implementation. Script defaults to CPU. Use `--force-mps` to try MPS anyway (may crash).
- **CPU**: Works but slow (~28s/step). Uses float32 automatically.

## Issue Tracking

This project uses **bd** (beads) for issue tracking instead of markdown TODOs.

```bash
bd ready                              # Find available work
bd create --title="..." --type=task   # Create new issue
bd update <id> --status=in_progress   # Claim work
bd close <id>                         # Mark complete
bd sync                               # Sync with git remote
```
