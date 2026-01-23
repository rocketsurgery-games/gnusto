# Deferred Frotz Modules

This directory contains modules that have been set aside while we focus on
building a theoretically sound foundation for winnability analysis.

## Why Deferred?

We want to establish a correct, provable implementation of:
1. Constraint back-propagation (backward.py)
2. State space exploration (explorer.py)

Before adding optimization layers like clustering and relevance analysis.

## Modules

### relevance.py

**Purpose**: Forward transitive closure from victory conditions to find
"relevant" state.

**Previous use**:
- Explorer used `relevance.relevant` as fallback for state fingerprinting
- BackwardAnalyzer accepted relevance but never actually used it

**Why deferred**: We now derive state refs directly from constraint
back-propagation via `collect_constraint_refs()`. This is more principled -
we track exactly what the constraints reference, not a forward approximation.

**To restore**: Would need to clarify relationship with backward analysis.
Are they complementary or redundant?

### clustering.py

**Purpose**: Hierarchical state clustering based on constraint satisfaction.
Includes:
- ClusterSignature - bit vectors for constraint satisfaction
- Constraint hierarchy building
- Cluster graph construction
- Dominator tree computation
- Region detection (SCCs)
- DOT visualization

**Previous use**:
- CLI used for --dot, --dominators, --structure, --regions outputs
- Provided ConstraintHierarchy for guided exploration

**Why deferred**: This is optimization on top of basic exploration. We need
to verify the core algorithm works correctly first.

**To restore**: Once constraint back-prop and exploration are verified correct,
clustering can be reintegrated for scalability.

## Restoration

To bring these modules back:
1. Update imports in main frotz modules
2. Add back CLI commands that use them
3. Update tests

The modules should still work - they just aren't imported anywhere.
