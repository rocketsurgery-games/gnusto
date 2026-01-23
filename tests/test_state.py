"""
Tests for the unified state model (frotz.state).

Tests cover:
- StatePath creation and parsing
- DomainConstraint factory methods
- BuiltinSpec and BuiltinFunc structures
- BuiltinRegistry
- Conversion utilities for migration
"""

import pytest

from frotz.state import (
    StatePath,
    DomainConstraint,
    DomainKind,
    BuiltinSpec,
    BuiltinFunc,
    BuiltinRegistry,
    create_standard_builtins,
    state_ref_to_path,
    path_to_state_ref,
)
from frotz.effects import PropertyRef, LocationRef, QueueRef, HeldRef


# =============================================================================
# StatePath Tests
# =============================================================================


class TestStatePathCreation:
    """Test StatePath factory methods."""

    def test_loc_path(self):
        """loc() creates location paths."""
        path = StatePath.loc("@key")
        assert path.path == "loc(@key)"
        assert str(path) == "loc(@key)"

    def test_prop_path(self):
        """prop() creates property paths."""
        path = StatePath.prop("@door", "locked")
        assert path.path == "prop(@door,locked)"

    def test_queue_path(self):
        """queue() creates queue paths."""
        path = StatePath.queue("hacker-helps")
        assert path.path == "queue(hacker-helps)"

    def test_held_path(self):
        """held() creates abstract held predicate paths."""
        path = StatePath.held("@axe")
        assert path.path == "held(@axe)"

    def test_paths_are_hashable(self):
        """StatePath instances can be used in sets and dicts."""
        paths = {
            StatePath.loc("@key"),
            StatePath.prop("@door", "locked"),
            StatePath.queue("event"),
        }
        assert len(paths) == 3

        # Same path hashes the same
        paths.add(StatePath.loc("@key"))
        assert len(paths) == 3

    def test_paths_are_frozen(self):
        """StatePath is immutable (frozen=True)."""
        path = StatePath.loc("@key")
        with pytest.raises(AttributeError):
            path.path = "modified"


class TestStatePathParsing:
    """Test StatePath parsing methods."""

    def test_kind_loc(self):
        """kind property extracts 'loc'."""
        path = StatePath.loc("@key")
        assert path.kind == "loc"

    def test_kind_prop(self):
        """kind property extracts 'prop'."""
        path = StatePath.prop("@door", "locked")
        assert path.kind == "prop"

    def test_kind_queue(self):
        """kind property extracts 'queue'."""
        path = StatePath.queue("event")
        assert path.kind == "queue"

    def test_kind_held(self):
        """kind property extracts 'held'."""
        path = StatePath.held("@axe")
        assert path.kind == "held"

    def test_kind_unknown(self):
        """kind handles malformed paths."""
        path = StatePath("malformed")
        assert path.kind == "unknown"

    def test_object_from_loc(self):
        """object property extracts from loc paths."""
        path = StatePath.loc("@key")
        assert path.object == "@key"

    def test_object_from_prop(self):
        """object property extracts from prop paths."""
        path = StatePath.prop("@door", "locked")
        assert path.object == "@door"

    def test_object_from_held(self):
        """object property extracts from held paths."""
        path = StatePath.held("@axe")
        assert path.object == "@axe"

    def test_object_from_queue(self):
        """object property returns None for queue paths."""
        path = StatePath.queue("event")
        assert path.object is None

    def test_property_name(self):
        """property_name extracts from prop paths."""
        path = StatePath.prop("@door", "locked")
        assert path.property_name == "locked"

    def test_property_name_none_for_non_prop(self):
        """property_name returns None for non-prop paths."""
        path = StatePath.loc("@key")
        assert path.property_name is None

    def test_event_name(self):
        """event_name extracts from queue paths."""
        path = StatePath.queue("hacker-helps")
        assert path.event_name == "hacker-helps"

    def test_event_name_none_for_non_queue(self):
        """event_name returns None for non-queue paths."""
        path = StatePath.loc("@key")
        assert path.event_name is None


class TestStatePathEquality:
    """Test StatePath equality and hashing."""

    def test_equal_paths(self):
        """Equal paths are equal."""
        p1 = StatePath.loc("@key")
        p2 = StatePath.loc("@key")
        assert p1 == p2
        assert hash(p1) == hash(p2)

    def test_different_paths(self):
        """Different paths are not equal."""
        p1 = StatePath.loc("@key")
        p2 = StatePath.loc("@door")
        assert p1 != p2

    def test_different_kinds(self):
        """Different kinds are not equal even with same object."""
        p1 = StatePath.loc("@key")
        p2 = StatePath.held("@key")
        assert p1 != p2


# =============================================================================
# DomainConstraint Tests
# =============================================================================


class TestDomainConstraint:
    """Test DomainConstraint factory methods and structure."""

    def test_any_domain(self):
        """any() creates unconstrained domain."""
        d = DomainConstraint.any()
        assert d.kind == DomainKind.ANY

    def test_rooms_domain(self):
        """rooms() creates room domain."""
        d = DomainConstraint.rooms()
        assert d.kind == DomainKind.ROOMS

    def test_objects_domain(self):
        """objects() creates object domain."""
        d = DomainConstraint.objects()
        assert d.kind == DomainKind.OBJECTS

    def test_locations_domain(self):
        """locations() creates location domain."""
        d = DomainConstraint.locations()
        assert d.kind == DomainKind.LOCATIONS

    def test_boolean_domain(self):
        """boolean() creates boolean domain."""
        d = DomainConstraint.boolean()
        assert d.kind == DomainKind.BOOLEAN

    def test_finite_domain(self):
        """finite() creates finite set domain."""
        d = DomainConstraint.finite({1, 2, 3})
        assert d.kind == DomainKind.FINITE
        assert d.values == frozenset({1, 2, 3})

    def test_integer_domain(self):
        """integer() creates integer domain."""
        d = DomainConstraint.integer(min_val=0, max_val=10)
        assert d.kind == DomainKind.INTEGER
        assert d.min_val == 0
        assert d.max_val == 10

    def test_integer_unbounded(self):
        """integer() with no bounds."""
        d = DomainConstraint.integer()
        assert d.kind == DomainKind.INTEGER
        assert d.min_val is None
        assert d.max_val is None

    def test_domain_is_frozen(self):
        """DomainConstraint is immutable."""
        d = DomainConstraint.boolean()
        with pytest.raises(AttributeError):
            d.kind = DomainKind.INTEGER


# =============================================================================
# BuiltinSpec Tests
# =============================================================================


class TestBuiltinSpec:
    """Test BuiltinSpec structure."""

    def test_basic_spec(self):
        """Create a basic builtin spec."""
        spec = BuiltinSpec(
            name="test:op",
            params={"?obj": DomainConstraint.objects()},
        )
        assert spec.name == "test:op"
        assert "?obj" in spec.params

    def test_spec_with_reads(self):
        """Spec with reads function."""
        spec = BuiltinSpec(
            name="test:read",
            reads=lambda obj: {StatePath.loc(obj)},
        )
        result = spec.reads("@key")
        assert StatePath.loc("@key") in result

    def test_spec_with_writes(self):
        """Spec with writes function."""
        spec = BuiltinSpec(
            name="test:write",
            writes=lambda obj: {StatePath.loc(obj)},
        )
        result = spec.writes("@key")
        assert StatePath.loc("@key") in result

    def test_spec_with_modifies_to(self):
        """Spec with modifies_to function."""
        spec = BuiltinSpec(
            name="test:modify",
            modifies_to=lambda obj, dest: {StatePath.loc(obj): {dest}},
        )
        result = spec.modifies_to("@key", "@player")
        assert result[StatePath.loc("@key")] == {"@player"}


# =============================================================================
# BuiltinFunc Tests
# =============================================================================


class TestBuiltinFunc:
    """Test BuiltinFunc structure."""

    def test_basic_func(self):
        """Create a basic builtin func."""
        func = BuiltinFunc(
            name="loc",
            params={"obj": DomainConstraint.objects()},
            returns=DomainConstraint.locations(),
        )
        assert func.name == "loc"
        assert func.returns.kind == DomainKind.LOCATIONS

    def test_func_with_reads(self):
        """Func with reads function."""
        func = BuiltinFunc(
            name="loc",
            reads=lambda obj: {StatePath.loc(obj)},
        )
        result = func.reads("@key")
        assert StatePath.loc("@key") in result


# =============================================================================
# BuiltinRegistry Tests
# =============================================================================


class TestBuiltinRegistry:
    """Test BuiltinRegistry."""

    def test_register_operation(self):
        """Register and retrieve an operation."""
        registry = BuiltinRegistry()
        spec = BuiltinSpec(name="test:op")
        registry.register_operation(spec)

        assert registry.get_operation("test:op") == spec
        assert registry.get_operation("unknown") is None

    def test_register_function(self):
        """Register and retrieve a function."""
        registry = BuiltinRegistry()
        func = BuiltinFunc(name="test-func")
        registry.register_function(func)

        assert registry.get_function("test-func") == func
        assert registry.get_function("unknown") is None


class TestStandardBuiltins:
    """Test the standard builtins registry."""

    @pytest.fixture
    def registry(self):
        return create_standard_builtins()

    def test_has_go_operation(self, registry):
        """Standard builtins include runtime:go."""
        spec = registry.get_operation("runtime:go")
        assert spec is not None
        assert "?from" in spec.params
        assert "?to" in spec.params
        assert "?via" in spec.params

    def test_has_take_operation(self, registry):
        """Standard builtins include runtime:take."""
        spec = registry.get_operation("runtime:take")
        assert spec is not None
        assert "?obj" in spec.params

    def test_has_drop_operation(self, registry):
        """Standard builtins include runtime:drop."""
        spec = registry.get_operation("runtime:drop")
        assert spec is not None

    def test_has_loc_function(self, registry):
        """Standard builtins include loc function."""
        func = registry.get_function("loc")
        assert func is not None
        assert func.returns.kind == DomainKind.LOCATIONS

    def test_has_held_function(self, registry):
        """Standard builtins include held? function."""
        func = registry.get_function("held?")
        assert func is not None
        assert func.returns.kind == DomainKind.BOOLEAN

    def test_has_in_room_function(self, registry):
        """Standard builtins include in-room? function."""
        func = registry.get_function("in-room?")
        assert func is not None

    def test_has_queued_function(self, registry):
        """Standard builtins include queued? function."""
        func = registry.get_function("queued?")
        assert func is not None

    def test_go_writes_player_loc(self, registry):
        """runtime:go writes player location."""
        spec = registry.get_operation("runtime:go")
        writes = spec.writes()
        assert StatePath.loc("@player") in writes

    def test_take_writes_object_loc(self, registry):
        """runtime:take writes object location."""
        spec = registry.get_operation("runtime:take")
        writes = spec.writes("@key")
        assert StatePath.loc("@key") in writes

    def test_loc_reads_object_loc(self, registry):
        """loc function reads object location."""
        func = registry.get_function("loc")
        reads = func.reads("@key")
        assert StatePath.loc("@key") in reads


# =============================================================================
# Conversion Utilities Tests
# =============================================================================


class TestConversionUtilities:
    """Test conversion between old StateRef and new StatePath."""

    def test_property_ref_to_path(self):
        """Convert PropertyRef to StatePath."""
        ref = PropertyRef("@door", "locked")
        path = state_ref_to_path(ref)
        assert path == StatePath.prop("@door", "locked")

    def test_location_ref_to_path(self):
        """Convert LocationRef to StatePath."""
        ref = LocationRef("@key")
        path = state_ref_to_path(ref)
        assert path == StatePath.loc("@key")

    def test_queue_ref_to_path(self):
        """Convert QueueRef to StatePath."""
        ref = QueueRef("event")
        path = state_ref_to_path(ref)
        assert path == StatePath.queue("event")

    def test_held_ref_to_path(self):
        """Convert HeldRef to StatePath."""
        ref = HeldRef("@axe")
        path = state_ref_to_path(ref)
        assert path == StatePath.held("@axe")

    def test_state_path_passthrough(self):
        """StatePath passes through unchanged."""
        path = StatePath.loc("@key")
        result = state_ref_to_path(path)
        assert result == path

    def test_path_to_property_ref(self):
        """Convert StatePath to PropertyRef."""
        path = StatePath.prop("@door", "locked")
        ref = path_to_state_ref(path)
        assert isinstance(ref, PropertyRef)
        assert ref.object == "@door"
        assert ref.property == "locked"

    def test_path_to_location_ref(self):
        """Convert StatePath to LocationRef."""
        path = StatePath.loc("@key")
        ref = path_to_state_ref(path)
        assert isinstance(ref, LocationRef)
        assert ref.object == "@key"

    def test_path_to_queue_ref(self):
        """Convert StatePath to QueueRef."""
        path = StatePath.queue("event")
        ref = path_to_state_ref(path)
        assert isinstance(ref, QueueRef)
        assert ref.event == "event"

    def test_path_to_held_ref(self):
        """Convert StatePath to HeldRef."""
        path = StatePath.held("@axe")
        ref = path_to_state_ref(path)
        assert isinstance(ref, HeldRef)
        assert ref.object == "@axe"

    def test_roundtrip_property(self):
        """Roundtrip PropertyRef through StatePath."""
        original = PropertyRef("@door", "locked")
        path = state_ref_to_path(original)
        back = path_to_state_ref(path)
        assert back.object == original.object
        assert back.property == original.property

    def test_roundtrip_location(self):
        """Roundtrip LocationRef through StatePath."""
        original = LocationRef("@key")
        path = state_ref_to_path(original)
        back = path_to_state_ref(path)
        assert back.object == original.object

    def test_unknown_ref_type_raises(self):
        """Unknown ref type raises TypeError."""
        with pytest.raises(TypeError):
            state_ref_to_path("not a ref")


# =============================================================================
# Edge Cases
# =============================================================================


# =============================================================================
# Integration Tests - EffectAnalysis.to_paths()
# =============================================================================


class TestEffectAnalysisConversion:
    """Test converting EffectAnalysis to PathEffectAnalysis."""

    def test_testgame_conversion(self):
        """Convert testgame effects to path-based format."""
        from frotz.effects import analyze_effects
        from grue import load_grue

        world = load_grue("games/testgame")
        effects = analyze_effects(world)
        path_effects = effects.to_paths()

        # Same number of items
        assert len(path_effects.all_state) == len(effects.all_state)
        assert len(path_effects.modifies) == len(effects.modifies)

    def test_all_paths_have_correct_kinds(self):
        """All converted paths have valid kinds."""
        from frotz.effects import analyze_effects
        from grue import load_grue

        world = load_grue("games/testgame")
        effects = analyze_effects(world)
        path_effects = effects.to_paths()

        for path in path_effects.all_state:
            assert path.kind in ("loc", "prop", "queue", "held")

    def test_modifies_to_preserved(self):
        """Target values are preserved in conversion."""
        from frotz.effects import analyze_effects
        from grue import load_grue

        world = load_grue("games/testgame")
        effects = analyze_effects(world)
        path_effects = effects.to_paths()

        # Find a path with known target values
        key_loc = StatePath.loc("@key")
        if key_loc in path_effects.modifies_to:
            values = path_effects.get_write_values(key_loc)
            # Key can be moved to @player (take) or variable destination (drop)
            assert "@player" in values or None in values

    def test_get_write_values_empty_for_unmodified(self):
        """get_write_values returns empty set for unmodified paths."""
        from frotz.effects import analyze_effects, PathEffectAnalysis

        path_effects = PathEffectAnalysis()
        result = path_effects.get_write_values(StatePath.loc("@nonexistent"))
        assert result == set()


class TestEdgeCases:
    """Test edge cases and unusual inputs."""

    def test_empty_object_name(self):
        """Handle empty object name."""
        path = StatePath.loc("")
        assert path.path == "loc()"
        assert path.object == ""

    def test_object_with_special_chars(self):
        """Handle object names with hyphens and underscores."""
        path = StatePath.loc("@floor-waxer")
        assert path.object == "@floor-waxer"

        path2 = StatePath.prop("@some_object", "prop_name")
        assert path2.object == "@some_object"
        assert path2.property_name == "prop_name"

    def test_property_with_comma(self):
        """Property names shouldn't contain commas (but we handle it)."""
        # This is malformed but let's be defensive
        path = StatePath("prop(@obj,prop,extra)")
        assert path.kind == "prop"
        # Current parsing would get 'prop,extra' as property name
        assert path.property_name == "prop,extra"

    def test_complex_event_name(self):
        """Event names can have hyphens."""
        path = StatePath.queue("hacker-helps-again")
        assert path.event_name == "hacker-helps-again"

    def test_repr(self):
        """Test repr output."""
        path = StatePath.loc("@key")
        assert repr(path) == "StatePath('loc(@key)')"
