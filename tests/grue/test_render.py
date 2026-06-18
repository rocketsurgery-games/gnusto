"""Tests for the variant render model: :render selectors, :rdesc briefs, keys."""

import pytest

from grue import parse_grue
from grue.render import (
    RenderError,
    assemble_brief,
    asset_base,
    brief_for_variant,
    get_render_spec,
    has_render_spec,
    is_renderable,
    render_keyset,
    render_variants,
    resolve_asset_key,
)
from grue.sexpr import parse


class TestRenderParsing:
    """Test parsing :render selectors and :rdesc briefs."""

    def test_literal_render_string(self):
        source = """
        (object @lantern
          :description "A brass lantern"
          :render "lantern.png")
        """
        obj = parse_grue(source).objects["@lantern"]
        assert obj.render == "lantern.png"
        assert has_render_spec(obj)
        assert is_renderable(obj)

    def test_rdesc_string_single_variant(self):
        source = """
        (object @chair
          :description "a chair"
          :rdesc "A molded blue plastic chair, on a solid white background.")
        """
        obj = parse_grue(source).objects["@chair"]
        assert obj.render is None  # no selector needed for single variant
        assert obj.rdesc == "A molded blue plastic chair, on a solid white background."
        assert is_renderable(obj)

    def test_rdesc_variant_map(self):
        source = """
        (object @microwave
          :description "microwave oven"
          :render (fn () (cond ((:open self) "open") (true "closed")))
          :rdesc (:open   "A microwave, door open."
                  :closed "A microwave, door closed."))
        """
        obj = parse_grue(source).objects["@microwave"]
        assert isinstance(obj.rdesc, dict)
        assert obj.rdesc["open"] == "A microwave, door open."
        assert obj.rdesc["closed"] == "A microwave, door closed."

    def test_room_rdesc(self):
        source = """
        (room @lab
          :description "Terminal Room"
          :rdesc "A dingy 1980s computer lab, fluorescent-lit, empty of people.")
        """
        room = parse_grue(source).rooms["@lab"]
        assert room.rdesc.startswith("A dingy 1980s computer lab")
        assert is_renderable(room)

    def test_not_renderable_without_render_or_rdesc(self):
        source = '(object @key :description "a brass key")'
        obj = parse_grue(source).objects["@key"]
        assert not is_renderable(obj)
        assert get_render_spec(obj) is None

    def test_bad_rdesc_type_raises(self):
        source = "(object @x :rdesc 123)"
        with pytest.raises(Exception):
            parse_grue(source)


class TestAssetBase:
    def test_strips_at_sign(self):
        assert asset_base("@microwave") == "microwave"
        assert asset_base("@cs-elevator-room") == "cs-elevator-room"


class TestResolveAssetKey:
    """Test runtime resolution of the current asset key."""

    def test_none_render_single_variant(self):
        # No selector -> base name (extension-less)
        assert resolve_asset_key("@chair", None, MockState()) == "chair"

    def test_literal_render_used_verbatim(self):
        # Literal string -> the exact key (alias / shared image)
        assert (
            resolve_asset_key("@elevator-door", "cs-elevator-room", MockState())
            == "cs-elevator-room"
        )

    def test_fn_selector_derives_key(self):
        spec = parse('(fn () (if true "open" "closed"))')
        assert resolve_asset_key("@microwave", spec, MockState()) == "microwave-open"

    def test_fn_selector_other_branch(self):
        spec = parse('(fn () (if false "open" "closed"))')
        assert resolve_asset_key("@microwave", spec, MockState()) == "microwave-closed"

    def test_empty_token_falls_back_to_base(self):
        spec = parse('(fn () (when false "never"))')  # returns nil -> ""
        assert resolve_asset_key("@thing", spec, MockState()) == "thing"

    def test_bad_selector_raises(self):
        with pytest.raises(RenderError):
            resolve_asset_key("@x", 123, MockState())


class TestKeysetAndVariants:
    """Test declarative keyset enumeration (no state needed)."""

    def test_variants_from_rdesc_map(self):
        source = """
        (object @microwave
          :render (fn () (cond ((:open self) "open") (true "closed")))
          :rdesc (:open "open brief" :closed "closed brief" :running "running brief"))
        """
        obj = parse_grue(source).objects["@microwave"]
        assert set(render_variants(obj)) == {"open", "closed", "running"}
        assert render_keyset("@microwave", obj) == {
            "microwave-open",
            "microwave-closed",
            "microwave-running",
        }

    def test_single_variant_keyset(self):
        source = '(object @chair :rdesc "A chair.")'
        obj = parse_grue(source).objects["@chair"]
        assert render_variants(obj) is None
        assert render_keyset("@chair", obj) == {"chair"}

    def test_literal_render_keyset(self):
        source = '(object @door :render "cs-elevator-room")'
        obj = parse_grue(source).objects["@door"]
        assert render_keyset("@door", obj) == {"cs-elevator-room"}

    def test_not_renderable_empty_keyset(self):
        source = '(object @key :description "a key")'
        obj = parse_grue(source).objects["@key"]
        assert render_keyset("@key", obj) == set()


class TestBriefForVariant:
    def test_map_lookup(self):
        source = """
        (object @microwave
          :rdesc (:open "open brief" :closed "closed brief"))
        """
        obj = parse_grue(source).objects["@microwave"]
        assert brief_for_variant(obj, "open") == "open brief"
        assert brief_for_variant(obj, "closed") == "closed brief"
        assert brief_for_variant(obj, "missing") is None

    def test_string_brief(self):
        source = '(object @chair :rdesc "A chair brief.")'
        obj = parse_grue(source).objects["@chair"]
        assert brief_for_variant(obj) == "A chair brief."

    def test_falls_back_to_string_description(self):
        source = '(object @key :description "a brass key" :render "key.png")'
        obj = parse_grue(source).objects["@key"]
        assert brief_for_variant(obj) == "a brass key"

    def test_no_brief_when_description_is_fn(self):
        source = '(object @key :description (fn () "dynamic") :render "key.png")'
        obj = parse_grue(source).objects["@key"]
        assert brief_for_variant(obj) is None


class TestVisualStyle:
    """Test parsing the world-level :visual-style keyword-map."""

    def test_visual_style_parsed_as_dict(self):
        source = """
        (world :name "Test" :player @player
          :visual-style (:prompt "Color graphic-novel horror, inked."
                         :palette "dark blues, sickly greens"
                         :aspect-ratio "16:9"))
        """
        world = parse_grue(source)
        assert world.visual_style["prompt"] == "Color graphic-novel horror, inked."
        assert world.visual_style["palette"] == "dark blues, sickly greens"
        assert world.visual_style["aspect-ratio"] == "16:9"

    def test_no_visual_style_is_empty_dict(self):
        world = parse_grue('(world :name "Test" :player @player)')
        assert world.visual_style == {}


class TestAssembleBrief:
    """Test assembling a generation prompt from style + brief."""

    def test_style_prefix_and_brief(self):
        style = {"prompt": "Color graphic-novel horror."}
        assert assemble_brief(style, "A brass lantern.") == (
            "Color graphic-novel horror. A brass lantern."
        )

    def test_palette_hint_appended(self):
        style = {"prompt": "Inked.", "palette": "dark blues"}
        assert (
            assemble_brief(style, "A lantern.")
            == "Inked. A lantern. Palette: dark blues."
        )

    def test_empty_style(self):
        assert assemble_brief(None, "Just the brief.") == "Just the brief."
        assert assemble_brief({}, "Just the brief.") == "Just the brief."

    def test_no_brief(self):
        assert assemble_brief({"prompt": "Style only."}, None) == "Style only."


class TestEndToEnd:
    """The microwave: selector + variant briefs working together."""

    def test_microwave_variant_pipeline(self):
        source = """
        (world :name "Test" :player @player
          :visual-style (:prompt "Color graphic-novel horror."))
        (object @microwave
          :description "microwave oven"
          :render (fn () (cond ((:open self) "open") (true "closed")))
          :rdesc (:open   "A microwave, door open, above a counter."
                  :closed "A microwave, door closed, above a counter."))
        """
        world = parse_grue(source)
        obj = world.objects["@microwave"]

        # Every declared variant has a key and a brief.
        assert render_keyset("@microwave", obj) == {
            "microwave-open",
            "microwave-closed",
        }
        full = assemble_brief(world.visual_style, brief_for_variant(obj, "open"))
        assert full == (
            "Color graphic-novel horror. A microwave, door open, above a counter."
        )


class MockState:
    """Mock WorldState for testing render selector evaluation."""

    def get_object_location(self, obj: str) -> str | None:
        return None

    def get_object_property(self, obj: str, prop: str):
        return None

    def get_global(self, name: str):
        raise KeyError(f"Unknown symbol: {name}")

    def get_player_location(self) -> str:
        return "@player-room"

    def get_player_name(self) -> str:
        return "@player"

    def get_inventory(self) -> list[str]:
        return []

    def is_visible(self, obj: str) -> bool:
        return True
