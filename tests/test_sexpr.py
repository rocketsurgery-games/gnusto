"""Tests for S-expression parser."""

import pytest
from grue.sexpr import (
    parse, parse_all, to_string,
    Symbol, Keyword, SList,
    SExprError, Tokenizer, TokenType
)


class TestTokenizer:
    """Test the tokenizer."""

    def test_simple_tokens(self):
        tokens = Tokenizer("( ) foo").tokenize()
        assert tokens[0].type == TokenType.LPAREN
        assert tokens[1].type == TokenType.RPAREN
        assert tokens[2].type == TokenType.SYMBOL
        assert tokens[2].value == "foo"

    def test_numbers(self):
        tokens = Tokenizer("42 -17 0").tokenize()
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 42
        assert tokens[1].type == TokenType.NUMBER
        assert tokens[1].value == -17
        assert tokens[2].type == TokenType.NUMBER
        assert tokens[2].value == 0

    def test_strings(self):
        tokens = Tokenizer('"hello" "world"').tokenize()
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "hello"
        assert tokens[1].type == TokenType.STRING
        assert tokens[1].value == "world"

    def test_string_escapes(self):
        tokens = Tokenizer(r'"hello\nworld" "quote\"here"').tokenize()
        assert tokens[0].value == "hello\nworld"
        assert tokens[1].value == 'quote"here'

    def test_keywords(self):
        tokens = Tokenizer(":locked :description").tokenize()
        assert tokens[0].type == TokenType.KEYWORD
        assert tokens[0].value == "locked"
        assert tokens[1].type == TokenType.KEYWORD
        assert tokens[1].value == "description"

    def test_booleans(self):
        tokens = Tokenizer("true false TRUE FALSE").tokenize()
        assert tokens[0].type == TokenType.BOOL_TRUE
        assert tokens[0].value is True
        assert tokens[1].type == TokenType.BOOL_FALSE
        assert tokens[1].value is False
        assert tokens[2].type == TokenType.BOOL_TRUE
        assert tokens[3].type == TokenType.BOOL_FALSE

    def test_symbols_with_special_chars(self):
        tokens = Tokenizer("has-flag? set! >= <=").tokenize()
        assert tokens[0].type == TokenType.SYMBOL
        assert tokens[0].value == "has-flag?"
        assert tokens[1].type == TokenType.SYMBOL
        assert tokens[1].value == "set!"

    def test_comments(self):
        tokens = Tokenizer("foo ; this is a comment\nbar").tokenize()
        assert tokens[0].type == TokenType.SYMBOL
        assert tokens[0].value == "foo"
        assert tokens[1].type == TokenType.SYMBOL
        assert tokens[1].value == "bar"

    def test_line_tracking(self):
        tokens = Tokenizer("foo\nbar\n  baz").tokenize()
        assert tokens[0].line == 1
        assert tokens[1].line == 2
        assert tokens[2].line == 3


class TestParser:
    """Test the parser."""

    def test_symbol(self):
        expr = parse("foo")
        assert isinstance(expr, Symbol)
        assert expr.name == "foo"

    def test_number(self):
        assert parse("42") == 42
        assert parse("-17") == -17

    def test_string(self):
        assert parse('"hello"') == "hello"

    def test_boolean(self):
        assert parse("true") is True
        assert parse("false") is False

    def test_keyword(self):
        expr = parse(":locked")
        assert isinstance(expr, Keyword)
        assert expr.name == "locked"

    def test_empty_list(self):
        expr = parse("()")
        assert isinstance(expr, SList)
        assert len(expr) == 0

    def test_simple_list(self):
        expr = parse("(foo bar baz)")
        assert isinstance(expr, SList)
        assert len(expr) == 3
        assert expr[0] == Symbol("foo")
        assert expr[1] == Symbol("bar")
        assert expr[2] == Symbol("baz")

    def test_nested_list(self):
        expr = parse("(and (foo x) (bar y))")
        assert isinstance(expr, SList)
        assert len(expr) == 3
        assert expr[0] == Symbol("and")
        assert isinstance(expr[1], SList)
        assert isinstance(expr[2], SList)

    def test_mixed_types(self):
        expr = parse('(set-prop! obj :locked false)')
        assert isinstance(expr, SList)
        assert expr[0] == Symbol("set-prop!")
        assert expr[1] == Symbol("obj")
        assert isinstance(expr[2], Keyword)
        assert expr[2].name == "locked"
        assert expr[3] is False


class TestRealWorldExamples:
    """Test expressions from the design doc."""

    def test_predicate_has_flag(self):
        expr = parse("(has-flag OBJ TAKEBIT)")
        assert isinstance(expr, SList)
        assert expr[0] == Symbol("has-flag")
        assert expr[1] == Symbol("OBJ")
        assert expr[2] == Symbol("TAKEBIT")

    def test_predicate_loc(self):
        expr = parse("(= (loc OBJ) PLAYER)")
        assert isinstance(expr, SList)
        assert expr[0] == Symbol("=")
        assert isinstance(expr[1], SList)
        assert expr[1][0] == Symbol("loc")

    def test_boolean_and(self):
        expr = parse("(and (visible? obj) (not (held? obj)))")
        assert isinstance(expr, SList)
        assert expr[0] == Symbol("and")
        assert len(expr) == 3

    def test_effect_move(self):
        expr = parse("(move! OBJ PLAYER)")
        assert isinstance(expr, SList)
        assert expr[0] == Symbol("move!")

    def test_effect_set_flag(self):
        expr = parse("(set-flag! DOOR OPENBIT)")
        assert isinstance(expr, SList)
        assert expr[0] == Symbol("set-flag!")

    def test_effect_inc(self):
        expr = parse("(inc! SCORE 5)")
        assert isinstance(expr, SList)
        assert expr[0] == Symbol("inc!")
        assert expr[2] == 5

    def test_complex_precondition(self):
        """Test the TAKE precondition from the design doc."""
        source = """
        (and
          (has-flag object TAKEBIT)
          (visible? object)
          (not (held? object)))
        """
        expr = parse(source)
        assert isinstance(expr, SList)
        assert expr[0] == Symbol("and")
        assert len(expr) == 4

    def test_conditional_effect(self):
        expr = parse("(when (= score 100) (set! GAME_WON true))")
        assert isinstance(expr, SList)
        assert expr[0] == Symbol("when")

    def test_quantifier(self):
        expr = parse('(some (fn (?obj) (has-flag ?obj LIGHTBIT)) (inventory PLAYER))')
        assert isinstance(expr, SList)
        assert expr[0] == Symbol("some")


class TestParseAll:
    """Test parsing multiple expressions."""

    def test_multiple_exprs(self):
        source = """
        (define foo 1)
        (define bar 2)
        (+ foo bar)
        """
        exprs = parse_all(source)
        assert len(exprs) == 3

    def test_with_comments(self):
        source = """
        ; first expression
        (foo)
        ; second expression
        (bar)
        """
        exprs = parse_all(source)
        assert len(exprs) == 2


class TestToString:
    """Test converting expressions back to strings."""

    def test_roundtrip_symbol(self):
        original = "foo"
        expr = parse(original)
        assert to_string(expr) == original

    def test_roundtrip_number(self):
        original = "42"
        expr = parse(original)
        assert to_string(expr) == original

    def test_roundtrip_string(self):
        original = '"hello world"'
        expr = parse(original)
        assert to_string(expr) == original

    def test_roundtrip_list(self):
        original = "(foo bar baz)"
        expr = parse(original)
        assert to_string(expr) == original

    def test_roundtrip_nested(self):
        original = "(and (foo x) (bar y))"
        expr = parse(original)
        assert to_string(expr) == original

    def test_roundtrip_complex(self):
        original = '(set-prop! obj :locked false)'
        expr = parse(original)
        assert to_string(expr) == original


class TestErrors:
    """Test error handling."""

    def test_unclosed_list(self):
        with pytest.raises(SExprError) as excinfo:
            parse("(foo bar")
        assert "Unclosed list" in str(excinfo.value)

    def test_unterminated_string(self):
        with pytest.raises(SExprError) as excinfo:
            parse('"hello')
        assert "Unterminated string" in str(excinfo.value)

    def test_unexpected_rparen(self):
        with pytest.raises(SExprError):
            parse(")")

    def test_error_includes_position(self):
        with pytest.raises(SExprError) as excinfo:
            parse("(foo\nbar\n(baz")
        # Should include line info
        assert "line" in str(excinfo.value)


class TestQuasiquoteParsing:
    """Test quasiquote/unquote/unquote-splicing parsing."""

    def test_tokenize_quasiquote(self):
        tokens = Tokenizer("`foo").tokenize()
        assert tokens[0].type == TokenType.QUASIQUOTE
        assert tokens[1].type == TokenType.SYMBOL

    def test_tokenize_unquote(self):
        tokens = Tokenizer(",foo").tokenize()
        assert tokens[0].type == TokenType.UNQUOTE
        assert tokens[1].type == TokenType.SYMBOL

    def test_tokenize_unquote_splicing(self):
        tokens = Tokenizer(",@foo").tokenize()
        assert tokens[0].type == TokenType.UNQUOTE_SPLICING
        assert tokens[1].type == TokenType.SYMBOL

    def test_parse_quasiquote(self):
        expr = parse("`(a b c)")
        assert isinstance(expr, SList)
        assert len(expr) == 2
        assert isinstance(expr[0], Symbol)
        assert expr[0].name == "quasiquote"

    def test_parse_unquote(self):
        expr = parse("`(a ,b c)")
        # quasiquote form
        assert expr[0].name == "quasiquote"
        inner = expr[1]  # (a ,b c)
        # Second element should be (unquote b)
        unquoted = inner[1]
        assert isinstance(unquoted, SList)
        assert unquoted[0].name == "unquote"
        assert unquoted[1].name == "b"

    def test_parse_unquote_splicing(self):
        expr = parse("`(a ,@b c)")
        inner = expr[1]  # (a ,@b c)
        spliced = inner[1]
        assert isinstance(spliced, SList)
        assert spliced[0].name == "unquote-splicing"
        assert spliced[1].name == "b"

    def test_roundtrip_quasiquote(self):
        original = "`(a b c)"
        expr = parse(original)
        assert to_string(expr) == original

    def test_roundtrip_unquote(self):
        original = "`(a ,b c)"
        expr = parse(original)
        assert to_string(expr) == original

    def test_roundtrip_unquote_splicing(self):
        original = "`(a ,@b c)"
        expr = parse(original)
        assert to_string(expr) == original

    def test_roundtrip_complex_quasiquote(self):
        original = "`((set foo ,(+ 1 2)) ,@effects (success))"
        expr = parse(original)
        assert to_string(expr) == original
