"""Tests for GRUE converter."""

import pytest
from grue import convert_zil_to_grue, ast_to_zil, routine_to_zil
from zil.ast import Atom, Number, String, Form, List
from zil.extractor import Routine


class TestAstToZil:
    """Test ZIL AST serialization."""

    def test_atom(self):
        node = Atom(name="FOO")
        assert ast_to_zil(node) == "FOO"

    def test_number(self):
        node = Number(value=42)
        assert ast_to_zil(node) == "42"

    def test_string(self):
        node = String(value="hello")
        assert ast_to_zil(node) == '"hello"'

    def test_string_with_quotes(self):
        node = String(value='say "hi"')
        assert ast_to_zil(node) == '"say \\"hi\\""'

    def test_simple_form(self):
        node = Form(elements=[Atom(name="TELL"), String(value="Hello")])
        assert ast_to_zil(node) == '<TELL "Hello">'

    def test_simple_list(self):
        node = List(elements=[Atom(name="A"), Atom(name="B")])
        assert ast_to_zil(node) == "(A B)"

    def test_nested_form(self):
        inner = Form(elements=[Atom(name="VERB?"), Atom(name="TAKE")])
        outer = Form(elements=[Atom(name="COND"), List(elements=[inner, Atom(name="RTRUE")])])
        result = ast_to_zil(outer)
        assert "<VERB? TAKE>" in result
        assert "RTRUE" in result


class TestRoutineToZil:
    """Test routine serialization."""

    def test_simple_routine(self):
        r = Routine(
            name="FOO-F",
            args=[],
            aux_vars=[],
            optional_args=[],
            body=[Form(elements=[Atom(name="RTRUE")])],
        )
        result = routine_to_zil(r)
        assert "ROUTINE FOO-F ()" in result
        assert "<RTRUE>" in result

    def test_routine_with_args(self):
        r = Routine(
            name="BAR-F",
            args=["X", "Y"],
            aux_vars=["Z"],
            optional_args=[],
            body=[],
        )
        result = routine_to_zil(r)
        assert "ROUTINE BAR-F (X Y" in result
        assert '"AUX"' in result
        assert "Z)" in result


class TestConversion:
    """Test full conversion flow."""

    def test_conversion_returns_result(self):
        # Minimal fake GameData
        from zil.extractor import GameData, ZILObject, Property

        data = GameData()
        room = ZILObject(name="TEST-ROOM", kind="room")
        room.properties["DESC"] = Property(name="DESC", values=["A room"])
        room.properties["FLAGS"] = Property(name="FLAGS", values=["ONBIT"])
        data.rooms["TEST-ROOM"] = room

        result = convert_zil_to_grue(data, name="Test Game")

        assert result.grue_source
        assert "Test Game" in result.grue_source
        assert "@test-room" in result.grue_source  # Now uses @lowercase naming
        assert result.stats["rooms"] == 1
