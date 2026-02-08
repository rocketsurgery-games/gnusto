"""Tests for terminal image display."""

import pytest
import io
from pathlib import Path
from unittest.mock import patch


class TestDetectProtocol:
    """Test terminal protocol detection."""

    def test_detect_none(self):
        from gnusto.terminal_images import detect_protocol

        with patch("gnusto.terminal_images._TERM", "xterm"):
            with patch("gnusto.terminal_images._TERM_PROGRAM", ""):
                with patch("gnusto.terminal_images._KITTY_WINDOW_ID", ""):
                    with patch("gnusto.terminal_images._WEZTERM_PANE", ""):
                        assert detect_protocol() == "none"

    def test_detect_kitty_by_window_id(self):
        from gnusto.terminal_images import detect_protocol

        with patch("gnusto.terminal_images._KITTY_WINDOW_ID", "123"):
            assert detect_protocol() == "kitty"

    def test_detect_kitty_by_term(self):
        from gnusto.terminal_images import detect_protocol

        with patch("gnusto.terminal_images._KITTY_WINDOW_ID", ""):
            with patch("gnusto.terminal_images._WEZTERM_PANE", ""):
                with patch("gnusto.terminal_images._TERM", "xterm-kitty"):
                    with patch("gnusto.terminal_images._TERM_PROGRAM", ""):
                        assert detect_protocol() == "kitty"

    def test_detect_wezterm(self):
        from gnusto.terminal_images import detect_protocol

        with patch("gnusto.terminal_images._KITTY_WINDOW_ID", ""):
            with patch("gnusto.terminal_images._WEZTERM_PANE", "1"):
                assert detect_protocol() == "kitty"

    def test_detect_iterm2(self):
        from gnusto.terminal_images import detect_protocol

        with patch("gnusto.terminal_images._KITTY_WINDOW_ID", ""):
            with patch("gnusto.terminal_images._WEZTERM_PANE", ""):
                with patch("gnusto.terminal_images._TERM", "xterm"):
                    with patch("gnusto.terminal_images._TERM_PROGRAM", "iTerm.app"):
                        assert detect_protocol() == "iterm2"

    def test_detect_ghostty(self):
        from gnusto.terminal_images import detect_protocol

        with patch("gnusto.terminal_images._KITTY_WINDOW_ID", ""):
            with patch("gnusto.terminal_images._WEZTERM_PANE", ""):
                with patch("gnusto.terminal_images._TERM", "ghostty"):
                    with patch("gnusto.terminal_images._TERM_PROGRAM", ""):
                        assert detect_protocol() == "kitty"


class TestIsSupported:
    """Test is_supported function."""

    def test_supported_with_kitty(self):
        from gnusto.terminal_images import is_supported

        with patch("gnusto.terminal_images.detect_protocol", return_value="kitty"):
            assert is_supported() is True

    def test_supported_with_iterm2(self):
        from gnusto.terminal_images import is_supported

        with patch("gnusto.terminal_images.detect_protocol", return_value="iterm2"):
            assert is_supported() is True

    def test_not_supported(self):
        from gnusto.terminal_images import is_supported

        with patch("gnusto.terminal_images.detect_protocol", return_value="none"):
            assert is_supported() is False


class TestDisplayImage:
    """Test display_image function."""

    def test_returns_false_when_unsupported(self, tmp_path):
        from gnusto.terminal_images import display_image
        from PIL import Image

        # Create a test image
        img_path = tmp_path / "test.png"
        Image.new("RGB", (10, 10)).save(img_path)

        with patch("gnusto.terminal_images.detect_protocol", return_value="none"):
            result = display_image(img_path)
            assert result is False

    def test_returns_false_for_missing_file(self):
        from gnusto.terminal_images import display_image

        with patch("gnusto.terminal_images.detect_protocol", return_value="kitty"):
            result = display_image("/nonexistent/path.png")
            assert result is False

    def test_kitty_output_format(self, tmp_path):
        from gnusto.terminal_images import display_image
        from PIL import Image

        # Create a test image
        img_path = tmp_path / "test.png"
        Image.new("RGB", (10, 10), color="red").save(img_path)

        output = io.StringIO()

        with patch("gnusto.terminal_images.detect_protocol", return_value="kitty"):
            result = display_image(img_path, file=output)

        assert result is True
        content = output.getvalue()
        # Check for Kitty escape sequence
        assert "\033_G" in content
        assert "\033\\" in content

    def test_iterm2_output_format(self, tmp_path):
        from gnusto.terminal_images import display_image
        from PIL import Image

        img_path = tmp_path / "test.png"
        Image.new("RGB", (10, 10), color="blue").save(img_path)

        output = io.StringIO()

        with patch("gnusto.terminal_images.detect_protocol", return_value="iterm2"):
            result = display_image(img_path, file=output)

        assert result is True
        content = output.getvalue()
        # Check for iTerm2 escape sequence
        assert "\033]1337;File=" in content


class TestDisplayPilImage:
    """Test display_pil_image function."""

    def test_returns_false_when_unsupported(self):
        from gnusto.terminal_images import display_pil_image
        from PIL import Image

        img = Image.new("RGB", (10, 10))

        with patch("gnusto.terminal_images.detect_protocol", return_value="none"):
            result = display_pil_image(img)
            assert result is False

    def test_kitty_pil_output(self):
        from gnusto.terminal_images import display_pil_image
        from PIL import Image

        img = Image.new("RGB", (10, 10), color="green")
        output = io.StringIO()

        with patch("gnusto.terminal_images.detect_protocol", return_value="kitty"):
            result = display_pil_image(img, file=output)

        assert result is True
        assert "\033_G" in output.getvalue()


class TestGetTerminalSize:
    """Test get_terminal_size function."""

    def test_returns_default_on_error(self):
        from gnusto.terminal_images import get_terminal_size

        with patch("os.get_terminal_size", side_effect=OSError):
            cols, rows = get_terminal_size()
            assert cols == 80
            assert rows == 24

    def test_returns_actual_size(self):
        from gnusto.terminal_images import get_terminal_size
        from unittest.mock import Mock

        mock_size = Mock()
        mock_size.columns = 120
        mock_size.lines = 40

        with patch("os.get_terminal_size", return_value=mock_size):
            cols, rows = get_terminal_size()
            assert cols == 120
            assert rows == 40
