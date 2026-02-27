---
id: gnusto-6q1
title: Static analysis theoretical limits
type: task
priority: 2
created: '2026-01-22T13:01:40.759366-05:00'
updated: '2026-02-08T19:07:11.000629Z'
---

## Purpose
Track theoretical/computability limitations we encounter in static analysis, and research whether constraints can make them tractable.

## Current Status (2026-01-22)

All limitations have **sound conservative fallbacks** - we never make incorrect claims, we just lose precision.

### 1. Dynamic Values ✅ HANDLED
Expressions like `(move @frob ,(loc @player))` compute destination at runtime.

**Current handling:** `_extract_literal_value` returns `None` for dynamic expressions.
**Fallback:** `_filter_modifiers_by_target` includes behaviors with unknown targets conservatively.
**Sound:** Yes - never miss real achievers
**Complete:** No - may include false achievers

### 2. Recursive Functions ✅ HANDLED
If functions can recurse, full inlining is impossible.

**Current handling:** `_inlining_stack` and `_inline_stack_*` detect cycles during traversal.
**Fallback:** Skip recursive paths, don't descend into same function twice.
**Sound:** Yes - won't infinite loop, won't make false claims
**Complete:** No - may miss effects inside recursive paths

### 3. Higher-Order Functions 🚫 N/A
If functions take functions as arguments (unlikely in Grue).

**Current:** Not relevant - Grue doesn't support HOF yet.
**Theory:** Would require flow analysis to track function identity.

### 4. Event Queue Ordering ✅ SIMPLIFIED
Multiple queued events can fire in different orders depending on timing.

**Current handling:** Queue modeled as boolean (queued/not queued), not ordered list.
**Fallback:** Any queue behavior is potential achiever regardless of order.
**Sound:** Yes - conservative
**Complete:** No - loses ordering information, may include impossible paths

### 5. Local Variable Bindings ✅ HANDLED
Conditions like `(= ?socket @input-socket)` depend on function arguments.

**Current handling:** `_condition_to_constraint` returns `None` for variable references.
**Fallback:** Skip constraint - just loses precision.
**Sound:** Yes - never claims false constraints
**Complete:** No - loses precision on argument-dependent branches

## Summary Table

| Limitation | Status | Sound? | Complete? | Notes |
|------------|--------|--------|-----------|-------|
| Dynamic values | ✅ Handled | Yes | No | False positives OK |
| Recursive functions | ✅ Handled | Yes | No | Skip on cycle |
| Higher-order functions | N/A | - | - | Not in Grue |
| Event queue ordering | ✅ Simplified | Yes | No | Boolean model |
| Local variables | ✅ Handled | Yes | No | Skip condition |

## Research Questions
- What subset of Grue is decidable for effect analysis?
- Can we define "analyzable Grue" restrictions that preserve expressiveness?
- Are there standard IF patterns that map to known tractable analysis classes?

## References
- Abstract interpretation (Cousot)
- Flow analysis for functional languages
- Model checking for event-driven systems
