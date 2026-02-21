"""Tests for render spec parsing and evaluation."""

import pytest

from grue import parse_grue
from grue.render import (
    RenderError,
    evaluate_render_spec,
    has_render_spec,
    get_render_spec,
)
from grue.sexpr import parse


class TestRenderSpecParsing:
    """Test parsing :render on objects and rooms."""

    def test_object_with_string_render(self):
        """Object can have a string :render spec."""
        source = """
        (object @lantern
          :description "A brass lantern"
          :render "lantern.png")
        """
        world = parse_grue(source)
        obj = world.objects["@lantern"]

        assert obj.render == "lantern.png"
        assert has_render_spec(obj)

    def test_room_with_string_render(self):
        """Room can have a string :render spec."""
        source = """
        (room @cellar
          :description "A dark cellar"
          :render "cellar.png")
        """
        world = parse_grue(source)
        room = world.rooms["@cellar"]

        assert room.render == "cellar.png"
        assert has_render_spec(room)

    def test_object_without_render_spec(self):
        """Objects without :render have render=None."""
        source = """
        (object @key
          :description "A brass key")
        """
        world = parse_grue(source)
        obj = world.objects["@key"]

        assert obj.render is None
        assert not has_render_spec(obj)

    def test_get_render_spec(self):
        """get_render_spec retrieves the spec or None."""
        source = """
        (object @lantern
          :description "A lantern"
          :render "lantern.png")
        (object @key
          :description "A key")
        """
        world = parse_grue(source)

        spec = get_render_spec(world.objects["@lantern"])
        assert spec == "lantern.png"

        spec = get_render_spec(world.objects["@key"])
        assert spec is None


class TestRenderSpecEvaluation:
    """Test evaluating render specs."""

    def test_none_returns_none(self):
        """None spec returns None."""
        result = evaluate_render_spec(None, "@lantern", MockState())
        assert result is None

    def test_string_returns_string(self):
        """String spec returns the string."""
        result = evaluate_render_spec("lantern.png", "@lantern", MockState())
        assert result == "lantern.png"

    def test_fn_spec(self):
        """fn spec evaluates and returns string."""
        spec = parse('(fn () "glowing-lantern.png")')
        result = evaluate_render_spec(spec, "@lantern", MockState())
        assert result == "glowing-lantern.png"

    def test_fn_spec_with_conditional(self):
        """fn spec with conditional logic."""
        spec = parse('(fn () (if true "open-door.png" "closed-door.png"))')
        result = evaluate_render_spec(spec, "@door", MockState())
        assert result == "open-door.png"

    def test_fn_spec_nil_result(self):
        """fn returning nil produces empty string."""
        spec = parse('(fn () (when false "never.png"))')
        result = evaluate_render_spec(spec, "@obj", MockState())
        assert result == ""


class TestRenderSpecErrors:
    """Test error handling in render spec evaluation."""

    def test_invalid_spec_type_raises(self):
        """Non-string, non-fn spec raises RenderError."""
        with pytest.raises(RenderError):
            evaluate_render_spec(123, "@obj", MockState())

    def test_list_without_fn_raises(self):
        """List that isn't (fn ...) raises RenderError."""
        spec = parse('("just a string in a list")')
        with pytest.raises(RenderError):
            evaluate_render_spec(spec, "@obj", MockState())


class MockState:
    """Mock WorldState for testing render spec evaluation."""

    def get_object_location(self, obj: str) -> str | None:
        return None

    def get_object_property(self, obj: str, prop: str) -> any:
        return None

    def get_global(self, name: str) -> any:
        raise KeyError(f"Unknown symbol: {name}")

    def get_player_location(self) -> str:
        return "@player-room"

    def get_player_name(self) -> str:
        return "@player"

    def get_inventory(self) -> list[str]:
        return []

    def is_visible(self, obj: str) -> bool:
        return True
