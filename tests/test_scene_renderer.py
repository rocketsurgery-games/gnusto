"""Tests for scene rendering integration."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from grue import parse_grue
from grue.render import evaluate_render_spec
from grue.render_cache import RenderCache


class TestTerminalImages:
    """Test terminal image protocol detection."""

    def test_detect_no_protocol(self):
        """Detects 'none' when no terminal image support."""
        from gnusto.terminal_images import detect_protocol

        with patch.dict("os.environ", {}, clear=True):
            # Clear all terminal-related env vars
            with patch("gnusto.terminal_images._TERM", "xterm"):
                with patch("gnusto.terminal_images._TERM_PROGRAM", ""):
                    with patch("gnusto.terminal_images._KITTY_WINDOW_ID", ""):
                        with patch("gnusto.terminal_images._WEZTERM_PANE", ""):
                            assert detect_protocol() == "none"

    def test_detect_kitty(self):
        """Detects Kitty terminal."""
        from gnusto.terminal_images import detect_protocol

        with patch("gnusto.terminal_images._KITTY_WINDOW_ID", "123"):
            assert detect_protocol() == "kitty"

    def test_detect_iterm2(self):
        """Detects iTerm2 terminal."""
        from gnusto.terminal_images import detect_protocol

        with patch("gnusto.terminal_images._KITTY_WINDOW_ID", ""):
            with patch("gnusto.terminal_images._WEZTERM_PANE", ""):
                with patch("gnusto.terminal_images._TERM_PROGRAM", "iTerm.app"):
                    assert detect_protocol() == "iterm2"

    def test_is_supported(self):
        """is_supported() returns False when no protocol."""
        from gnusto.terminal_images import is_supported

        with patch("gnusto.terminal_images.detect_protocol", return_value="none"):
            assert is_supported() is False

        with patch("gnusto.terminal_images.detect_protocol", return_value="kitty"):
            assert is_supported() is True


class TestRenderSpecIntegration:
    """Test render spec parsing with actual Grue definitions."""

    def test_object_with_render_spec(self):
        """Parse and evaluate object render spec."""
        source = """
        (object @lantern
          :description "A brass lantern"
          :render ("A brass lantern with glass panels and a metal handle"
                   :ref "assets/lantern.png"
                   :ref-size 384))
        """
        world = parse_grue(source)
        obj = world.objects["@lantern"]

        assert obj.render is not None

        # Evaluate the spec
        result = evaluate_render_spec(obj.render, "@lantern", MockState())
        assert result.prompt == "A brass lantern with glass panels and a metal handle"
        assert result.ref_paths == ["assets/lantern.png"]
        assert result.ref_size == 384

    def test_room_with_contents(self):
        """Parse room render spec with :contents."""
        source = """
        (room @cellar
          :description "A dark cellar"
          :render ("A stone cellar with torchlight"
                   :ref "assets/cellar.png"
                   :contents))
        """
        world = parse_grue(source)
        room = world.rooms["@cellar"]

        result = evaluate_render_spec(room.render, "@cellar", MockState())
        assert result.prompt == "A stone cellar with torchlight"
        assert result.include_contents is True

    def test_render_spec_with_object_refs(self):
        """Parse render spec with object references."""
        source = """
        (object @scene
          :render ("A scene with " @lantern " on " @table
                   :anchor @atomic-lantern))
        """
        world = parse_grue(source)
        obj = world.objects["@scene"]

        result = evaluate_render_spec(obj.render, "@scene", MockState())
        assert result.prompt == "A scene with on"  # Object refs don't contribute to prompt
        assert len(result.object_refs) == 2
        assert result.object_refs[0].name == "@lantern"
        assert result.object_refs[1].name == "@table"
        assert result.anchors == ["@atomic-lantern"]


class TestSceneRendererUnit:
    """Unit tests for SceneRenderer (without GPU)."""

    def test_init(self):
        """SceneRenderer can be initialized."""
        from gnusto.scene_renderer import SceneRenderer

        # Create a minimal mock runtime
        runtime = Mock()
        runtime.world = Mock()
        runtime.world.rooms = {}
        runtime.world.objects = {}

        renderer = SceneRenderer(
            runtime=runtime,
            cache_dir="/tmp/test-cache",
            assets_dir="/tmp/test-assets",
        )

        assert renderer.runtime == runtime
        assert renderer.default_ref_size == 384
        assert renderer._max_depth == 3

    def test_render_room_no_spec(self):
        """render_room returns None if room has no render spec."""
        from gnusto.scene_renderer import SceneRenderer

        runtime = Mock()
        runtime.world = Mock()
        room = Mock()
        room.render = None  # No render spec
        runtime.world.rooms = {"@test-room": room}

        renderer = SceneRenderer(runtime=runtime, cache_dir="/tmp/test-cache")
        result = renderer.render_room("@test-room")

        assert result is None

    def test_render_room_missing(self):
        """render_room returns None for non-existent room."""
        from gnusto.scene_renderer import SceneRenderer

        runtime = Mock()
        runtime.world = Mock()
        runtime.world.rooms = {}

        renderer = SceneRenderer(runtime=runtime, cache_dir="/tmp/test-cache")
        result = renderer.render_room("@nonexistent")

        assert result is None


class TestCacheIntegration:
    """Test render caching integration."""

    def test_cache_key_consistency(self):
        """Same render spec produces same cache key."""
        cache = RenderCache("/tmp/test-cache")

        key1 = cache.compute_key(
            "A brass lantern on a wooden table",
            ref_hashes=["abc123", "def456"]
        )
        key2 = cache.compute_key(
            "A brass lantern on a wooden table",
            ref_hashes=["abc123", "def456"]
        )

        assert key1 == key2

    def test_different_refs_different_key(self):
        """Different refs produce different cache keys."""
        cache = RenderCache("/tmp/test-cache")

        key1 = cache.compute_key("A scene", ref_hashes=["abc123"])
        key2 = cache.compute_key("A scene", ref_hashes=["xyz789"])

        assert key1 != key2


class MockState:
    """Mock WorldState for testing."""

    def get_object_location(self, obj: str):
        return None

    def get_object_property(self, obj: str, prop: str):
        return None

    def get_global(self, name: str):
        return None

    def get_player_location(self) -> str:
        return "@player-room"

    def get_player_name(self) -> str:
        return "@player"

    def get_inventory(self) -> list[str]:
        return []

    def is_visible(self, obj: str) -> bool:
        return True
