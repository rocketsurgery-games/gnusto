"""
S-expression parser.

Grammar (EBNF):
    sexpr      ::= atom | string | number | list
    list       ::= '(' sexpr* ')'
    atom       ::= symbol | keyword
    symbol     ::= [@a-zA-Z_][@a-zA-Z0-9_!?-]*
    keyword    ::= ':' symbol
    string     ::= '"' char* '"'
    number     ::= '-'? [0-9]+
    comment    ::= ';' [^\\n]* '\\n'

String semantics (ZIL-style for IF prose):
    - Newlines and surrounding whitespace collapse to single space
    - Use \\n for actual newlines in output
    - Use \\t for tabs, \\\\ for backslash, \\" for quote

Examples:
    (has-flag obj TAKEBIT)
    (and (visible? obj) (not (held? obj)))
    (move obj PLAYER)
    (set obj :locked false)
"""

from dataclasses import dataclass
from typing import Union
from enum import Enum, auto


class TokenType(Enum):
    LPAREN = auto()
    RPAREN = auto()
    QUOTE = auto()  # '
    QUASIQUOTE = auto()  # `
    UNQUOTE = auto()  # ,
    UNQUOTE_SPLICING = auto()  # ,@
    SYMBOL = auto()
    KEYWORD = auto()  # :keyword
    STRING = auto()
    NUMBER = auto()
    BOOL_TRUE = auto()
    BOOL_FALSE = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: str | int | bool
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r})"


class SExprError(Exception):
    """Error during S-expression parsing."""

    def __init__(self, message: str, line: int = 0, col: int = 0):
        self.line = line
        self.col = col
        super().__init__(f"{message} at line {line}, col {col}")


# AST Node types
@dataclass
class Symbol:
    """An identifier/symbol like 'has-flag' or 'TAKEBIT'."""
    name: str

    def __repr__(self) -> str:
        return f"Symbol({self.name})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Symbol):
            return self.name == other.name
        return False

    def __hash__(self) -> int:
        return hash(self.name)


@dataclass
class Keyword:
    """A keyword like ':locked' or ':description'."""
    name: str

    def __repr__(self) -> str:
        return f":{self.name}"


@dataclass
class SList:
    """A list/form like (has-flag obj TAKEBIT)."""
    items: list["SExpr"]

    def __repr__(self) -> str:
        items_str = " ".join(repr(item) for item in self.items)
        return f"({items_str})"

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> "SExpr":
        return self.items[index]

    def __iter__(self):
        return iter(self.items)


# Union type for all S-expression values
SExpr = Union[Symbol, Keyword, SList, str, int, bool]


# Known parameter types for type annotations
PARAM_TYPES = {"entity", "string", "number", "symbol"}


def parse_param_list(
    params_expr: SList,
    *,
    require_question_mark: bool = False,
) -> tuple[list[str], dict[str, str]]:
    """Parse a function parameter list with optional type annotations.

    Supports type annotations via keyword after parameter:
        (?x)              -> (["x"], {})
        (?x :number)      -> (["x"], {"x": "number"})
        (?x :entity ?y)   -> (["x", "y"], {"x": "entity"})

    Args:
        params_expr: The parameter list S-expression.
        require_question_mark: If True, all params must start with '?'.

    Returns:
        (param_names, param_types) where param_types maps name -> type
        for explicitly annotated parameters only.
    """
    params: list[str] = []
    param_types: dict[str, str] = {}
    items = list(params_expr.items)
    i = 0
    while i < len(items):
        p = items[i]
        if isinstance(p, Symbol):
            if require_question_mark and not p.name.startswith("?"):
                raise ValueError(f"Expected ?param, got {p.name}")
            name = p.name[1:] if p.name.startswith("?") else p.name
            params.append(name)
            # Check for type annotation keyword
            next_item = items[i + 1] if i + 1 < len(items) else None
            if isinstance(next_item, Keyword):
                type_name = next_item.name
                if type_name not in PARAM_TYPES:
                    raise ValueError(
                        f"Unknown parameter type :{type_name} for ?{name}. "
                        f"Expected one of: {', '.join(sorted(PARAM_TYPES))}"
                    )
                param_types[name] = type_name
                i += 2
            else:
                i += 1
        else:
            raise ValueError(f"Expected parameter symbol, got {p}")
    return params, param_types


class Tokenizer:
    """Tokenize S-expression source text."""

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1

    def peek(self) -> str:
        if self.pos >= len(self.source):
            return ""
        return self.source[self.pos]

    def advance(self) -> str:
        ch = self.peek()
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def skip_whitespace_and_comments(self) -> None:
        while self.pos < len(self.source):
            ch = self.peek()
            if ch.isspace():
                self.advance()
            elif ch == ";":
                # Skip to end of line
                while self.peek() and self.peek() != "\n":
                    self.advance()
            else:
                break

    def read_string(self) -> str:
        """Read a double-quoted string.

        ZIL-style: newlines and surrounding whitespace are collapsed to a single space.
        This allows prose to be formatted nicely in source without affecting output.
        Use explicit \\n for actual newlines.
        """
        self.advance()  # consume opening quote
        result = []
        while self.peek() and self.peek() != '"':
            ch = self.advance()
            if ch == "\\":
                # Handle escape sequences
                next_ch = self.advance()
                if next_ch == "n":
                    result.append("\n")
                elif next_ch == "t":
                    result.append("\t")
                elif next_ch == "\\":
                    result.append("\\")
                elif next_ch == '"':
                    result.append('"')
                else:
                    result.append(next_ch)
            elif ch == "\n":
                # Collapse newline and surrounding whitespace to single space
                # First, trim any trailing whitespace we just added
                while result and result[-1] in " \t":
                    result.pop()
                # Skip any leading whitespace on the next line
                while self.peek() in " \t":
                    self.advance()
                # Add single space (unless at start of string or next char is closing quote)
                if result and self.peek() != '"':
                    result.append(" ")
            else:
                result.append(ch)
        if not self.peek():
            raise SExprError("Unterminated string", self.line, self.col)
        self.advance()  # consume closing quote
        return "".join(result)

    def is_symbol_start(self, ch: str) -> bool:
        """Check if character can start a symbol."""
        return (
            ch.isalpha() or
            ch == "_" or
            ch == "@" or  # Entity prefix
            ch in "=<>!?+-*/" or
            ch == ":"
        )

    def is_symbol_char(self, ch: str) -> bool:
        """Check if character can be part of a symbol."""
        return ch.isalnum() or ch in "_!?-+*/<>=@"

    def read_symbol_or_number(self) -> Token:
        """Read a symbol, keyword, number, or boolean."""
        start_line = self.line
        start_col = self.col
        result = []

        # Check for keyword prefix
        is_keyword = False
        if self.peek() == ":":
            is_keyword = True
            self.advance()

        # Read the identifier/number using symbol character check
        while self.peek() and self.is_symbol_char(self.peek()):
            result.append(self.advance())

        text = "".join(result)

        if not text:
            raise SExprError(
                f"Expected symbol after ':'",
                start_line, start_col
            )

        # Check for booleans
        if text.lower() == "true":
            return Token(TokenType.BOOL_TRUE, True, start_line, start_col)
        if text.lower() == "false":
            return Token(TokenType.BOOL_FALSE, False, start_line, start_col)

        # Check for numbers
        if not is_keyword:
            try:
                if text.startswith("-") and len(text) > 1:
                    return Token(TokenType.NUMBER, int(text), start_line, start_col)
                elif text[0].isdigit():
                    return Token(TokenType.NUMBER, int(text), start_line, start_col)
            except ValueError:
                pass

        if is_keyword:
            return Token(TokenType.KEYWORD, text, start_line, start_col)
        return Token(TokenType.SYMBOL, text, start_line, start_col)

    def next_token(self) -> Token:
        self.skip_whitespace_and_comments()

        if self.pos >= len(self.source):
            return Token(TokenType.EOF, "", self.line, self.col)

        start_line = self.line
        start_col = self.col
        ch = self.peek()

        if ch == "(":
            self.advance()
            return Token(TokenType.LPAREN, "(", start_line, start_col)
        elif ch == ")":
            self.advance()
            return Token(TokenType.RPAREN, ")", start_line, start_col)
        elif ch == "'":
            self.advance()
            return Token(TokenType.QUOTE, "'", start_line, start_col)
        elif ch == "`":
            self.advance()
            return Token(TokenType.QUASIQUOTE, "`", start_line, start_col)
        elif ch == ",":
            self.advance()
            # Check for ,@ (unquote-splicing)
            if self.peek() == "@":
                self.advance()
                return Token(TokenType.UNQUOTE_SPLICING, ",@", start_line, start_col)
            return Token(TokenType.UNQUOTE, ",", start_line, start_col)
        elif ch == '"':
            s = self.read_string()
            return Token(TokenType.STRING, s, start_line, start_col)
        elif self.is_symbol_start(ch):
            return self.read_symbol_or_number()
        elif ch.isdigit():
            return self.read_symbol_or_number()
        else:
            raise SExprError(f"Unexpected character: {ch!r}", start_line, start_col)

    def tokenize(self) -> list[Token]:
        tokens = []
        while True:
            tok = self.next_token()
            tokens.append(tok)
            if tok.type == TokenType.EOF:
                break
        return tokens


class Parser:
    """Parse tokens into S-expression AST."""

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        if self.pos >= len(self.tokens):
            return self.tokens[-1]  # Return EOF
        return self.tokens[self.pos]

    def advance(self) -> Token:
        tok = self.peek()
        self.pos += 1
        return tok

    def parse_expr(self) -> SExpr:
        tok = self.peek()

        if tok.type == TokenType.QUOTE:
            self.advance()  # consume '
            quoted = self.parse_expr()
            return SList([Symbol("quote"), quoted])
        elif tok.type == TokenType.QUASIQUOTE:
            self.advance()  # consume `
            quoted = self.parse_expr()
            return SList([Symbol("quasiquote"), quoted])
        elif tok.type == TokenType.UNQUOTE:
            self.advance()  # consume ,
            unquoted = self.parse_expr()
            return SList([Symbol("unquote"), unquoted])
        elif tok.type == TokenType.UNQUOTE_SPLICING:
            self.advance()  # consume ,@
            unquoted = self.parse_expr()
            return SList([Symbol("unquote-splicing"), unquoted])
        elif tok.type == TokenType.LPAREN:
            return self.parse_list()
        elif tok.type == TokenType.SYMBOL:
            self.advance()
            return Symbol(tok.value)
        elif tok.type == TokenType.KEYWORD:
            self.advance()
            return Keyword(tok.value)
        elif tok.type == TokenType.STRING:
            self.advance()
            return tok.value
        elif tok.type == TokenType.NUMBER:
            self.advance()
            return tok.value
        elif tok.type in (TokenType.BOOL_TRUE, TokenType.BOOL_FALSE):
            self.advance()
            return tok.value
        elif tok.type == TokenType.EOF:
            raise SExprError("Unexpected end of input", tok.line, tok.col)
        else:
            raise SExprError(
                f"Unexpected token: {tok.type}",
                tok.line, tok.col
            )

    def parse_list(self) -> SList:
        lparen = self.advance()
        if lparen.type != TokenType.LPAREN:
            raise SExprError(
                f"Expected '(', got {lparen.type}",
                lparen.line, lparen.col
            )

        items = []
        while self.peek().type != TokenType.RPAREN:
            if self.peek().type == TokenType.EOF:
                raise SExprError(
                    "Unclosed list - expected ')'",
                    lparen.line, lparen.col
                )
            items.append(self.parse_expr())

        self.advance()  # consume ')'
        return SList(items)

    def parse(self) -> SExpr:
        """Parse a single S-expression."""
        return self.parse_expr()

    def parse_all(self) -> list[SExpr]:
        """Parse all S-expressions in the input."""
        exprs = []
        while self.peek().type != TokenType.EOF:
            exprs.append(self.parse_expr())
        return exprs


def parse(source: str) -> SExpr:
    """Parse a single S-expression from source text."""
    tokenizer = Tokenizer(source)
    tokens = tokenizer.tokenize()
    parser = Parser(tokens)
    return parser.parse()


def parse_all(source: str) -> list[SExpr]:
    """Parse all S-expressions from source text."""
    tokenizer = Tokenizer(source)
    tokens = tokenizer.tokenize()
    parser = Parser(tokens)
    return parser.parse_all()


def to_string(expr: SExpr) -> str:
    """Convert S-expression back to string form."""
    if isinstance(expr, Symbol):
        return expr.name
    elif isinstance(expr, Keyword):
        return f":{expr.name}"
    elif isinstance(expr, SList):
        # Pretty-print quote/quasiquote/unquote forms
        if (len(expr.items) == 2 and isinstance(expr.items[0], Symbol)):
            sym_name = expr.items[0].name
            if sym_name == "quote":
                return f"'{to_string(expr.items[1])}"
            elif sym_name == "quasiquote":
                return f"`{to_string(expr.items[1])}"
            elif sym_name == "unquote":
                return f",{to_string(expr.items[1])}"
            elif sym_name == "unquote-splicing":
                return f",@{to_string(expr.items[1])}"
        items = " ".join(to_string(item) for item in expr.items)
        return f"({items})"
    elif isinstance(expr, str):
        # Escape special characters
        escaped = expr.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    elif isinstance(expr, bool):
        return "true" if expr else "false"
    elif isinstance(expr, int):
        return str(expr)
    elif isinstance(expr, list):
        # Handle Python lists (from quoted expressions)
        items = " ".join(to_string(item) for item in expr)
        return f"({items})"
    else:
        raise ValueError(f"Unknown expression type: {type(expr)}")
