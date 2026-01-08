# CLAUDE.md

Instructions for AI assistants working on this codebase.

## Project Overview

FrotzLM generates illustrations for text adventure games (like Zork) using OmniGen2, a unified diffusion model that handles text-to-image generation with multi-modal conditioning.

## Architecture

- `test_omnigen2.py` - Main script with predefined Zork scene prompts and OmniGen2 pipeline wrapper
- `omnigen2_repo/` - Cloned OmniGen2 repository (added to sys.path at runtime)
- `benchmark/` - Performance benchmarks and optimization results
- Model weights from HuggingFace (`OmniGen2/OmniGen2`, ~14GB)

## Commands

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

## Hardware Notes

- **NVIDIA GB10**: Works with CUDA. Requires uninstalling triton (incompatible with sm_121). Run tests serially, not in parallel. Flash-attn not beneficial (SDPA is optimal).
- **Apple Silicon (MPS)**: Defaults to CPU due to attention issues. Use `--force-mps` to try anyway.
- **CPU**: Works but slow (~28s/step). Uses float32 automatically.

## Issue Tracking

This project uses **bd** (beads) for issue tracking.

```bash
bd ready                              # Find available work
bd show <id>                          # View issue details
bd create --title="..." --type=task   # Create new issue
bd update <id> --status=in_progress   # Claim work
bd close <id>                         # Mark complete
bd sync                               # Sync with git remote
```

## Session Completion Workflow

When ending a work session, complete ALL steps. Work is NOT complete until `git push` succeeds.

1. **File issues** for remaining work
2. **Run quality gates** if code changed (tests, linters, builds)
3. **Update issue status** - close finished work, update in-progress items
4. **Push to remote** (MANDATORY):
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # Must show "up to date with origin"
   ```
5. **Verify** all changes committed AND pushed
6. **Hand off** - provide context for next session

**Rules:**
- Work is NOT complete until `git push` succeeds
- Never stop before pushing - that leaves work stranded locally
- If push fails, resolve and retry until it succeeds
