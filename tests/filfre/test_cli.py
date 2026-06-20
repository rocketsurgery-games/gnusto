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


# A minimal game world used by the manifest-driven brief/fill tests.
_GAME_SRC = """
(world :name "Test Game" :player @player
  :visual-style (:prompt "Inked horror." :palette "dark blues" :aspect-ratio "1:1"))
(object @player :description "you")
(room @lab :description "Lab" :rdesc "An empty dingy lab.")
(object @microwave
  :description "microwave"
  :render (fn () (if (:open self) "open" "closed"))
  :rdesc (:open "Microwave, door open." :closed "Microwave, door closed."))
"""


def _make_game(tmp_path):
    """Write a minimal game dir and return its path."""
    game = tmp_path / "game"
    game.mkdir()
    (game / "game.grue").write_text(_GAME_SRC)
    return game


class TestBriefCommand:
    """filfre brief: per-key briefs (no network)."""

    def test_brief_print_shows_full_prompt_per_key(self, tmp_path, capsys):
        from argparse import Namespace

        from filfre.cli import cmd_brief

        cmd_brief(Namespace(game=str(_make_game(tmp_path)), out=None, key=None))
        out = capsys.readouterr().out
        # The style preamble is kind-specific now, so the full composed prompt is
        # shown per key (style appears once per entry, not hoisted once overall).
        assert out.count("Inked horror.") == 3
        assert "microwave-open" in out
        assert "microwave-closed" in out
        assert "lab" in out

    def test_brief_out_writes_full_prompts(self, tmp_path):
        from argparse import Namespace

        from filfre.cli import cmd_brief

        out_dir = tmp_path / "briefs"
        cmd_brief(Namespace(game=str(_make_game(tmp_path)), out=str(out_dir), key=None))
        text = (out_dir / "microwave-open.txt").read_text()
        # Each file carries the full prompt: style preamble + entity brief.
        assert text.startswith(
            "Inked horror. Palette: dark blues. Microwave, door open."
        )
        assert {p.name for p in out_dir.glob("*.txt")} == {
            "lab.txt",
            "microwave-open.txt",
            "microwave-closed.txt",
        }

    def test_brief_key_filter(self, tmp_path, capsys):
        from argparse import Namespace

        from filfre.cli import cmd_brief

        cmd_brief(Namespace(game=str(_make_game(tmp_path)), out=None, key=["lab"]))
        out = capsys.readouterr().out
        assert "lab" in out
        assert "microwave-open" not in out


class TestFillDryRun:
    """filfre fill --dry-run: prompt preview without calling the model."""

    def test_dry_run_lists_all_when_no_assets(self, tmp_path, capsys):
        from argparse import Namespace

        from filfre.cli import cmd_fill

        cmd_fill(
            Namespace(
                game=str(_make_game(tmp_path)),
                key=None,
                force=False,
                aspect_ratio=None,
                seed=0,
                dry_run=True,
            )
        )
        out = capsys.readouterr().out
        assert "To generate: 3" in out
        assert "microwave-open.jpg" in out
        # Full prompt previewed (style preamble + brief).
        assert "Inked horror. Palette: dark blues. Microwave, door open." in out

    def test_dry_run_skips_existing(self, tmp_path, capsys):
        from argparse import Namespace

        from PIL import Image

        from filfre.cli import cmd_fill

        game = _make_game(tmp_path)
        assets = game / "assets"
        assets.mkdir()
        Image.new("RGB", (8, 8)).save(assets / "lab.jpg")

        cmd_fill(
            Namespace(
                game=str(game),
                key=None,
                force=False,
                aspect_ratio=None,
                seed=0,
                dry_run=True,
            )
        )
        out = capsys.readouterr().out
        assert "To generate: 2" in out
        assert "skipping 1" in out


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
