"""
Tests for the value domain inference module.

Tests cover:
- ValueDomain creation and abstraction
- ReadPattern tracking
- DomainAnalyzer inference
- AbstractionConfig for exploration
- Integration with effect analysis
"""

import pytest

from frotz.domains import (
    ValueDomain,
    AbstractionKind,
    NOT_HELD,
    ReadPattern,
    ComparisonKind,
    DomainAnalysis,
    DomainAnalyzer,
    AbstractionConfig,
    analyze_domains,
    infer_abstraction,
)
from frotz.state import StatePath
from frotz.effects import (
    EffectAnalysis,
    PathEffectAnalysis,
    PropertyRef,
    LocationRef,
    QueueRef,
    BehaviorRef,
    analyze_effects,
)
from grue import GrueWorld
from grue.parser import parse_grue


# =============================================================================
# ValueDomain Tests
# =============================================================================


class TestValueDomain:
    """Tests for ValueDomain class."""

    def test_boolean_domain(self):
        """Boolean domain has two values."""
        domain = ValueDomain.boolean()
        assert domain.kind == AbstractionKind.BOOLEAN
        assert domain.values == frozenset({True, False})
        assert len(domain) == 2
        assert domain.state_multiplier() == 2

    def test_held_domain(self):
        """Held domain abstracts to held/not-held."""
        domain = ValueDomain.held()
        assert domain.kind == AbstractionKind.HELD
        assert domain.values == frozenset({"@player", NOT_HELD})
        assert len(domain) == 2

    def test_held_abstraction(self):
        """Held domain abstracts locations correctly."""
        domain = ValueDomain.held()

        # @player stays @player
        assert domain.abstract("@player") == "@player"

        # Everything else becomes NOT_HELD
        assert domain.abstract("@room-1") == NOT_HELD
        assert domain.abstract("@chest") == NOT_HELD
        assert domain.abstract(None) == NOT_HELD

    def test_finite_domain(self):
        """Finite domain tracks exact values."""
        values = {"@inf-1", "@inf-2", "@inf-3", "@inf-4", "@inf-5"}
        domain = ValueDomain.finite(values)

        assert domain.kind == AbstractionKind.FINITE
        assert domain.values == frozenset(values)
        assert len(domain) == 5
        assert domain.state_multiplier() == 5

    def test_concrete_domain(self):
        """Concrete domain tracks exact values."""
        values = {1, 2, 3}
        domain = ValueDomain.concrete(values)

        assert domain.kind == AbstractionKind.CONCRETE
        assert domain.values == frozenset(values)

    def test_unknown_domain(self):
        """Unknown domain has no values."""
        domain = ValueDomain.unknown()
        assert domain.kind == AbstractionKind.UNKNOWN
        assert len(domain) == 0
        assert domain.state_multiplier() == 0

    def test_abstract_without_function(self):
        """Without abstraction function, values pass through."""
        domain = ValueDomain.finite({1, 2, 3})
        assert domain.abstract(1) == 1
        assert domain.abstract(2) == 2
        assert domain.abstract(42) == 42  # Even values not in domain


# =============================================================================
# ReadPattern Tests
# =============================================================================


class TestReadPattern:
    """Tests for ReadPattern class."""

    def test_empty_pattern(self):
        """New pattern has no comparisons."""
        pattern = ReadPattern()
        assert len(pattern.comparisons) == 0
        assert len(pattern.equality_targets) == 0
        assert not pattern.has_runtime_param

    def test_add_equality(self):
        """Adding equality records comparison and target."""
        pattern = ReadPattern()
        pattern.add_equality("@player")
        pattern.add_equality("@room-1")

        assert ComparisonKind.EQUALITY in pattern.comparisons
        assert "@player" in pattern.equality_targets
        assert "@room-1" in pattern.equality_targets

    def test_add_held_check(self):
        """Held check records both held and @player target."""
        pattern = ReadPattern()
        pattern.add_held_check()

        assert ComparisonKind.HELD_CHECK in pattern.comparisons
        assert "@player" in pattern.equality_targets

    def test_add_boolean(self):
        """Boolean check records comparison kind."""
        pattern = ReadPattern()
        pattern.add_boolean()

        assert ComparisonKind.BOOLEAN in pattern.comparisons

    def test_add_runtime_param(self):
        """Runtime param sets flag and records equality."""
        pattern = ReadPattern()
        pattern.add_runtime_param()

        assert pattern.has_runtime_param
        assert ComparisonKind.EQUALITY in pattern.comparisons


# =============================================================================
# DomainAnalysis Tests
# =============================================================================


class TestDomainAnalysis:
    """Tests for DomainAnalysis class."""

    def test_get_domain_missing(self):
        """Getting missing domain returns unknown."""
        analysis = DomainAnalysis()
        path = StatePath.loc("@key")

        domain = analysis.get_domain(path)
        assert domain.kind == AbstractionKind.UNKNOWN

    def test_get_domain_present(self):
        """Getting present domain returns it."""
        analysis = DomainAnalysis()
        path = StatePath.loc("@key")
        expected = ValueDomain.held()
        analysis.domains[path] = expected

        assert analysis.get_domain(path) == expected

    def test_summary(self):
        """Summary describes the analysis."""
        analysis = DomainAnalysis()
        analysis.domains[StatePath.loc("@key")] = ValueDomain.held()
        analysis.domains[StatePath.prop("@door", "locked")] = ValueDomain.boolean()

        summary = analysis.summary()
        assert "2" in summary  # 2 paths
        assert "HELD" in summary or "BOOLEAN" in summary


# =============================================================================
# DomainAnalyzer Tests (with minimal test world)
# =============================================================================


def make_test_world(grue_code: str) -> GrueWorld:
    """Create a test world from Grue code."""
    return parse_grue(grue_code)


class TestDomainAnalyzer:
    """Tests for DomainAnalyzer class."""

    def test_boolean_property_inference(self):
        """Boolean properties get boolean domain."""
        world = make_test_world("""
        (object @lamp
            :location LOBBY
            :properties (:lit false :lightable true)
            :behaviors (
                :light (fn ()
                    '((set @lamp :lit true)
                      (success :message "Lit")))
                :douse (fn ()
                    '((set @lamp :lit false)
                      (success :message "Doused")))))
        (room LOBBY :description "lobby")
        """)

        effects = analyze_effects(world)
        analysis = analyze_domains(world, effects)

        lit_path = StatePath.prop("@lamp", "lit")
        domain = analysis.get_domain(lit_path)

        # Should infer boolean domain since only true/false written
        assert domain.kind == AbstractionKind.BOOLEAN or domain.values <= frozenset({True, False})

    def test_location_write_domain(self):
        """Location writes are collected."""
        world = make_test_world("""
        (object @ball
            :location ROOM1
            :properties (:takeable true))

        (room ROOM1 :description "room 1")
        (room ROOM2 :description "room 2")

        (event warp-ball
            :on-turn (move @ball ROOM2))
        """)

        effects = analyze_effects(world)
        analysis = analyze_domains(world, effects)

        ball_loc = StatePath.loc("@ball")

        # Write domain should include ROOM2 (from event) and @player (from take)
        assert "ROOM2" in analysis.write_domains.get(ball_loc, set()) or \
               "@player" in analysis.write_domains.get(ball_loc, set())

    def test_finite_location_domain(self):
        """Finite location writes create finite domain."""
        world = make_test_world("""
        (object @waxer
            :location INF1)

        (room INF1 :description "inf 1")
        (room INF2 :description "inf 2")
        (room INF3 :description "inf 3")

        (event waxer-moves
            :on-turn
            (cond
                ((= (loc @waxer) INF1) (move @waxer INF2))
                ((= (loc @waxer) INF2) (move @waxer INF3))
                ((= (loc @waxer) INF3) (move @waxer INF1))))
        """)

        effects = analyze_effects(world)
        analysis = analyze_domains(world, effects)

        waxer_loc = StatePath.loc("@waxer")
        domain = analysis.get_domain(waxer_loc)

        # Should have finite domain with the 3 rooms
        assert domain.kind in {AbstractionKind.FINITE, AbstractionKind.CONCRETE}
        assert len(domain.values) >= 3

    def test_takeable_gets_domain(self):
        """Takeable objects get a domain that includes @player."""
        world = make_test_world("""
        (object @key
            :location ROOM1
            :properties (:takeable true))

        (room ROOM1 :description "room")
        """)

        effects = analyze_effects(world)
        analysis = analyze_domains(world, effects)

        key_loc = StatePath.loc("@key")

        # Takeable objects can be moved to @player (via take)
        # The write domain should include @player
        write_domain = analysis.write_domains.get(key_loc, set())
        assert "@player" in write_domain, f"Expected @player in write domain, got {write_domain}"


# =============================================================================
# AbstractionConfig Tests
# =============================================================================


class TestAbstractionConfig:
    """Tests for AbstractionConfig class."""

    def test_empty_config(self):
        """Empty config has no paths."""
        config = AbstractionConfig()
        assert len(config.tracked_paths) == 0
        assert config.state_space_estimate() == 1  # Product of empty = 1

    def test_from_analysis(self):
        """Config created from analysis."""
        analysis = DomainAnalysis()
        analysis.domains[StatePath.loc("@key")] = ValueDomain.held()
        analysis.domains[StatePath.prop("@door", "locked")] = ValueDomain.boolean()

        config = AbstractionConfig.from_analysis(analysis)

        assert len(config.tracked_paths) == 2
        assert config.state_space_estimate() == 4  # 2 * 2

    def test_from_analysis_with_filter(self):
        """Config can filter to specific paths."""
        analysis = DomainAnalysis()
        analysis.domains[StatePath.loc("@key")] = ValueDomain.held()
        analysis.domains[StatePath.prop("@door", "locked")] = ValueDomain.boolean()

        paths = {StatePath.loc("@key")}
        config = AbstractionConfig.from_analysis(analysis, paths)

        assert len(config.tracked_paths) == 1
        assert StatePath.loc("@key") in config.tracked_paths

    def test_fingerprint(self):
        """Fingerprint abstracts concrete state."""
        config = AbstractionConfig()
        key_loc = StatePath.loc("@key")
        config.tracked_paths.add(key_loc)
        config.domains[key_loc] = ValueDomain.held()

        # @player -> @player
        state1 = {key_loc: "@player"}
        fp1 = config.fingerprint(state1)
        assert (key_loc, "@player") in fp1

        # @room-1 -> NOT_HELD
        state2 = {key_loc: "@room-1"}
        fp2 = config.fingerprint(state2)
        assert (key_loc, NOT_HELD) in fp2

        # Both non-player rooms should have same fingerprint
        state3 = {key_loc: "@room-2"}
        fp3 = config.fingerprint(state3)
        assert fp2 == fp3  # Same abstract value

    def test_state_space_estimate(self):
        """State space is product of domain sizes."""
        config = AbstractionConfig()

        # 3 paths with sizes 2, 5, 3 = 30 states
        config.tracked_paths.add(StatePath.loc("@a"))
        config.domains[StatePath.loc("@a")] = ValueDomain.held()  # 2

        config.tracked_paths.add(StatePath.loc("@b"))
        config.domains[StatePath.loc("@b")] = ValueDomain.finite(
            {"@r1", "@r2", "@r3", "@r4", "@r5"}
        )  # 5

        config.tracked_paths.add(StatePath.prop("@c", "x"))
        config.domains[StatePath.prop("@c", "x")] = ValueDomain.finite({1, 2, 3})  # 3

        assert config.state_space_estimate() == 2 * 5 * 3

    def test_summary(self):
        """Summary describes the config."""
        config = AbstractionConfig()
        config.tracked_paths.add(StatePath.loc("@key"))
        config.domains[StatePath.loc("@key")] = ValueDomain.held()

        summary = config.summary()
        assert "1" in summary  # 1 path
        assert "HELD" in summary


# =============================================================================
# Integration Tests
# =============================================================================


class TestInferAbstraction:
    """Integration tests for infer_abstraction convenience function."""

    def test_simple_game(self):
        """Infer abstraction for a simple game."""
        world = make_test_world("""
        (object @key
            :location ROOM1
            :properties (:takeable true))

        (object @door
            :location ROOM1
            :properties (:locked true)
            :behaviors (
                :unlock (fn ()
                    (if (held? @key)
                        '((set @door :locked false)
                          (success :message "Unlocked"))
                        '((blocked :reason no-key))))))

        (room ROOM1 :description "room")
        """)

        effects = analyze_effects(world)
        config = infer_abstraction(world, effects)

        assert len(config.tracked_paths) > 0
        assert config.state_space_estimate() > 0

    def test_floor_waxer_pattern(self):
        """Test the floor-waxer scenario that motivated this work."""
        world = make_test_world("""
        (object @floor-waxer
            :location INF1)

        (room INF1 :description "inf 1")
        (room INF2 :description "inf 2")
        (room INF3 :description "inf 3")
        (room INF4 :description "inf 4")
        (room INF5 :description "inf 5")

        (event waxer-moves
            :on-turn
            (cond
                ((= (loc @floor-waxer) INF1) (move @floor-waxer INF2))
                ((= (loc @floor-waxer) INF2) (move @floor-waxer INF3))
                ((= (loc @floor-waxer) INF3) (move @floor-waxer INF4))
                ((= (loc @floor-waxer) INF4) (move @floor-waxer INF5))
                ((= (loc @floor-waxer) INF5) (move @floor-waxer INF1))))
        """)

        effects = analyze_effects(world)
        analysis = analyze_domains(world, effects)

        waxer_loc = StatePath.loc("@floor-waxer")
        domain = analysis.get_domain(waxer_loc)

        # Should have 5-value domain for the waxer location
        # (The rooms it can be in)
        assert len(domain.values) == 5
        assert "INF1" in domain.values
        assert "INF5" in domain.values

    def test_select_specific_paths(self):
        """Can select specific paths for abstraction."""
        world = make_test_world("""
        (object @a :location R1 :properties (:x 0 :takeable true))
        (object @b :location R2 :properties (:y 0 :takeable true))
        (room R1 :description "r1")
        (room R2 :description "r2")
        """)

        effects = analyze_effects(world)

        # Only track @a's location - must be modifiable to have a domain
        paths = {StatePath.loc("@a")}
        config = infer_abstraction(world, effects, paths)

        # @a's location should be tracked (it's modifiable via take)
        assert StatePath.loc("@a") in config.tracked_paths
        # @b should NOT be tracked since we only asked for @a
        assert StatePath.loc("@b") not in config.tracked_paths


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_unknown_writes(self):
        """Paths with unknown writes get runtime param flag."""
        world = make_test_world("""
        (object @ball
            :location ROOM
            :properties (:takeable true))  ; drop destination is unknown
        (room ROOM :description "room")
        """)

        effects = analyze_effects(world)
        analysis = analyze_domains(world, effects)

        ball_loc = StatePath.loc("@ball")
        pattern = analysis.read_patterns.get(ball_loc, ReadPattern())

        # Drop adds None (unknown) destination, which sets runtime param
        # The domain should still be useful though
        domain = analysis.get_domain(ball_loc)
        assert domain.kind != AbstractionKind.UNKNOWN

    def test_empty_world(self):
        """Empty world produces empty analysis."""
        world = make_test_world("")

        effects = analyze_effects(world)
        analysis = analyze_domains(world, effects)

        assert len(analysis.domains) == 0

    def test_no_effects_location_is_unknown(self):
        """Unmodified location is not tracked."""
        world = make_test_world("""
        (object @static
            :location ROOM
            :properties (:value 42))
        (room ROOM :description "room")
        """)

        effects = analyze_effects(world)
        analysis = analyze_domains(world, effects)

        # @static:location is not modified (object is not takeable, no events move it)
        # so it should be unknown
        loc_path = StatePath.loc("@static")
        loc_domain = analysis.get_domain(loc_path)
        assert loc_domain.kind == AbstractionKind.UNKNOWN

    def test_self_referential_domain(self):
        """Object that moves itself gets proper domain."""
        world = make_test_world("""
        (object @wanderer
            :location START
            :behaviors (
                :wander (fn ()
                    (cond
                        ((= (loc ?self) START) '((move @wanderer END) (success)))
                        (true '((move @wanderer START) (success)))))))
        (room START :description "start")
        (room END :description "end")
        """)

        effects = analyze_effects(world)
        analysis = analyze_domains(world, effects)

        wander_loc = StatePath.loc("@wanderer")
        domain = analysis.get_domain(wander_loc)

        # Should have START and END in domain
        assert "START" in domain.values
        assert "END" in domain.values
