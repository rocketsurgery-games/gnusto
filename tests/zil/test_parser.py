"""Tests for ZIL parser."""

import pytest
from zil import parse, Atom, Number, String, Form, List
from zil.parser import ParseError


class TestBasicParsing:
    """Test parsing of basic elements."""

    def test_empty_input(self):
        ast = parse("")
        assert ast == []

    def test_single_atom(self):
        ast = parse("ROOM")
        assert len(ast) == 1
        assert isinstance(ast[0], Atom)
        assert ast[0].name == "ROOM"

    def test_number(self):
        ast = parse("42")
        assert len(ast) == 1
        assert isinstance(ast[0], Number)
        assert ast[0].value == 42

    def test_string(self):
        ast = parse('"Hello"')
        assert len(ast) == 1
        assert isinstance(ast[0], String)
        assert ast[0].value == "Hello"

    def test_multiple_atoms(self):
        ast = parse("ONE TWO THREE")
        assert len(ast) == 3
        assert [a.name for a in ast] == ["ONE", "TWO", "THREE"]


class TestFormParsing:
    """Test parsing of forms <...>."""

    def test_empty_form(self):
        ast = parse("<>")
        assert len(ast) == 1
        assert isinstance(ast[0], Form)
        assert ast[0].elements == []

    def test_simple_form(self):
        ast = parse("<TELL>")
        assert len(ast) == 1
        form = ast[0]
        assert isinstance(form, Form)
        assert form.operator.name == "TELL"

    def test_form_with_args(self):
        ast = parse('<TELL "Hello" 42>')
        form = ast[0]
        assert form.operator.name == "TELL"
        assert len(form.args) == 2
        assert isinstance(form.args[0], String)
        assert isinstance(form.args[1], Number)

    def test_nested_forms(self):
        ast = parse("<OUTER <INNER>>")
        outer = ast[0]
        assert outer.operator.name == "OUTER"
        assert len(outer.args) == 1
        inner = outer.args[0]
        assert isinstance(inner, Form)
        assert inner.operator.name == "INNER"

    def test_form_source_location(self):
        ast = parse("<FORM>")
        assert ast[0].line == 1
        assert ast[0].column == 1


class TestListParsing:
    """Test parsing of lists (...)."""

    def test_empty_list(self):
        ast = parse("()")
        assert len(ast) == 1
        assert isinstance(ast[0], List)
        assert ast[0].elements == []

    def test_simple_list(self):
        ast = parse("(IN ROOMS)")
        lst = ast[0]
        assert isinstance(lst, List)
        assert len(lst.elements) == 2
        assert lst.elements[0].name == "IN"
        assert lst.elements[1].name == "ROOMS"

    def test_list_with_mixed_types(self):
        ast = parse('(DESC "A room" 42)')
        lst = ast[0]
        assert len(lst.elements) == 3
        assert isinstance(lst.elements[0], Atom)
        assert isinstance(lst.elements[1], String)
        assert isinstance(lst.elements[2], Number)


class TestNestedStructures:
    """Test nested forms and lists."""

    def test_form_containing_list(self):
        ast = parse("<ROOM FOO (IN ROOMS)>")
        form = ast[0]
        assert form.operator.name == "ROOM"
        assert isinstance(form.args[0], Atom)
        assert isinstance(form.args[1], List)

    def test_list_containing_form(self):
        ast = parse("(<PLUS 1 2>)")
        lst = ast[0]
        assert len(lst.elements) == 1
        assert isinstance(lst.elements[0], Form)

    def test_deeply_nested(self):
        ast = parse("<A (<B <C>>)>")
        outer = ast[0]
        assert outer.operator.name == "A"
        inner_list = outer.args[0]
        inner_form1 = inner_list.elements[0]
        assert inner_form1.operator.name == "B"
        inner_form2 = inner_form1.args[0]
        assert inner_form2.operator.name == "C"


class TestCommentSkipping:
    """Test that comments are properly skipped."""

    def test_commented_form_skipped(self):
        ast = parse("BEFORE ;<IGNORED> AFTER")
        names = [n.name for n in ast if isinstance(n, Atom)]
        assert names == ["BEFORE", "AFTER"]

    def test_commented_list_skipped(self):
        ast = parse("BEFORE ;(IGNORED) AFTER")
        names = [n.name for n in ast if isinstance(n, Atom)]
        assert names == ["BEFORE", "AFTER"]

    def test_nested_comment_form(self):
        ast = parse(";<OUTER ;<INNER>>")
        assert ast == []


class TestRealWorldExamples:
    """Test parsing of realistic ZIL constructs."""

    def test_room_definition(self):
        source = '''<ROOM KITCHEN
            (IN ROOMS)
            (DESC "A kitchen with a window")
            (NORTH TO HALLWAY)
            (FLAGS LIGHTBIT CONTBIT)>'''
        ast = parse(source)
        room = ast[0]
        assert room.operator.name == "ROOM"
        assert room.args[0].name == "KITCHEN"
        # Count property lists
        props = [a for a in room.args if isinstance(a, List)]
        assert len(props) == 4

    def test_routine_definition(self):
        source = '''<ROUTINE V-TAKE ("AUX" OBJ)
            <COND (<FSET? ,PRSO ,TAKEBIT>
                <MOVE ,PRSO ,WINNER>
                <TELL "Taken.">)>>'''
        ast = parse(source)
        routine = ast[0]
        assert routine.operator.name == "ROUTINE"
        assert routine.args[0].name == "V-TAKE"

    def test_syntax_definition(self):
        source = '<SYNTAX TAKE OBJECT (HELD MANY HAVE) = V-TAKE PRE-TAKE>'
        ast = parse(source)
        syntax = ast[0]
        assert syntax.operator.name == "SYNTAX"


class TestParseErrors:
    """Test parse error handling."""

    def test_unterminated_form(self):
        with pytest.raises(ParseError, match="Unterminated form"):
            parse("<UNCLOSED")

    def test_unterminated_list(self):
        with pytest.raises(ParseError, match="Unterminated list"):
            parse("(UNCLOSED")

    def test_nested_unterminated(self):
        with pytest.raises(ParseError):
            parse("<OUTER <INNER>")
