# OmniGen2 Inference Optimization Benchmarks

Benchmark results for OmniGen2 on NVIDIA GB10 (Blackwell architecture, sm_121).

## Environment

- **GPU**: NVIDIA GB10
- **Driver**: 580.95.05
- **CUDA**: 13.0
- **PyTorch**: 2.9.1+cu128
- **Python**: 3.11

## Results Summary

All benchmarks run with `--scene white_house --steps 25 --seed 42` at 1024×1024 unless noted.

| Configuration | Gen Time | Per Step | Speedup |
|--------------|----------|----------|---------|
| Baseline | 2:45 | 6.6s | 1.0x |
| TaylorSeer | 1:22 | 3.3s | **2.0x** |
| TeaCache (thresh=0.05) | 2:46 | 6.6s | ~1.0x |
| cfg-range-end=0.7 | 2:22 | 5.7s | 1.2x |
| TaylorSeer + cfg-range-end=0.7 | 1:14 | 3.0s | **2.2x** |
| 512×512 baseline | 0:48 | 1.95s | 3.4x |

## Recommended Configuration

For best speed/quality tradeoff:

```bash
filfre --scene white_house --taylorseer --cfg-range-end 0.7
```

This achieves **2.2x speedup** with minimal quality impact.

## Optimization Details

### TaylorSeer (Recommended)

- **Speedup**: ~2x
- **Flag**: `--taylorseer`
- **How it works**: Caches intermediate transformer computations and reuses them across denoising steps when changes are small
- **Quality impact**: Minimal - output appears visually identical

### cfg-range-end (Recommended)

- **Speedup**: ~14% alone, stacks with TaylorSeer
- **Flag**: `--cfg-range-end 0.7`
- **How it works**: Skips classifier-free guidance computation in final 30% of steps
- **Quality impact**: Minimal - CFG has diminishing returns in later steps

### TeaCache (Not Recommended)

- **Speedup**: None observed at default threshold
- **Flags**: `--teacache --teacache-thresh 0.05`
- **Issue**: Default threshold (0.05) is too conservative, causing nearly all steps to be computed
- **Note**: Higher thresholds may help but risk quality degradation

### Resolution Scaling

- **Scaling**: Roughly linear with pixel count
- **512×512**: 3.4x faster than 1024×1024
- **Use case**: Lower resolution for rapid iteration, full resolution for final output

**Prompt sensitivity at small resolutions**: Certain prompts produce blank/white outputs at smaller sizes:

| Prompt Style | 1024² | 512² | 256² |
|--------------|-------|------|------|
| "detailed illustration of X" | ✅ | ✅ | ✅ |
| "pencil sketch of X" | ✅ | faint | very faint |
| "X on a blank background" | ✅ | ❌ blank | ❌ blank |

**Root cause**: The model interprets "blank/white/empty background" too literally at smaller resolutions where the latent space (32×32 at 256²) leaves less room for both subject and background interpretation.

**Workarounds**:
- Avoid "blank background", "white background", "empty background" at <1024²
- Use vivid prompts ("detailed illustration" vs "pencil sketch")
- Generate at 1024² and downscale if specific style needed

### Scheduler Alternatives (Not Compatible)

DPMSolver++ and Heun schedulers were tested but are incompatible with OmniGen2's pipeline, which passes custom kwargs (`num_tokens`) that other schedulers don't accept.

### Flash Attention (Not Beneficial on GB10)

Investigation of flash-attn compatibility revealed:

- GB10 (sm_121) requires custom compilation with patches
- **Benchmark results show SDPA is 2% faster** than compiled flash-attn on GB10
- Flash-attn kernels fall back to generic PTX code paths without Blackwell optimizations
- OmniGen2 already uses PyTorch SDPA as fallback - this is optimal for GB10

The "Cannot import flash_attn" warnings are harmless and can be ignored.

## CLI Flags Reference

```
Optimization flags:
  --taylorseer          Enable TaylorSeer (~2x speedup)
  --teacache            Enable TeaCache (needs threshold tuning)
  --teacache-thresh N   TeaCache L1 threshold (default: 0.05)
  --cfg-range-end N     CFG range end 0.0-1.0 (default: 1.0)
```

Note: `--taylorseer` and `--teacache` are mutually exclusive.

## Raw Benchmark Logs

Individual benchmark logs are stored in `benchmark/*.log`.
