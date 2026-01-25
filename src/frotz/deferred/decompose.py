"""
Subproblem decomposition for guided state-space exploration.

This module provides a thin wrapper around the backward constraint propagation
system (backward.py) to define exploration subproblems. Each subproblem represents
a constraint that must be achieved, with defined start/end state conditions.

The goal is to make full state-space exploration tractable by breaking it into
smaller pieces:
1. Build constraint tree from victory condition (via backward.py)
2. Each constraint node becomes a subproblem boundary
3. Explore from "parent constraints satisfied" to "this constraint satisfied"

This approach leverages the constraint tree's dependency ordering rather than
trying to independently identify "irreversible" state changes.
"""

from dataclasses import dataclass, field
from typing import Any

from grue import GrueWorld

from .backward import (
    BackwardAnalyzer,
    Constraint,
    ConstraintNode,
    ConstraintTree,
    build_victory_constraints,
    collect_constraint_refs,
)
from .effects import (
    EffectAnalysis,
    StateRef,
    PropertyRef,
    LocationRef,
    analyze_effects,
)


@dataclass
class Subproblem:
    """A subproblem for guided exploration.

    Each subproblem represents achieving a specific constraint. The exploration
    should start from states where all parent constraints are satisfied and
    explore until this constraint is satisfied.

    Attributes:
        constraint: The constraint to achieve
        parent_constraints: Constraints that must be satisfied before this one
        is_initial: True if constraint is satisfied in initial state (leaf node)
        is_root: True if this is the root/goal constraint
    """
    constraint: Constraint
    parent_constraints: list[Constraint] = field(default_factory=list)
    is_initial: bool = False
    is_root: bool = False

    def __str__(self):
        if self.is_initial:
            return f"{self.constraint} [INITIAL]"
        elif self.is_root:
            return f"{self.constraint} [ROOT/GOAL]"
        else:
            parents = ", ".join(str(p) for p in self.parent_constraints)
            return f"{self.constraint} <- [{parents}]"

    @property
    def state_ref(self) -> StateRef:
        """The state reference this subproblem targets."""
        return self.constraint.ref

    @property
    def target_value(self) -> Any:
        """The value the state ref should have when this subproblem is solved."""
        return self.constraint.value


@dataclass
class DecompositionResult:
    """Result of decomposing a goal into subproblems."""
    root_constraint: Constraint
    subproblems: dict[Constraint, Subproblem]
    constraint_tree: ConstraintTree  # Original tree for reference

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [f"=== Decomposition: {self.root_constraint} ===", ""]

        # Show in dependency order (BFS from root)
        visited: set[Constraint] = set()
        queue = [self.root_constraint]
        depth: dict[Constraint, int] = {self.root_constraint: 0}

        while queue:
            constraint = queue.pop(0)
            if constraint in visited:
                continue
            visited.add(constraint)

            sp = self.subproblems.get(constraint)
            if sp:
                indent = "  " * depth[constraint]
                lines.append(f"{indent}{sp}")
                for parent in sp.parent_constraints:
                    if parent not in depth:
                        depth[parent] = depth[constraint] + 1
                        queue.append(parent)

        lines.append("")
        lines.append(f"Total subproblems: {len(self.subproblems)}")
        initial_count = sum(1 for sp in self.subproblems.values() if sp.is_initial)
        lines.append(f"Initial (leaf) nodes: {initial_count}")

        return "\n".join(lines)

    def to_dot(self) -> str:
        """Generate DOT graph of subproblem dependencies."""
        lines = [
            "digraph decomposition {",
            '  rankdir=BT;',  # Bottom to top (goals at top)
            '  node [shape=box fontsize=10 fontname="Helvetica"];',
            "",
        ]

        # Node definitions
        for constraint, sp in self.subproblems.items():
            label = str(constraint).replace("@", "").replace(":", "\\n")
            node_id = self._constraint_id(constraint)

            if sp.is_root:
                style = 'style=filled fillcolor=palegreen'
            elif sp.is_initial:
                style = 'style=filled fillcolor=lightblue'
            else:
                style = ''

            lines.append(f'  {node_id} [label="{label}" {style}];')

        lines.append("")

        # Edges (from depends on to)
        for constraint, sp in self.subproblems.items():
            from_id = self._constraint_id(constraint)
            for parent in sp.parent_constraints:
                # Skip self-referential edges
                if parent == constraint:
                    continue
                to_id = self._constraint_id(parent)
                lines.append(f'  {from_id} -> {to_id};')

        lines.append("}")
        return "\n".join(lines)

    def _constraint_id(self, constraint: Constraint) -> str:
        """Generate a valid DOT node ID for a constraint."""
        import re
        ref_str = str(constraint.ref)
        val_str = str(constraint.value)
        op_str = constraint.operator
        # Sanitize to only allow alphanumeric and underscore
        def sanitize(s: str) -> str:
            return re.sub(r'[^a-zA-Z0-9]', '_', s)
        return f"c_{sanitize(ref_str)}_{sanitize(op_str)}_{sanitize(val_str)}"

    def get_state_refs(self) -> set[StateRef]:
        """Get all state refs referenced by subproblems."""
        return {sp.constraint.ref for sp in self.subproblems.values()}


def decompose_from_tree(tree: ConstraintTree) -> DecompositionResult:
    """Convert a constraint tree into subproblems.

    Each ConstraintNode becomes a Subproblem. The node's children become
    parent_constraints (things that must be achieved first).
    """
    subproblems: dict[Constraint, Subproblem] = {}

    def process_node(node: ConstraintNode, is_root: bool = False):
        if node.constraint in subproblems:
            return

        # Collect parent constraints from children
        parent_constraints = list(node.children.keys())

        sp = Subproblem(
            constraint=node.constraint,
            parent_constraints=parent_constraints,
            is_initial=node.is_initial or node.is_constant,
            is_root=is_root,
        )
        subproblems[node.constraint] = sp

        # Recursively process children
        for child in node.children.values():
            process_node(child)

    process_node(tree.root, is_root=True)

    return DecompositionResult(
        root_constraint=tree.root.constraint,
        subproblems=subproblems,
        constraint_tree=tree,
    )


def decompose_victory(
    world: GrueWorld,
    effects: EffectAnalysis | None = None,
    max_depth: int = 15,
) -> list[DecompositionResult]:
    """Decompose victory conditions into subproblems.

    Returns a list of DecompositionResult, one per victory constraint tree.
    """
    if effects is None:
        effects = analyze_effects(world)

    trees = build_victory_constraints(world, effects)
    return [decompose_from_tree(tree) for tree in trees]


def decompose_goal(
    world: GrueWorld,
    ref: StateRef,
    value: Any,
    effects: EffectAnalysis | None = None,
    max_depth: int = 15,
) -> DecompositionResult:
    """Decompose a specific goal into subproblems.

    This is useful for testing or analyzing specific constraints.
    """
    if effects is None:
        effects = analyze_effects(world)

    analyzer = BackwardAnalyzer(world, effects)
    constraint = Constraint(ref, "=", value)
    tree = analyzer.build_tree(constraint, max_depth=max_depth)

    return decompose_from_tree(tree)


# CLI entry point
def main():
    """Command-line interface for decomposition."""
    import sys
    from pathlib import Path
    from grue import load_grue

    if len(sys.argv) < 2:
        print("Usage: python -m frotz.decompose <game_path> [--dot output.dot]")
        print()
        print("Decomposes the victory condition into subproblems using")
        print("backward constraint propagation.")
        sys.exit(1)

    game_path = Path(sys.argv[1])
    dot_output = None

    if "--dot" in sys.argv:
        dot_idx = sys.argv.index("--dot")
        if dot_idx + 1 < len(sys.argv):
            dot_output = sys.argv[dot_idx + 1]

    world = load_grue(str(game_path))
    effects = analyze_effects(world)

    print(f"Decomposing: {world.name or game_path}")
    print()

    results = decompose_victory(world, effects)

    if not results:
        print("No victory conditions found.")
        sys.exit(0)

    for i, result in enumerate(results):
        if len(results) > 1:
            print(f"--- Victory constraint {i+1} ---")
        print(result.summary())
        print()

        if dot_output:
            # If multiple results, append index to filename
            if len(results) > 1:
                base, ext = dot_output.rsplit(".", 1) if "." in dot_output else (dot_output, "dot")
                out_path = f"{base}_{i+1}.{ext}"
            else:
                out_path = dot_output

            Path(out_path).write_text(result.to_dot())
            print(f"DOT graph written to: {out_path}")


if __name__ == "__main__":
    main()
