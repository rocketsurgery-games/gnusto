"""
Relevance analysis pass for Grue games.

Starting from victory/defeat conditions, works backwards to find the
minimal set of state that affects winnability.

This is "backward slicing" - starting from what we care about (victory)
and tracing back through data dependencies to find what matters.
"""

from dataclasses import dataclass, field
from typing import Any

from grue import GrueWorld
from grue.sexpr import SList, Symbol, Keyword

from .effects import (
    EffectAnalysis,
    StateRef,
    PropertyRef,
    LocationRef,
    QueueRef,
    BehaviorRef,
)


@dataclass
class RelevanceAnalysis:
    """Results of relevance analysis."""

    # State directly referenced by victory/defeat conditions
    victory_refs: set[StateRef] = field(default_factory=set)
    defeat_refs: set[StateRef] = field(default_factory=set)

    # Transitively relevant state (what can affect victory)
    relevant: set[StateRef] = field(default_factory=set)

    # Behaviors that can affect relevant state
    relevant_behaviors: set[BehaviorRef] = field(default_factory=set)

    # State that is modifiable but not relevant (can be ignored)
    irrelevant_modifiable: set[StateRef] = field(default_factory=set)

    def summary(self) -> str:
        """Return a human-readable summary."""
        lines = []
        lines.append(f"Victory condition references: {len(self.victory_refs)}")
        lines.append(f"Defeat condition references: {len(self.defeat_refs)}")
        lines.append(f"Transitively relevant state: {len(self.relevant)}")
        lines.append(f"Relevant behaviors: {len(self.relevant_behaviors)}")
        lines.append(f"Irrelevant modifiable state: {len(self.irrelevant_modifiable)}")
        lines.append("")

        if self.victory_refs:
            lines.append("Victory depends on:")
            for ref in sorted(self.victory_refs, key=str):
                lines.append(f"  {ref}")
            lines.append("")

        if self.defeat_refs:
            lines.append("Defeat depends on:")
            for ref in sorted(self.defeat_refs, key=str):
                lines.append(f"  {ref}")
            lines.append("")

        if self.relevant:
            lines.append("Puzzle-relevant state:")
            for ref in sorted(self.relevant, key=str):
                lines.append(f"  {ref}")
            lines.append("")

        if self.irrelevant_modifiable:
            lines.append("Modifiable but irrelevant:")
            for ref in sorted(self.irrelevant_modifiable, key=str):
                lines.append(f"  {ref}")

        return "\n".join(lines)


class RelevanceAnalyzer:
    """Computes the victory-relevant slice of game state."""

    def __init__(self, world: GrueWorld, effects: EffectAnalysis):
        self.world = world
        self.effects = effects
        self.analysis = RelevanceAnalysis()

    def analyze(self) -> RelevanceAnalysis:
        """Run the analysis and return results."""
        # Step 1: Find state directly referenced by victory/defeat
        self._extract_condition_refs()

        # Step 2: Compute transitive closure
        self._compute_relevant_closure()

        # Step 3: Find irrelevant modifiable state
        self._compute_irrelevant()

        return self.analysis

    def _extract_condition_refs(self):
        """Extract state references from victory and defeat conditions."""
        if self.world.victory:
            refs = self._walk_expr_for_refs(self.world.victory.when)
            self.analysis.victory_refs.update(refs)

        if self.world.defeat:
            for defeat in self.world.defeat.values():
                refs = self._walk_expr_for_refs(defeat.when)
                self.analysis.defeat_refs.update(refs)

    def _walk_expr_for_refs(self, expr: Any) -> set[StateRef]:
        """Walk an expression and collect all state references."""
        refs: set[StateRef] = set()

        if expr is None:
            return refs

        if isinstance(expr, Symbol):
            # Object reference by itself doesn't read state
            # (we need property access or loc check)
            return refs

        if isinstance(expr, (str, int, float, bool, Keyword)):
            return refs

        if isinstance(expr, SList):
            items = expr.items
            if not items:
                return refs

            head = items[0]
            if isinstance(head, Symbol):
                name = head.name

                # Location check: (loc @obj)
                if name == "loc" and len(items) >= 2:
                    obj = items[1]
                    if isinstance(obj, Symbol) and obj.name.startswith("@"):
                        refs.add(LocationRef(obj.name))
                    return refs

                # Location check: (= (loc @obj) @room)
                # Already handled by recursive walk

                # Held check: (held? @obj)
                if name == "held?" and len(items) >= 2:
                    obj = items[1]
                    if isinstance(obj, Symbol) and obj.name.startswith("@"):
                        refs.add(LocationRef(obj.name))
                    return refs

                # Room check: (in-room? @obj @room ...)
                if name == "in-room?" and len(items) >= 2:
                    obj = items[1]
                    if isinstance(obj, Symbol) and obj.name.startswith("@"):
                        refs.add(LocationRef(obj.name))
                    return refs

                # Queue check: (queued? event)
                if name == "queued?" and len(items) >= 2:
                    event = items[1]
                    event_name = event.name if isinstance(event, Symbol) else str(event)
                    refs.add(QueueRef(event_name))
                    return refs

            # Keyword-as-function: (:prop @obj)
            if isinstance(head, Keyword) and len(items) >= 2:
                obj = items[1]
                if isinstance(obj, Symbol) and obj.name.startswith("@"):
                    refs.add(PropertyRef(obj.name, head.name))
                # Still walk remaining args
                for item in items[2:]:
                    refs.update(self._walk_expr_for_refs(item))
                return refs

            # Default: walk all children
            for item in items:
                refs.update(self._walk_expr_for_refs(item))

        elif isinstance(expr, list):
            for item in expr:
                refs.update(self._walk_expr_for_refs(item))

        return refs

    def _compute_relevant_closure(self):
        """Compute transitive closure of relevant state.

        Algorithm:
        1. Start with victory/defeat refs as the "frontier"
        2. For each state ref in frontier:
           - Find behaviors that can modify it
           - Find state refs those behaviors read (preconditions)
           - Add those to relevant set
        3. Repeat until no new refs added
        """
        # Seed with direct condition refs
        relevant = set(self.analysis.victory_refs) | set(self.analysis.defeat_refs)
        frontier = set(relevant)

        while frontier:
            new_frontier: set[StateRef] = set()

            for ref in frontier:
                # Find behaviors that modify this state
                modifiers = self.effects.modifies.get(ref, set())

                for behavior in modifiers:
                    self.analysis.relevant_behaviors.add(behavior)

                    # Find what this behavior reads (its preconditions)
                    for read_ref, readers in self.effects.reads.items():
                        if behavior in readers:
                            if read_ref not in relevant:
                                new_frontier.add(read_ref)

            relevant.update(new_frontier)
            frontier = new_frontier

        self.analysis.relevant = relevant

    def _compute_irrelevant(self):
        """Find modifiable state that doesn't affect victory."""
        modifiable = set(self.effects.modifies.keys())
        self.analysis.irrelevant_modifiable = modifiable - self.analysis.relevant


def analyze_relevance(world: GrueWorld, effects: EffectAnalysis) -> RelevanceAnalysis:
    """Convenience function to analyze relevance."""
    analyzer = RelevanceAnalyzer(world, effects)
    return analyzer.analyze()
