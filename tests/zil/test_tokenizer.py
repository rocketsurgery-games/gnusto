"""Tests for ZIL tokenizer."""

import pytest
from zil import tokenize, Token, TokenType, ZILTokenizer


class TestBasicTokens:
    """Test basic token recognition."""

    def test_empty_input(self):
        tokens = tokenize("")
        assert tokens == []

    def test_whitespace_only(self):
        tokens = tokenize("   \n\t  ")
        assert tokens == []

    def test_single_atom(self):
        tokens = tokenize("ROOM")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.ATOM
        assert tokens[0].value == "ROOM"

    def test_atom_with_prefix(self):
        tokens = tokenize(",HERE .X %FOO !BAR")
        assert len(tokens) == 4
        assert [t.value for t in tokens] == [",HERE", ".X", "%FOO", "!BAR"]

    def test_number(self):
        tokens = tokenize("42")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "42"

    def test_negative_number(self):
        tokens = tokenize("-1")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "-1"

    def test_string(self):
        tokens = tokenize('"Hello, world!"')
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "Hello, world!"

    def test_string_with_escapes(self):
        tokens = tokenize(r'"line1\nline2"')
        assert tokens[0].value == "line1\nline2"

    def test_string_with_quote_escape(self):
        tokens = tokenize(r'"He said \"hello\""')
        assert tokens[0].value == 'He said "hello"'


class TestDelimiters:
    """Test delimiter tokens."""

    def test_form_delimiters(self):
        tokens = tokenize("<>")
        assert len(tokens) == 2
        assert tokens[0].type == TokenType.FORM_OPEN
        assert tokens[1].type == TokenType.FORM_CLOSE

    def test_list_delimiters(self):
        tokens = tokenize("()")
        assert len(tokens) == 2
        assert tokens[0].type == TokenType.LIST_OPEN
        assert tokens[1].type == TokenType.LIST_CLOSE

    def test_nested_delimiters(self):
        tokens = tokenize("<()>")
        types = [t.type for t in tokens]
        assert types == [
            TokenType.FORM_OPEN,
            TokenType.LIST_OPEN,
            TokenType.LIST_CLOSE,
            TokenType.FORM_CLOSE,
        ]


class TestComments:
    """Test comment handling."""

    def test_line_comment(self):
        tokens = tokenize("ATOM ; this is a comment\nNEXT")
        assert len(tokens) == 2
        assert tokens[0].value == "ATOM"
        assert tokens[1].value == "NEXT"

    def test_comment_string(self):
        tokens = tokenize('BEFORE ;"ignored comment" AFTER')
        assert len(tokens) == 2
        assert tokens[0].value == "BEFORE"
        assert tokens[1].value == "AFTER"

    def test_comment_form(self):
        # The tokenizer returns a COMMENT token followed by the form tokens.
        # The parser is responsible for skipping the expression after COMMENT.
        tokens = tokenize("BEFORE ;<IGNORED STUFF> AFTER")
        assert tokens[0].value == "BEFORE"
        assert tokens[1].type == TokenType.COMMENT
        # Form tokens follow - parser will skip them
        assert tokens[2].type == TokenType.FORM_OPEN
        # Last token should be AFTER
        assert tokens[-1].value == "AFTER"

    def test_comment_atom(self):
        tokens = tokenize("BEFORE ;IGNORED AFTER")
        assert len(tokens) == 2
        assert tokens[0].value == "BEFORE"
        assert tokens[1].value == "AFTER"


class TestComplexExamples:
    """Test complete ZIL constructs."""

    def test_simple_form(self):
        tokens = tokenize('<TELL "Hello">')
        assert len(tokens) == 4
        assert tokens[0].type == TokenType.FORM_OPEN
        assert tokens[1].value == "TELL"
        assert tokens[2].value == "Hello"
        assert tokens[3].type == TokenType.FORM_CLOSE

    def test_room_definition(self):
        source = '''<ROOM KITCHEN
            (IN ROOMS)
            (DESC "A kitchen")
            (FLAGS LIGHTBIT)>'''
        tokens = tokenize(source)
        assert tokens[0].type == TokenType.FORM_OPEN
        assert tokens[1].value == "ROOM"
        assert tokens[2].value == "KITCHEN"

    def test_position_tracking(self):
        tokens = tokenize("LINE1\nLINE2")
        assert tokens[0].line == 1
        assert tokens[0].column == 1
        assert tokens[1].line == 2
        assert tokens[1].column == 1


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_unterminated_string_raises(self):
        with pytest.raises(SyntaxError, match="Unterminated string"):
            tokenize('"unclosed')

    def test_section_separator(self):
        # Backslash at start of line with control char is section break
        tokens = tokenize("BEFORE\n\\SECTION\nAFTER")
        # Section separator should be skipped
        values = [t.value for t in tokens if t.type == TokenType.ATOM]
        assert "BEFORE" in values
        assert "AFTER" in values

    def test_escaped_delimiter_in_atom(self):
        # \. in an atom should include the period
        tokens = tokenize(r"P\.NORTH")
        assert len(tokens) == 1
        assert tokens[0].value == "P.NORTH"
