"""Tests for filfre CLI utilities."""

import pytest
from pathlib import Path


class TestGetGameDirs:
    """Test the get_game_dirs utility."""

    def test_directory_path(self, tmp_path):
        from filfre.cli import get_game_dirs

        game_dir, renders_dir, assets_dir = get_game_dirs(tmp_path)

        assert game_dir == tmp_path
        assert renders_dir == tmp_path / "assets" / "renders"
        assert assets_dir == tmp_path / "assets"

    def test_file_path(self, tmp_path):
        from filfre.cli import get_game_dirs

        game_file = tmp_path / "game.grue"
        game_file.write_text("test")

        game_dir, renders_dir, assets_dir = get_game_dirs(game_file)

        # Should use parent directory
        assert game_dir == tmp_path
        assert renders_dir == tmp_path / "assets" / "renders"

    def test_string_path(self, tmp_path):
        from filfre.cli import get_game_dirs

        game_dir, renders_dir, assets_dir = get_game_dirs(str(tmp_path))

        assert game_dir == tmp_path


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
        from filfre.cli import load_reference_images
        from PIL import Image

        # Create a test image
        img_path = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(img_path)

        images = load_reference_images([str(img_path)])

        assert len(images) == 1
        assert images[0].mode == "RGB"
        assert images[0].size == (100, 100)

    def test_load_with_resize(self, tmp_path):
        from filfre.cli import load_reference_images
        from PIL import Image

        img_path = tmp_path / "test.png"
        img = Image.new("RGB", (200, 200), color="blue")
        img.save(img_path)

        images = load_reference_images([str(img_path)], size=64)

        assert images[0].size == (64, 64)

    def test_load_multiple_images(self, tmp_path):
        from filfre.cli import load_reference_images
        from PIL import Image

        paths = []
        for i in range(3):
            path = tmp_path / f"test{i}.png"
            Image.new("RGB", (100, 100)).save(path)
            paths.append(str(path))

        images = load_reference_images(paths)

        assert len(images) == 3


class TestModelConstants:
    """Test model name constants."""

    def test_valid_models_list(self):
        from filfre.cli import VALID_MODELS, MODEL_FLUX, MODEL_NANOBANANA

        assert MODEL_FLUX in VALID_MODELS
        assert MODEL_NANOBANANA in VALID_MODELS

    def test_model_versions(self):
        from filfre.cli import MODEL_VERSIONS, MODEL_FLUX, MODEL_NANOBANANA

        assert MODEL_FLUX in MODEL_VERSIONS
        assert MODEL_NANOBANANA in MODEL_VERSIONS
        assert "flux" in MODEL_VERSIONS[MODEL_FLUX]
        assert "gemini" in MODEL_VERSIONS[MODEL_NANOBANANA]


class TestCLIParsing:
    """Test CLI argument parsing."""

    def test_generate_requires_model(self):
        from filfre.cli import main
        import sys

        original_argv = sys.argv
        try:
            sys.argv = ["filfre", "generate", "--prompt", "test"]
            with pytest.raises(SystemExit):
                main()
        finally:
            sys.argv = original_argv

    def test_generate_requires_prompt(self):
        from filfre.cli import main
        import sys

        original_argv = sys.argv
        try:
            sys.argv = ["filfre", "generate", "--model", "flux"]
            with pytest.raises(SystemExit):
                main()
        finally:
            sys.argv = original_argv

    def test_no_command_shows_help(self, capsys):
        from filfre.cli import main
        import sys

        original_argv = sys.argv
        try:
            sys.argv = ["filfre"]
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
        finally:
            sys.argv = original_argv
