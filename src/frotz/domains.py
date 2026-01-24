"""
Value domain inference for abstract interpretation.

This module analyzes reduced Grue expressions to determine:
1. Write domains: What values can be written to each StatePath
2. Read patterns: How values are compared (equality checks, boolean context)
3. Minimal domains: Optimal abstractions preserving comparison semantics

Key concepts:
- ValueDomain: Represents the set of possible values for a state path
- ReadPattern: How a state path's value is used in conditions
- DomainAnalyzer: Infers domains from effect analysis
- AbstractionConfig: Configuration for state space exploration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, TYPE_CHECKING

from frotz.state import StatePath, DomainConstraint, DomainKind

if TYPE_CHECKING:
    from frotz.effects import EffectAnalysis, PathEffectAnalysis
    from grue import GrueWorld


# =============================================================================
# ValueDomain - Inferred value domains with abstraction support
# =============================================================================


class AbstractionKind(Enum):
    """The kind of abstraction to apply to a value domain."""

    CONCRETE = auto()  # Track exact concrete values
    HELD = auto()       # Abstract to {held, not-held} (2 values)
    BOOLEAN = auto()    # Abstract to truthiness {true, false}
    FINITE = auto()     # Track finite set of values
    UNKNOWN = auto()    # Value is completely unknown (not tracked)


@dataclass(frozen=True)
class ValueDomain:
    """Represents the domain of possible values for a state path.

    Combines:
    - The set of values that can be written (write domain)
    - How the value is read/compared (read pattern)
    - The optimal abstraction for exploration

    Examples:
        ValueDomain.boolean()  # {True, False}
        ValueDomain.held()     # {"@player", NOT_HELD}
        ValueDomain.finite({"@inf-1", "@inf-2", "@inf-3", "@inf-4", "@inf-5"})
    """

    kind: AbstractionKind
    values: frozenset[Any] = field(default_factory=frozenset)  # Concrete values
    abstraction: Callable[[Any], Any] | None = None  # Maps concrete to abstract

    @staticmethod
    def boolean() -> ValueDomain:
        """Boolean domain: True or False."""
        return ValueDomain(
            kind=AbstractionKind.BOOLEAN,
            values=frozenset({True, False}),
        )

    @staticmethod
    def held() -> ValueDomain:
        """Held abstraction: is the object held by @player?

        Abstracts any location value to either "@player" (held) or NOT_HELD.
        """
        return ValueDomain(
            kind=AbstractionKind.HELD,
            values=frozenset({"@player", NOT_HELD}),
            abstraction=lambda v: "@player" if v == "@player" else NOT_HELD,
        )

    @staticmethod
    def finite(values: set[Any]) -> ValueDomain:
        """Finite set of concrete values."""
        return ValueDomain(
            kind=AbstractionKind.FINITE,
            values=frozenset(values),
        )

    @staticmethod
    def concrete(values: set[Any]) -> ValueDomain:
        """Track exact concrete values."""
        return ValueDomain(
            kind=AbstractionKind.CONCRETE,
            values=frozenset(values),
        )

    @staticmethod
    def unknown() -> ValueDomain:
        """Unknown - value is not tracked."""
        return ValueDomain(kind=AbstractionKind.UNKNOWN)

    def abstract(self, value: Any) -> Any:
        """Apply the abstraction function to a concrete value."""
        if self.abstraction:
            return self.abstraction(value)
        return value

    def __len__(self) -> int:
        """Return the number of abstract values."""
        return len(self.values)

    def state_multiplier(self) -> int:
        """Return the state space multiplier for this domain.

        Returns 0 for unknown (not tracked), otherwise the domain size.
        """
        if self.kind == AbstractionKind.UNKNOWN:
            return 0
        return len(self.values)


# Sentinel value for "not held by player"
NOT_HELD = object()


# =============================================================================
# ReadPattern - How state values are used in conditions
# =============================================================================


class ComparisonKind(Enum):
    """The kind of comparison used on a state value."""

    NONE = auto()        # Not used in any comparison
    EQUALITY = auto()    # Equality check: (= value target)
    BOOLEAN = auto()     # Truthiness check: (if value ...)
    HELD_CHECK = auto()  # Held check: (held? @obj) or (= (loc @obj) @player)


@dataclass
class ReadPattern:
    """Describes how a state path's value is used in conditions.

    Tracks:
    - The kinds of comparisons performed
    - The specific values compared against (for equality checks)
    - Whether runtime parameters are involved
    """

    comparisons: set[ComparisonKind] = field(default_factory=set)
    equality_targets: set[Any] = field(default_factory=set)  # Values compared with =
    has_runtime_param: bool = False  # Compared against ?from, ?to, etc.

    def add_equality(self, target: Any):
        """Record an equality comparison against a value."""
        self.comparisons.add(ComparisonKind.EQUALITY)
        self.equality_targets.add(target)

    def add_held_check(self):
        """Record a held? check (equivalent to = @player for location)."""
        self.comparisons.add(ComparisonKind.HELD_CHECK)
        self.equality_targets.add("@player")

    def add_boolean(self):
        """Record a truthiness check."""
        self.comparisons.add(ComparisonKind.BOOLEAN)

    def add_runtime_param(self):
        """Record comparison against a runtime parameter."""
        self.has_runtime_param = True
        self.comparisons.add(ComparisonKind.EQUALITY)


# =============================================================================
# DomainAnalyzer - Infer domains from effect analysis
# =============================================================================


@dataclass
class DomainAnalysis:
    """Results of domain analysis on a game world."""

    # Write domains: what values can be written to each path
    write_domains: dict[StatePath, set[Any]] = field(default_factory=dict)

    # Read patterns: how values are compared
    read_patterns: dict[StatePath, ReadPattern] = field(default_factory=dict)

    # Inferred optimal domains
    domains: dict[StatePath, ValueDomain] = field(default_factory=dict)

    def get_domain(self, path: StatePath) -> ValueDomain:
        """Get the inferred domain for a path, or unknown if not analyzed."""
        return self.domains.get(path, ValueDomain.unknown())

    def summary(self) -> str:
        """Return a human-readable summary."""
        lines = []
        lines.append(f"Analyzed {len(self.domains)} state paths")

        # Group by domain kind
        by_kind: dict[AbstractionKind, list[StatePath]] = {}
        for path, domain in self.domains.items():
            by_kind.setdefault(domain.kind, []).append(path)

        for kind, paths in sorted(by_kind.items(), key=lambda x: x[0].name):
            lines.append(f"\n{kind.name}: {len(paths)} paths")
            for path in sorted(paths, key=str)[:5]:
                domain = self.domains[path]
                lines.append(f"  {path}: {len(domain)} values")
            if len(paths) > 5:
                lines.append(f"  ... and {len(paths) - 5} more")

        return "\n".join(lines)


class DomainAnalyzer:
    """Analyzes effect analysis results to infer optimal value domains.

    The analysis process:
    1. Collect write domains from effect analysis (all values written to each path)
    2. Analyze read patterns (how values are used in conditions)
    3. Compute minimal domains that preserve comparison semantics
    """

    def __init__(self, world: "GrueWorld", effects: "EffectAnalysis"):
        self.world = world
        self.effects = effects
        self.path_effects = effects.to_paths()
        self.analysis = DomainAnalysis()

    def analyze(self) -> DomainAnalysis:
        """Run domain analysis and return results."""
        # Step 1: Collect write domains
        self._collect_write_domains()

        # Step 2: Analyze read patterns
        self._analyze_read_patterns()

        # Step 3: Compute minimal domains
        self._compute_minimal_domains()

        return self.analysis

    def _collect_write_domains(self):
        """Collect all possible values that can be written to each path."""
        for path, behavior_targets in self.path_effects.modifies_to.items():
            values = set()
            for targets in behavior_targets.values():
                values.update(targets)
            # Remove None (unknown values) for now - we'll handle separately
            known_values = {v for v in values if v is not None}
            has_unknown = None in values

            self.analysis.write_domains[path] = known_values

            # If there are unknown values, we can't fully constrain the domain
            if has_unknown:
                # Mark that this path has unknown writes
                self.analysis.read_patterns.setdefault(path, ReadPattern()).has_runtime_param = True

    def _analyze_read_patterns(self):
        """Analyze how each state path's value is used in conditions.

        This walks the game's behaviors looking for comparisons involving
        the state paths we're tracking.
        """
        from grue.sexpr import SList, Symbol, Keyword

        # For each path that's read, analyze what comparisons are made
        for path in self.path_effects.reads:
            pattern = self.analysis.read_patterns.setdefault(path, ReadPattern())

            # Determine what behaviors read this path
            behaviors = self.path_effects.reads.get(path, set())

            # For location paths used with held?, mark as held check
            if path.kind == "loc":
                # Check if any behavior uses held? on this object
                obj = path.object
                for behavior in behaviors:
                    # The behavior reads this location - check if via held?
                    # For now, conservatively mark as held check if object is takeable
                    if obj and obj in self.world.objects:
                        obj_def = self.world.objects[obj]
                        if obj_def.properties.get("takeable", False):
                            pattern.add_held_check()

    def _compute_minimal_domains(self):
        """Compute the minimal domain for each path that preserves semantics.

        The algorithm:
        1. If path only has held checks, use HELD abstraction (2 values)
        2. If path has finite equality targets, use those as the domain
        3. If path has runtime params, use the write domain
        4. Otherwise, use the write domain
        """
        for path in self.path_effects.all_state:
            write_domain = self.analysis.write_domains.get(path, set())
            read_pattern = self.analysis.read_patterns.get(path, ReadPattern())

            # Determine optimal domain
            domain = self._compute_domain_for_path(path, write_domain, read_pattern)
            self.analysis.domains[path] = domain

    def _compute_domain_for_path(
        self,
        path: StatePath,
        write_domain: set[Any],
        read_pattern: ReadPattern
    ) -> ValueDomain:
        """Compute the optimal domain for a single path."""

        # Boolean properties: always use boolean domain
        if path.kind == "prop":
            # Check if the property only takes boolean values
            if write_domain <= {True, False}:
                return ValueDomain.boolean()

        # Location paths with only held checks: use held abstraction
        if path.kind == "loc":
            comparisons = read_pattern.comparisons
            if comparisons == {ComparisonKind.HELD_CHECK}:
                return ValueDomain.held()
            if comparisons == {ComparisonKind.HELD_CHECK, ComparisonKind.EQUALITY}:
                # Check if all equality targets are just @player
                if read_pattern.equality_targets == {"@player"}:
                    return ValueDomain.held()

        # If we have finite write domain, use it
        if write_domain and not read_pattern.has_runtime_param:
            return ValueDomain.finite(write_domain)

        # If we have equality targets from comparisons, use those
        if read_pattern.equality_targets:
            return ValueDomain.finite(read_pattern.equality_targets | write_domain)

        # Fall back to concrete tracking of write domain
        if write_domain:
            return ValueDomain.concrete(write_domain)

        # No information - unknown
        return ValueDomain.unknown()


# =============================================================================
# AbstractionConfig - Configuration for state space exploration
# =============================================================================


@dataclass
class AbstractionConfig:
    """Configuration for abstract state space exploration.

    Bundles:
    - Which state paths to track
    - What value domain each path has
    - How to compute state fingerprints

    This is derived automatically from domain analysis, not manually specified.
    """

    tracked_paths: set[StatePath] = field(default_factory=set)
    domains: dict[StatePath, ValueDomain] = field(default_factory=dict)

    @staticmethod
    def from_analysis(analysis: DomainAnalysis, paths: set[StatePath] | None = None) -> AbstractionConfig:
        """Create an AbstractionConfig from domain analysis results.

        Args:
            analysis: The domain analysis results
            paths: Optional set of paths to track. If None, tracks all analyzed paths.
        """
        if paths is None:
            paths = set(analysis.domains.keys())

        config = AbstractionConfig()
        for path in paths:
            domain = analysis.get_domain(path)
            if domain.kind != AbstractionKind.UNKNOWN:
                config.tracked_paths.add(path)
                config.domains[path] = domain

        return config

    def fingerprint(self, state_values: dict[StatePath, Any]) -> tuple[tuple[StatePath, Any], ...]:
        """Compute an abstract fingerprint from concrete state values.

        The fingerprint is a hashable tuple of (path, abstract_value) pairs,
        suitable for use as a dictionary key for state deduplication.
        """
        items = []
        for path in sorted(self.tracked_paths, key=str):
            if path in state_values:
                concrete = state_values[path]
                domain = self.domains.get(path)
                if domain:
                    abstract = domain.abstract(concrete)
                else:
                    abstract = concrete
                items.append((path, abstract))
        return tuple(items)

    def state_space_estimate(self) -> int:
        """Estimate the state space size as product of domain sizes.

        Returns the product of all tracked domain sizes, which gives an
        upper bound on distinct abstract states.
        """
        product = 1
        for domain in self.domains.values():
            mult = domain.state_multiplier()
            if mult > 0:
                product *= mult
        return product

    def summary(self) -> str:
        """Return a human-readable summary."""
        lines = [f"Tracking {len(self.tracked_paths)} state paths"]
        lines.append(f"Estimated state space: {self.state_space_estimate():,}")

        # Show paths sorted by domain size (largest first)
        sorted_paths = sorted(
            self.tracked_paths,
            key=lambda p: (self.domains.get(p, ValueDomain.unknown()).state_multiplier(), str(p)),
            reverse=True
        )

        lines.append("\nPaths by domain size:")
        for path in sorted_paths[:10]:
            domain = self.domains.get(path, ValueDomain.unknown())
            lines.append(f"  {path}: {domain.kind.name} ({len(domain)} values)")
        if len(sorted_paths) > 10:
            lines.append(f"  ... and {len(sorted_paths) - 10} more")

        return "\n".join(lines)


# =============================================================================
# Convenience functions
# =============================================================================


def analyze_domains(world: "GrueWorld", effects: "EffectAnalysis") -> DomainAnalysis:
    """Convenience function to analyze value domains for a world."""
    analyzer = DomainAnalyzer(world, effects)
    return analyzer.analyze()


def infer_abstraction(
    world: "GrueWorld",
    effects: "EffectAnalysis",
    paths: set[StatePath] | None = None,
    include_player_loc: bool = True,
) -> AbstractionConfig:
    """Infer the optimal abstraction configuration for exploration.

    This is the main entry point for Phase 4 integration:

    1. Analyzes the game to find write domains and read patterns
    2. Computes minimal value domains for each state path
    3. Returns an AbstractionConfig ready for use with the explorer

    Args:
        world: The Grue game world
        effects: Effect analysis results
        paths: Optional set of paths to track. If None, tracks all relevant paths.
        include_player_loc: If True, always include player location (default True).
            Player location is needed for exploration even though its domain
            can't be statically inferred.
    """
    analysis = analyze_domains(world, effects)
    config = AbstractionConfig.from_analysis(analysis, paths)

    # Player location is special - we can't infer its domain statically
    # (it depends on runtime parameters), but we need to track it for
    # exploration to work properly. Add it with a concrete (empty) domain.
    if include_player_loc:
        player_path = StatePath.loc(world.player)
        if player_path not in config.tracked_paths:
            tracked = set(config.tracked_paths)
            tracked.add(player_path)
            domains = dict(config.domains)
            domains[player_path] = ValueDomain.concrete(set())
            config = AbstractionConfig(tracked_paths=tracked, domains=domains)

    return config


def state_refs_to_paths(refs: set) -> set[StatePath]:
    """Convert legacy StateRef objects to StatePath objects.

    This bridges backward analysis (which produces StateRefs) with
    domain inference (which works on StatePaths).

    Conversion rules:
    - LocationRef(@obj) -> loc(@obj)
    - PropertyRef(@obj, prop) -> prop(@obj, prop)
    - HeldRef(@obj) -> loc(@obj)  # Domain inference will give HELD abstraction
    - QueueRef(event) -> queue(event)
    """
    from .effects import LocationRef, PropertyRef, HeldRef, QueueRef

    paths = set()
    for ref in refs:
        if isinstance(ref, LocationRef):
            paths.add(StatePath.loc(ref.object))
        elif isinstance(ref, PropertyRef):
            paths.add(StatePath.prop(ref.object, ref.property))
        elif isinstance(ref, HeldRef):
            # HeldRef maps to location - domain inference will correctly
            # give it HELD abstraction if it's only used in held? checks
            paths.add(StatePath.loc(ref.object))
        elif isinstance(ref, QueueRef):
            paths.add(StatePath.queue(ref.event))
    return paths
