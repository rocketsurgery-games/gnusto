"""Tests for the variant render model: :render selectors, :rdesc briefs, keys."""

import pytest

from grue import parse_grue
from grue.render import (
    RenderError,
    RenderRead,
    assemble_brief,
    assemble_style,
    asset_base,
    brief_for_variant,
    build_render_manifest,
    event_render_tags,
    get_render_spec,
    has_render_spec,
    is_renderable,
    lint_render,
    render_codomain,
    render_keyset,
    render_reads,
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
        spec = parse("(fn () (if true :open :closed))")
        assert resolve_asset_key("@microwave", spec, MockState()) == "microwave-open"

    def test_fn_selector_other_branch(self):
        spec = parse("(fn () (if false :open :closed))")
        assert resolve_asset_key("@microwave", spec, MockState()) == "microwave-closed"

    def test_literal_keyword_tag(self):
        # A bare keyword :render value is a single literal variant tag.
        spec = parse(":open")
        assert resolve_asset_key("@microwave", spec, MockState()) == "microwave-open"

    def test_fn_returning_string_is_verbatim_key(self):
        # A string from a selector is a verbatim key, NOT a derived tag.
        spec = parse('(fn () "shared-image")')
        assert resolve_asset_key("@door", spec, MockState()) == "shared-image"

    def test_empty_token_falls_back_to_base(self):
        spec = parse("(fn () (when false :never))")  # returns nil
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


class TestAssembleStyle:
    """The shared style preamble (hoisted, not repeated per entry)."""

    def test_prompt_and_palette(self):
        style = {"prompt": "Inked.", "palette": "dark blues"}
        assert assemble_style(style) == "Inked. Palette: dark blues."

    def test_prompt_only(self):
        assert assemble_style({"prompt": "Inked."}) == "Inked."

    def test_empty(self):
        assert assemble_style(None) == ""
        assert assemble_style({}) == ""


class TestAssembleBrief:
    """Test assembling a full generation prompt: style preamble + brief."""

    def test_style_prefix_and_brief(self):
        style = {"prompt": "Color graphic-novel horror."}
        assert assemble_brief(style, "A brass lantern.") == (
            "Color graphic-novel horror. A brass lantern."
        )

    def test_palette_in_style_preamble(self):
        # Palette is part of the shared style preamble, so it leads the brief.
        style = {"prompt": "Inked.", "palette": "dark blues"}
        assert (
            assemble_brief(style, "A lantern.")
            == "Inked. Palette: dark blues. A lantern."
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
        # The manifest carries the per-entity brief without the shared style.
        entry = {e.key: e for e in build_render_manifest(world)}["microwave-open"]
        assert entry.brief == "A microwave, door open, above a counter."


class TestRenderReads:
    """Static extraction of state paths a :render selector reads."""

    def test_self_property_read(self):
        spec = parse('(fn () (if (:open self) "open" "closed"))')
        reads = render_reads(spec)
        assert RenderRead("prop", "self", "open") in reads

    def test_foreign_property_read(self):
        spec = parse('(fn () (if (:open @microwave) "a" "b"))')
        reads = render_reads(spec)
        assert RenderRead("prop", "@microwave", "open") in reads

    def test_queue_read(self):
        spec = parse('(fn () (if (queued? microwave-running) "running" "idle"))')
        reads = render_reads(spec)
        assert RenderRead("queue", None, "microwave-running") in reads

    def test_held_and_loc_reads(self):
        spec = parse('(fn () (cond ((held? @lamp) "held") ((loc @lamp) "loose")))')
        reads = render_reads(spec)
        assert RenderRead("loc", "@lamp") in reads

    def test_literal_selector_no_reads(self):
        assert render_reads("cs-elevator-room") == set()
        assert render_reads(None) == set()


class TestRenderCodomain:
    """Static extraction of the variant tokens a selector can return."""

    def test_if_codomain(self):
        spec = parse("(fn () (if (:open self) :open :closed))")
        assert render_codomain(spec) == {"open", "closed"}

    def test_cond_codomain(self):
        spec = parse(
            "(fn () (cond ((:open self) :open) ((queued? e) :running) (true :closed)))"
        )
        assert render_codomain(spec) == {"open", "running", "closed"}

    def test_nested_codomain(self):
        spec = parse("(fn () (if a :x (if b :y :z)))")
        assert render_codomain(spec) == {"x", "y", "z"}

    def test_string_returns_are_not_tags(self):
        # Verbatim string keys are not variant tags -> empty tag codomain.
        spec = parse('(fn () (if a "verbatim" :tag))')
        assert render_codomain(spec) == {"tag"}

    def test_unbounded_codomain_is_none(self):
        # Returns a computed value, not a literal -> not statically bounded.
        spec = parse('(fn () (str "variant-" (:n self)))')
        assert render_codomain(spec) is None

    def test_literal_selector_codomain_none(self):
        # Literal-string selectors are their own key; not a fn codomain.
        assert render_codomain("cs-elevator-room") is None


class TestBuildManifest:
    """Manifest enumeration over a whole world."""

    def test_manifest_keys_and_briefs(self):
        source = """
        (world :name "Test" :player @player
          :visual-style (:prompt "Color graphic-novel horror."))
        (room @lab :description "Lab" :rdesc "A dingy lab.")
        (object @player :description "you")
        (object @microwave
          :description "microwave"
          :render (fn () (if (:open self) "open" "closed"))
          :rdesc (:open "Microwave open." :closed "Microwave closed."))
        """
        world = parse_grue(source)
        manifest = build_render_manifest(world)
        by_key = {e.key: e for e in manifest}
        assert set(by_key) == {"lab", "microwave-open", "microwave-closed"}
        assert by_key["lab"].kind == "room"
        assert by_key["microwave-open"].kind == "object"
        assert by_key["microwave-open"].variant == "open"
        # Entry brief is the raw :rdesc only; the world style is hoisted out.
        assert by_key["microwave-open"].brief == "Microwave open."
        assert assemble_brief(world.visual_style, by_key["microwave-open"].brief) == (
            "Color graphic-novel horror. Microwave open."
        )

    def test_shared_alias_key_deduped(self):
        source = """
        (world :name "Test" :player @player)
        (object @player :description "you")
        (room @elevator :description "Elevator" :rdesc "An elevator interior.")
        (object @elevator-door :render "elevator")
        """
        world = parse_grue(source)
        keys = [e.key for e in build_render_manifest(world)]
        # The door reuses the room's key; it appears exactly once.
        assert keys.count("elevator") == 1


class TestLintRender:
    """The explosion-guard lint."""

    def test_clean_object_selector(self):
        source = """
        (world :name "Test" :player @player)
        (object @player :description "you")
        (object @microwave
          :render (fn () (cond ((:open self) "open")
                               ((queued? microwave-running) "running")
                               (true "closed")))
          :rdesc (:open "o" :running "r" :closed "c"))
        """
        assert lint_render(parse_grue(source)) == []

    def test_codomain_not_subset_of_variants(self):
        source = """
        (world :name "Test" :player @player)
        (object @player :description "you")
        (object @microwave
          :render (fn () (if (:open self) :open :shut))
          :rdesc (:open "o" :closed "c"))
        """
        errors = lint_render(parse_grue(source))
        assert len(errors) == 1
        assert "shut" in errors[0].message
        assert errors[0].severity == "error"

    def test_room_reading_object_state_is_error(self):
        source = """
        (world :name "Test" :player @player)
        (object @player :description "you")
        (object @microwave :description "microwave")
        (room @kitchen
          :description "Kitchen"
          :render (fn () (if (:open @microwave) "open" "closed"))
          :rdesc (:open "k open" :closed "k closed"))
        """
        errors = lint_render(parse_grue(source))
        assert any("foreign object state" in e.message for e in errors)
        assert any(e.entity == "@kitchen" for e in errors)

    def test_object_reading_foreign_state_is_error(self):
        source = """
        (world :name "Test" :player @player)
        (object @player :description "you")
        (object @fridge :description "fridge")
        (object @magnet
          :render (fn () (if (:open @fridge) "on" "off"))
          :rdesc (:on "on" :off "off"))
        """
        errors = lint_render(parse_grue(source))
        assert any("foreign state" in e.message for e in errors)

    def test_self_read_via_at_name_is_own_state(self):
        # Referring to the entity by its own @name counts as own state.
        source = """
        (world :name "Test" :player @player)
        (object @player :description "you")
        (object @microwave
          :render (fn () (if (:open @microwave) "open" "closed"))
          :rdesc (:open "o" :closed "c"))
        """
        assert lint_render(parse_grue(source)) == []


class TestEventRenderTags:
    """Static extraction of beat tags emitted by an event body."""

    def test_collects_literal_tags(self):
        body = parse(
            '(cond ((= a 0) \'((success :render :stage1 :message "m")))'
            "      (true '((blocked :reason death :render :stage2))))"
        )
        tags, exact = event_render_tags(body)
        assert tags == {"stage1", "stage2"}
        assert exact is True

    def test_non_literal_tag_is_inexact(self):
        body = parse("'((success :render some-var))")
        tags, exact = event_render_tags(body)
        assert exact is False

    def test_no_emissions(self):
        assert event_render_tags(parse("'((dequeue e) (success))")) == (set(), True)


class TestEventBeatManifestAndLint:
    """Events with a :rdesc beat catalog flow through manifest + lint."""

    def _world(self, body, rdesc):
        source = f"""
        (world :name "T" :player @player)
        (object @player :description "you")
        (event ritual
          :on-turn {body}
          :rdesc {rdesc})
        """
        return parse_grue(source)

    def test_manifest_includes_event_beats(self):
        world = self._world(
            '(cond ((= a 0) \'((success :render :a :message "m")))'
            "      (true '((success :render :b))))",
            '(:a "beat a" :b "beat b")',
        )
        by_key = {e.key: e for e in build_render_manifest(world)}
        assert "ritual-a" in by_key and "ritual-b" in by_key
        assert by_key["ritual-a"].kind == "event"
        assert by_key["ritual-a"].variant == "a"
        assert by_key["ritual-a"].brief == "beat a"
        assert lint_render(world) == []

    def test_emitted_tag_without_catalog_entry_is_error(self):
        world = self._world(
            "'((success :render :c))",
            '(:a "beat a" :b "beat b")',
        )
        errors = [e for e in lint_render(world) if e.severity == "error"]
        assert any("c" in e.message and e.entity == "ritual" for e in errors)

    def test_unused_catalog_entry_is_warning(self):
        world = self._world(
            "'((success :render :a))",
            '(:a "beat a" :b "beat b")',
        )
        warnings = [e for e in lint_render(world) if e.severity == "warning"]
        assert any("b" in e.message for e in warnings)


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
