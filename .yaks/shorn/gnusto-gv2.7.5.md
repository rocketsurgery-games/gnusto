---
id: gnusto-gv2.7.5
title: Prune monotonic state from exploration
type: task
priority: 3
created: '2026-01-24T10:44:14.726163-05:00'
updated: '2026-02-08T19:07:11.067641Z'
---

Implemented monotonic state pruning for exploration:

**Key changes:**
1. Added `get_one_way_flags()` to EffectAnalysis - detects properties that only change in one direction (e.g., rmung: False->True)
2. Added `MonotonicPruner` class in explorer.py - tracks seen states by non-monotonic fingerprint and prunes dominated states
3. Integrated pruning into StateExplorer - automatically enabled when effects analysis is provided
4. Added `states_pruned_monotonic` stat to ExplorationStats

**How it works:**
- One-way flags are identified by static analysis (properties with single target value ≠ initial value)
- States are split into monotonic and non-monotonic parts
- A state is pruned if we've already seen a state with the same non-monotonic values but 'better' monotonic values (closer to final)
- Example: {player@kitchen, rmung=False} is dominated by {player@kitchen, rmung=True}

**Results for LH:**
- 36 one-way flags detected
- Moderate state savings in exploration (varies by tracked refs)
- Enabled automatically when effects are passed to explore_state_space()

This implements domination-based pruning for irreversible state transitions.
