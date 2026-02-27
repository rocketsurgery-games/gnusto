---
id: gnusto-ds7
title: Benchmark OmniGen2 inference optimizations
type: task
priority: 1
created: '2026-01-07T23:46:13.935162296-05:00'
updated: '2026-02-08T19:07:10.984193Z'
---

Systematically benchmark available OmniGen2 speedup options to find the best quality/speed tradeoff for FrotzLM. Options to test: TaylorSeer (~2x), TeaCache (~30%), DPMSolver++ scheduler, reduced cfg_range, flash_attn, and resolution scaling.
