---
id: gnusto-lgz
title: Investigate flash_attn compatibility with GB10
type: task
priority: 3
created: '2026-01-07T23:46:48.417720313-05:00'
updated: '2026-02-08T19:07:11.078039Z'
---

Flash attention provides ~20-30% speedup but may have compatibility issues with NVIDIA GB10 (sm_121a architecture, CUDA capability 12.1). PyTorch currently only supports up to 12.0. Investigate: (1) if flash_attn can be built for sm_121, (2) if newer flash_attn versions support it, (3) workarounds if any.
