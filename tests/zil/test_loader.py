"""Tests for ZIL loader."""

import pytest
import tempfile
from pathlib import Path
from zil import parse_file, parse_directory, parse_with_includes, load_game


class TestParseFile:
    """Test parsing single files."""

    def test_parse_file(self, tmp_path):
        zil_file = tmp_path / "test.zil"
        zil_file.write_text('<ROOM KITCHEN (IN ROOMS)>')
        ast = parse_file(zil_file)
        assert len(ast) == 1
        assert ast[0].operator.name == "ROOM"

    def test_parse_file_string_path(self, tmp_path):
        zil_file = tmp_path / "test.zil"
        zil_file.write_text('<OBJECT LAMP>')
        ast = parse_file(str(zil_file))
        assert len(ast) == 1


class TestParseDirectory:
    """Test parsing all files in a directory."""

    def test_parse_multiple_files(self, tmp_path):
        (tmp_path / "rooms.zil").write_text('<ROOM KITCHEN>')
        (tmp_path / "objects.zil").write_text('<OBJECT LAMP>')
        ast = parse_directory(tmp_path)
        ops = [n.operator.name for n in ast]
        assert "ROOM" in ops
        assert "OBJECT" in ops

    def test_only_zil_files(self, tmp_path):
        (tmp_path / "game.zil").write_text('<ROOM START>')
        (tmp_path / "readme.txt").write_text("Not ZIL")
        ast = parse_directory(tmp_path)
        assert len(ast) == 1

    def test_empty_directory(self, tmp_path):
        ast = parse_directory(tmp_path)
        assert ast == []


class TestParseWithIncludes:
    """Test parsing with INSERT-FILE support."""

    def test_include_file(self, tmp_path):
        main = tmp_path / "main.zil"
        included = tmp_path / "rooms.zil"
        main.write_text('''
            <INSERT-FILE "rooms.zil">
            <OBJECT LAMP>
        ''')
        included.write_text('<ROOM KITCHEN>')

        ast = parse_with_includes(main)
        ops = [n.operator.name for n in ast]
        assert "ROOM" in ops
        assert "OBJECT" in ops
        # INSERT-FILE directive should not appear
        assert "INSERT-FILE" not in ops

    def test_nested_includes(self, tmp_path):
        main = tmp_path / "main.zil"
        middle = tmp_path / "middle.zil"
        inner = tmp_path / "inner.zil"
        main.write_text('<INSERT-FILE "middle.zil">')
        middle.write_text('''
            <ROOM START>
            <INSERT-FILE "inner.zil">
        ''')
        inner.write_text('<OBJECT LAMP>')

        ast = parse_with_includes(main)
        ops = [n.operator.name for n in ast]
        assert "ROOM" in ops
        assert "OBJECT" in ops

    def test_circular_includes_handled(self, tmp_path):
        file_a = tmp_path / "a.zil"
        file_b = tmp_path / "b.zil"
        file_a.write_text('''
            <ROOM A>
            <INSERT-FILE "b.zil">
        ''')
        file_b.write_text('''
            <ROOM B>
            <INSERT-FILE "a.zil">
        ''')

        # Should not infinite loop
        ast = parse_with_includes(file_a)
        rooms = [n for n in ast if n.operator and n.operator.name == "ROOM"]
        assert len(rooms) == 2

    def test_missing_include_ignored(self, tmp_path):
        main = tmp_path / "main.zil"
        main.write_text('''
            <INSERT-FILE "missing.zil">
            <ROOM START>
        ''')
        ast = parse_with_includes(main)
        assert len(ast) == 1
        assert ast[0].operator.name == "ROOM"


class TestLoadGame:
    """Test the high-level load_game function."""

    def test_load_from_file(self, tmp_path):
        game_file = tmp_path / "game.zil"
        game_file.write_text('''
            <ROOM START (IN ROOMS) (DESC "Start")>
            <OBJECT LAMP (IN START)>
            <CONSTANT TITLE "Test">
        ''')
        data = load_game(game_file)
        assert "START" in data.rooms
        assert "LAMP" in data.objects
        assert "TITLE" in data.constants

    def test_load_from_directory(self, tmp_path):
        (tmp_path / "rooms.zil").write_text('<ROOM KITCHEN (IN ROOMS)>')
        (tmp_path / "objects.zil").write_text('<OBJECT LAMP (IN KITCHEN)>')
        data = load_game(tmp_path)
        assert "KITCHEN" in data.rooms
        assert "LAMP" in data.objects

    def test_load_with_main_file(self, tmp_path):
        # Create game.name/game.name.zil pattern
        game_dir = tmp_path / "mygame"
        game_dir.mkdir()
        main = game_dir / "mygame.zil"
        rooms = game_dir / "rooms.zil"
        main.write_text('<INSERT-FILE "rooms.zil">')
        rooms.write_text('<ROOM START (IN ROOMS)>')

        data = load_game(game_dir)
        assert "START" in data.rooms

    def test_load_nonexistent_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_game(tmp_path / "nonexistent")

    def test_load_without_includes(self, tmp_path):
        main = tmp_path / "main.zil"
        included = tmp_path / "included.zil"
        main.write_text('''
            <INSERT-FILE "included.zil">
            <ROOM MAIN>
        ''')
        included.write_text('<ROOM INCLUDED>')

        # With use_includes=False, should not follow INSERT-FILE
        data = load_game(main, use_includes=False)
        assert "MAIN" in data.rooms
        # INSERT-FILE is not a ROOM, so it won't create a room
        assert "INCLUDED" not in data.rooms
