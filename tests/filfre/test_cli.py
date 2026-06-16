"""Tests for filfre CLI utilities."""

import pytest


class TestTimedContextManager:
    """Test the timed context manager."""

    def test_timed_runs_code(self, capsys):
        from filfre.cli import timed

        with timed("test"):
            pass  # Just ensure it completes

        captured = capsys.readouterr()
        assert "[test]" in captured.out
        assert "s" in captured.out  # should have time suffix


class TestLoadReferenceImages:
    """Test loading and preprocessing reference images."""

    def test_load_single_image(self, tmp_path):
        from PIL import Image

        from filfre.cli import load_reference_images

        # Create a test image
        img_path = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(img_path)

        images = load_reference_images([str(img_path)])

        assert len(images) == 1
        assert images[0].mode == "RGB"
        assert images[0].size == (100, 100)

    def test_load_with_resize(self, tmp_path):
        from PIL import Image

        from filfre.cli import load_reference_images

        img_path = tmp_path / "test.png"
        img = Image.new("RGB", (200, 200), color="blue")
        img.save(img_path)

        images = load_reference_images([str(img_path)], size=64)

        assert images[0].size == (64, 64)

    def test_load_multiple_images(self, tmp_path):
        from PIL import Image

        from filfre.cli import load_reference_images

        paths = []
        for i in range(3):
            path = tmp_path / f"test{i}.png"
            Image.new("RGB", (100, 100)).save(path)
            paths.append(str(path))

        images = load_reference_images(paths)

        assert len(images) == 3


class TestModelConstants:
    """Test model constants."""

    def test_nanobanana_model_id(self):
        from filfre.cli import NANOBANANA_MODEL_ID

        assert "gemini" in NANOBANANA_MODEL_ID


class TestCLIParsing:
    """Test CLI argument parsing."""

    def test_generate_requires_prompt(self):
        import sys

        from filfre.cli import main

        original_argv = sys.argv
        try:
            sys.argv = ["filfre", "generate"]
            with pytest.raises(SystemExit):
                main()
        finally:
            sys.argv = original_argv

    def test_no_command_shows_help(self, capsys):
        import sys

        from filfre.cli import main

        original_argv = sys.argv
        try:
            sys.argv = ["filfre"]
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
        finally:
            sys.argv = original_argv
