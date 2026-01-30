"""Tests for render spec parsing and evaluation."""

import pytest

from grue import (
    parse_grue,
    GrueObject,
    GrueRoom,
    Symbol,
    SList,
    Keyword,
)
from grue.render import (
    RenderResult,
    RenderError,
    ObjectRef,
    evaluate_render_spec,
    has_render_spec,
    get_render_spec,
)
from grue.sexpr import parse


class TestRenderSpecParsing:
    """Test parsing :render on objects and rooms."""

    def test_object_with_render_spec(self):
        """Object can have a :render spec."""
        source = """
        (object @lantern
          :description "A brass lantern"
          :render ("A brass lantern with glass panels"
                   :ref "assets/lantern.png"))
        """
        world = parse_grue(source)
        obj = world.objects["@lantern"]

        assert obj.render is not None
        assert has_render_spec(obj)

    def test_room_with_render_spec(self):
        """Room can have a :render spec."""
        source = """
        (room @cellar
          :description "A dark cellar"
          :render ("A stone cellar with torchlight"
                   :ref "assets/cellar.png"
                   :contents))
        """
        world = parse_grue(source)
        room = world.rooms["@cellar"]

        assert room.render is not None
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
          :render ("A brass lantern"))
        (object @key
          :description "A key")
        """
        world = parse_grue(source)

        spec = get_render_spec(world.objects["@lantern"])
        assert spec is not None
        assert isinstance(spec, SList)

        spec = get_render_spec(world.objects["@key"])
        assert spec is None


class TestRenderSpecEvaluation:
    """Test evaluating render specs to RenderResult."""

    def test_simple_prompt(self):
        """Simple string prompt."""
        spec = parse('("A brass lantern")')
        result = evaluate_render_spec(spec, "@lantern", MockState())

        assert result.prompt == "A brass lantern"
        assert result.ref_paths == []
        assert result.object_refs == []

    def test_prompt_with_ref(self):
        """Prompt with :ref path."""
        spec = parse('("A brass lantern" :ref "assets/lantern.png")')
        result = evaluate_render_spec(spec, "@lantern", MockState())

        assert result.prompt == "A brass lantern"
        assert result.ref_paths == ["assets/lantern.png"]

    def test_prompt_with_multiple_refs(self):
        """Prompt with multiple :ref paths."""
        spec = parse("""
            ("A brass lantern on a wooden table"
             :ref "assets/lantern.png"
             :ref "assets/table.png")
        """)
        result = evaluate_render_spec(spec, "@lantern", MockState())

        assert result.prompt == "A brass lantern on a wooden table"
        assert result.ref_paths == ["assets/lantern.png", "assets/table.png"]

    def test_object_references(self):
        """Object references (@obj) become object_refs."""
        spec = parse('("A scene with " @lantern " and " @table)')
        result = evaluate_render_spec(spec, "@scene", MockState())

        assert result.prompt == "A scene with and"  # Object refs don't add to prompt
        assert len(result.object_refs) == 2
        assert result.object_refs[0].name == "@lantern"
        assert result.object_refs[1].name == "@table"

    def test_ref_size_option(self):
        """The :ref-size keyword sets ref_size."""
        spec = parse('("A lantern" :ref-size 512 :ref "assets/lantern.png")')
        result = evaluate_render_spec(spec, "@lantern", MockState())

        assert result.ref_size == 512

    def test_anchor_option(self):
        """The :anchor keyword adds to anchors list."""
        spec = parse('("A scene" @composite :anchor @atomic-ref)')
        result = evaluate_render_spec(spec, "@scene", MockState())

        assert result.anchors == ["@atomic-ref"]

    def test_contents_option(self):
        """The :contents keyword sets include_contents."""
        spec = parse('("A cellar" :ref "assets/cellar.png" :contents)')
        result = evaluate_render_spec(spec, "@cellar", MockState())

        assert result.include_contents is True

    def test_concatenated_strings(self):
        """Multiple strings are concatenated."""
        spec = parse('("A brass " "lantern " "with glass panels")')
        result = evaluate_render_spec(spec, "@lantern", MockState())

        assert result.prompt == "A brass lantern with glass panels"

    def test_expression_evaluation(self):
        """Expressions are evaluated and added to prompt."""
        spec = parse('("Door is " (if true "open" "closed"))')
        result = evaluate_render_spec(spec, "@door", MockState())

        assert result.prompt == "Door is open"

    def test_self_binding(self):
        """The `self` symbol is bound to entity name."""
        spec = parse('("Rendering " self)')
        result = evaluate_render_spec(spec, "@my-object", MockState())

        assert result.prompt == "Rendering @my-object"

    def test_when_expression_nil(self):
        """(when false ...) returns nil and is skipped."""
        spec = parse('("A lantern" (when false ", glowing"))')
        result = evaluate_render_spec(spec, "@lantern", MockState())

        # The nil result from (when false ...) should be skipped
        assert result.prompt == "A lantern"

    def test_ref_size_applies_to_object_refs(self):
        """ref-size applies to subsequent object refs."""
        spec = parse('(:ref-size 384 @lantern @table :ref-size 128 @background)')
        result = evaluate_render_spec(spec, "@scene", MockState())

        assert len(result.object_refs) == 3
        assert result.object_refs[0].ref_size == 384
        assert result.object_refs[1].ref_size == 384
        assert result.object_refs[2].ref_size == 128


class TestRenderSpecErrors:
    """Test error handling in render spec evaluation."""

    def test_string_as_prompt_only(self):
        """String spec is valid as prompt-only render."""
        result = evaluate_render_spec("A brass lantern", "@obj", MockState())
        assert result.prompt == "A brass lantern"
        assert result.ref_paths == []
        assert result.object_refs == []

    def test_invalid_spec_type(self):
        """Non-list, non-string spec raises RenderError."""
        with pytest.raises(RenderError, match="must be a string, fn, or list"):
            evaluate_render_spec(123, "@obj", MockState())

    def test_ref_without_path(self):
        """:ref without path raises error."""
        spec = parse('("A lantern" :ref)')
        with pytest.raises(RenderError, match=":ref requires a path"):
            evaluate_render_spec(spec, "@obj", MockState())

    def test_ref_with_non_string_path(self):
        """:ref with non-string path raises error."""
        spec = parse('("A lantern" :ref 123)')
        with pytest.raises(RenderError, match="must be a string"):
            evaluate_render_spec(spec, "@obj", MockState())

    def test_ref_size_without_value(self):
        """:ref-size without number raises error."""
        spec = parse('("A lantern" :ref-size)')
        with pytest.raises(RenderError, match=":ref-size requires a number"):
            evaluate_render_spec(spec, "@obj", MockState())

    def test_anchor_without_object(self):
        """:anchor without object ref raises error."""
        spec = parse('("A scene" :anchor)')
        with pytest.raises(RenderError, match=":anchor requires an object"):
            evaluate_render_spec(spec, "@obj", MockState())


class MockState:
    """Mock WorldState for testing render spec evaluation."""

    def get_object_location(self, obj: str) -> str | None:
        return None

    def get_object_property(self, obj: str, prop: str) -> any:
        return None

    def get_global(self, name: str) -> any:
        return None

    def get_player_location(self) -> str:
        return "@player-room"

    def get_player_name(self) -> str:
        return "@player"

    def get_inventory(self) -> list[str]:
        return []

    def is_visible(self, obj: str) -> bool:
        return True
