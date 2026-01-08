# OmniGen2 Distillation Research

Research into options for creating smaller/faster versions of OmniGen2 for domain-specific IF illustration generation.

## Context

We have a domain-specific use case:
- Fixed visual vocabulary (IF objects, characters, scenes)
- Consistent style (pen/ink, cross-hatching)
- Potential for large training dataset of prompt-image pairs

This document explores distillation and compression options.

## Two Dimensions of Optimization

| Dimension | What Changes | Typical Gains | Approach |
|-----------|--------------|---------------|----------|
| **Fewer Steps** | Inference iterations | 6-10x faster | LCM, progressive distillation, adversarial distillation |
| **Smaller Architecture** | Model parameters | 30-50% smaller | Block pruning + knowledge distillation |

These are orthogonal and can be combined.

---

## Step Reduction Techniques

### Latent Consistency Models (LCM)

The most practical approach for reducing inference steps without changing model size.

| Metric | Before | After |
|--------|--------|-------|
| Steps | 25-50 | 2-4 |
| Inference time | ~4s (A100) | ~0.4s |
| Model size | Unchanged | Unchanged |
| Training cost | - | ~32 A100 hours |

**How it works**: LCMs are trained to directly predict the solution of the probability flow ODE in latent space, eliminating the need for iterative denoising.

**LCM-LoRA variant**: Train only adapter layers (~50-200MB), which can be applied to any fine-tuned version of the base model without re-distillation.

### Progressive Distillation

Iteratively halves sampling steps by training student to match two teacher steps in one.

| Stage | Teacher Steps | Student Steps |
|-------|---------------|---------------|
| 0 | 1024 | 512 |
| 1 | 512 | 256 |
| ... | ... | ... |
| N | 8 | 4 |

Training cost is roughly equivalent to training the original model once.

### Adversarial Diffusion Distillation (ADD)

Used by SDXL-Turbo and FLUX.1 [schnell]. Combines adversarial training with score distillation.

FLUX.1 [schnell] results:
- 1-4 steps vs 20-50 for FLUX.1 [dev]
- 10x faster than FLUX.1 [pro]
- Same 12B parameters

---

## Architecture Compression Techniques

### Block Pruning + Knowledge Distillation (BK-SDM approach)

Remove architectural blocks from U-Net and retrain with knowledge distillation.

**Stable Diffusion v1.4 results**:

| Variant | Parameters | Size Reduction | Speed Gain |
|---------|-----------|----------------|------------|
| Original | 1.04B | - | - |
| BK-SDM-Base | 0.76B | 27% | ~30% |
| BK-SDM-Small | 0.66B | 37% | ~40% |
| BK-SDM-Tiny | 0.50B | 52% | ~43% |

**Training efficiency**: Only 13 A100 days with 0.22M image-text pairs (vs. billions for original).

### SSD-1B (SDXL compression)

- 50% smaller than SDXL (2.6B → 1.3B parameters)
- 60% faster inference
- Uses multi-teacher distillation (SDXL, ZavyChromaXL, JuggernautXL)

---

## OmniGen2-Specific Considerations

### Current State

- **Model size**: ~14GB
- **LoRA fine-tuning**: Officially supported and documented
- **Training code**: Released mid-2025
- **Distillation recipes**: None published

### Fine-tuning (Available Now)

```bash
accelerate launch train.py \
  --model_name_or_path Shitao/OmniGen-v1 \
  --use_lora --lora_rank 8 \
  --json_file ./your_data.jsonl \
  --image_path ./images \
  --max_image_size 1024 \
  --epochs 200 \
  --results_dir ./results/lora_finetune
```

Typical settings for small datasets (20-50 images):
- LoRA rank: 8-16
- Training steps: 2000-3000
- Learning rate: 1e-3

### Challenges for Distillation

1. **Multi-modal in-context conditioning**: The `<img1>`, `<img2>` reference system is unique to OmniGen. Distillation must preserve this capability.

2. **No reference implementation**: Unlike SDXL/FLUX, there's no "OmniGen2-LCM" or "OmniGen2-Tiny" to build from.

3. **Architecture differences**: OmniGen2 uses a unified transformer architecture, not the U-Net used in SD/SDXL. Compression techniques may not transfer directly.

---

## Recommended Approach

### Phase 1: LoRA Fine-tuning

**Goal**: Validate domain lock-in, establish quality baseline.

| Aspect | Estimate |
|--------|----------|
| Training data | 100-500 examples |
| Compute | 20-50 A100 hours |
| Cloud cost | $100-300 |
| Complexity | Low (documented) |
| Result | Same speed/size, better domain quality |

### Phase 2: Step Reduction (LCM-style)

**Goal**: 4-8x faster inference.

| Aspect | Estimate |
|--------|----------|
| Training data | 10k-50k generated examples |
| Compute | 100-200 A100 hours |
| Cloud cost | $500-1000 |
| Complexity | Medium (adapt LCM recipe) |
| Result | Same size, 4-8x faster |

### Phase 3: Architecture Compression (Optional)

**Goal**: Smaller model for deployment constraints.

| Aspect | Estimate |
|--------|----------|
| Training data | Phase 1 dataset + generations |
| Compute | 300-500 A100 hours |
| Cloud cost | $2000-5000 |
| Complexity | High (custom research) |
| Result | ~50% smaller, ~50% faster (stacks with Phase 2) |

---

## Combined Optimization Potential

If all phases succeed:

| Metric | Original | Optimized | Improvement |
|--------|----------|-----------|-------------|
| Model size | 14GB | ~7GB | 50% smaller |
| Inference steps | 30 | 4 | 7.5x fewer |
| Inference time | ~10s | ~0.8s | 12x faster |
| Domain quality | Generic | IF-specialized | Better |

Note: These are theoretical maximums. Actual results depend on:
- How well in-context conditioning survives distillation
- Quality tolerance for compressed architecture
- Domain-specific quality floor

---

## Key Uncertainties

1. **In-context image conditioning preservation**: Unknown if `<img1>` referencing survives aggressive distillation.

2. **Quality vs compression trade-off**: For pen/ink style, artifacts might be more/less visible than in photorealistic domains.

3. **Architecture portability**: BK-SDM techniques target U-Net; OmniGen2's unified transformer may require different approaches.

4. **Training stability**: No published training curves or failure modes for OmniGen2 distillation.

---

## Sources

### OmniGen2
- [OmniGen2 Repository](https://github.com/VectorSpaceLab/OmniGen2)
- [OmniGen Fine-tuning Documentation](https://github.com/VectorSpaceLab/OmniGen/blob/main/docs/fine-tuning.md)
- [OmniGen2 Paper](https://arxiv.org/abs/2506.18871)

### Latent Consistency Models
- [LCM Project Page](https://latent-consistency-models.github.io/)
- [LCM Paper](https://arxiv.org/abs/2310.04378)
- [LCM-LoRA Blog Post](https://huggingface.co/blog/lcm_lora)
- [LCM Distillation Training](https://huggingface.co/docs/diffusers/en/training/lcm_distill)
- [How LCMs Work (Baseten)](https://www.baseten.co/blog/how-latent-consistency-models-work/)

### Progressive Distillation
- [Progressive Distillation Paper](https://arxiv.org/abs/2202.00512)
- [The Paradox of Diffusion Distillation](https://sander.ai/2024/02/28/paradox.html)

### Architecture Compression
- [BK-SDM Paper (ECCV'24)](https://arxiv.org/abs/2305.15798)
- [BK-SDM Repository](https://github.com/Nota-NetsPresso/BK-SDM)
- [SSD-1B Model](https://huggingface.co/segmind/SSD-1B)
- [SSD-1B Announcement](https://blog.segmind.com/introducing-segmind-ssd-1b/)

### FLUX Distillation
- [FLUX.1 [schnell]](https://huggingface.co/black-forest-labs/FLUX.1-schnell)
- [FLUX.2 Turbo Analysis](https://www.techbuddies.io/2025/12/30/fals-flux-2-turbo-how-a-distilled-lora-pushes-open-weight-image-generation-to-production-speeds/)
- [Few-Step Model Comparison](https://www.baseten.co/blog/comparing-few-step-image-generation-models/)

### General
- [Lightweight Diffusion Models Survey](https://link.springer.com/article/10.1007/s10462-024-10800-8)
- [Diffusion Model Compression (CVPR 2025)](https://arxiv.org/html/2504.02011v1)
- [Distilled Stable Diffusion Guide](https://blog.segmind.com/distilledstable-diffusion-models/)

---

*Research conducted January 2026*
