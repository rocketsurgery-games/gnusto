"""
ZIL Tokenizer

Converts ZIL source code into a stream of tokens.

ZIL syntax elements:
- < > : Form delimiters (function calls)
- ( ) : List delimiters (data/property lists)
- "..." : String literals
- ; : Comment marker (can comment out entire following expression)
- \ : Escape / section separator
- Atoms: Sequences of non-delimiter characters
- Numbers: Integer literals

Special atom prefixes:
- , : Global variable reference (e.g., ,HERE)
- . : Local variable reference (e.g., .X)
- % : Macro expansion
- ! : Segment (splice)
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator


class TokenType(Enum):
    """Types of tokens in ZIL."""

    FORM_OPEN = auto()  # <
    FORM_CLOSE = auto()  # >
    LIST_OPEN = auto()  # (
    LIST_CLOSE = auto()  # )
    STRING = auto()  # "..."
    NUMBER = auto()  # integer
    ATOM = auto()  # symbol/identifier
    COMMENT = auto()  # ; (comments out next expr)
    EOF = auto()  # end of file


@dataclass
class Token:
    """A single token from ZIL source."""

    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self) -> str:
        if self.type == TokenType.STRING:
            return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"
        return f"Token({self.type.name}, {self.value}, {self.line}:{self.column})"


class ZILTokenizer:
    """
    Tokenizer for ZIL source code.

    Usage:
        tokenizer = ZILTokenizer(source_code)
        for token in tokenizer:
            print(token)
    """

    # Characters that delimit tokens
    DELIMITERS = set("<>()\" \t\n\r;\\")

    def __init__(self, source: str, filename: str = "<string>"):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.column = 1
        self.length = len(source)

    def __iter__(self) -> Iterator[Token]:
        """Iterate over all tokens in the source."""
        while True:
            token = self.next_token()
            yield token
            if token.type == TokenType.EOF:
                break

    def peek(self, offset: int = 0) -> str:
        """Look at a character without consuming it."""
        pos = self.pos + offset
        if pos < self.length:
            return self.source[pos]
        return ""

    def advance(self) -> str:
        """Consume and return the current character."""
        if self.pos >= self.length:
            return ""
        char = self.source[self.pos]
        self.pos += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def skip_whitespace(self) -> None:
        """Skip whitespace only (not comments)."""
        while self.pos < self.length:
            char = self.peek()
            if char in " \t\n\r":
                self.advance()
                continue
            break

    def next_token(self) -> Token:
        """Return the next token from the source."""
        self.skip_whitespace()

        if self.pos >= self.length:
            return Token(TokenType.EOF, "", self.line, self.column)

        start_line = self.line
        start_column = self.column
        char = self.peek()

        # Backslash - escape or section separator
        # In ZIL, \ at start of line with optional control char is section break
        # \. \, \" etc are escaped characters in atoms
        if char == "\\":
            next_char = self.peek(1)
            # Section separators like \ or \^L - skip to end of line
            if next_char in "\n\r" or next_char == "^" or next_char == "":
                while self.pos < self.length and self.peek() != "\n":
                    self.advance()
                if self.pos < self.length:
                    self.advance()  # skip newline
                return self.next_token()
            # Otherwise it's an escaped character in an atom - fall through

        # Comment handling
        if char == ";":
            next_char = self.peek(1)

            # ;"..." is a comment string - skip it entirely
            if next_char == '"':
                self.advance()  # skip ;
                self.advance()  # skip "
                self._skip_string_contents()
                return self.next_token()

            # ;<form> or ;(list) - return COMMENT token so parser can skip expr
            if next_char in "<(":
                self.advance()  # skip ;
                return Token(TokenType.COMMENT, ";", start_line, start_column)

            # ;ATOM - comment out a single atom (skip to next delimiter)
            if next_char and next_char not in " \t\n\r":
                self.advance()  # skip ;
                # Skip the atom
                while self.pos < self.length:
                    c = self.peek()
                    if c in self.DELIMITERS:
                        break
                    self.advance()
                return self.next_token()

            # ; followed by whitespace - line comment, skip to end of line
            while self.pos < self.length and self.peek() != "\n":
                self.advance()
            return self.next_token()

        # Single-character tokens
        if char == "<":
            self.advance()
            return Token(TokenType.FORM_OPEN, "<", start_line, start_column)

        if char == ">":
            self.advance()
            return Token(TokenType.FORM_CLOSE, ">", start_line, start_column)

        if char == "(":
            self.advance()
            return Token(TokenType.LIST_OPEN, "(", start_line, start_column)

        if char == ")":
            self.advance()
            return Token(TokenType.LIST_CLOSE, ")", start_line, start_column)

        # String literal
        if char == '"':
            return self._read_string(start_line, start_column)

        # Atom or number
        return self._read_atom_or_number(start_line, start_column)

    def _skip_string_contents(self) -> None:
        """Skip until closing quote, handling escapes."""
        while self.pos < self.length:
            char = self.advance()
            if char == '"':
                return
            if char == "\\" and self.pos < self.length:
                self.advance()  # skip escaped character

    def _read_string(self, start_line: int, start_column: int) -> Token:
        """Read a string literal."""
        self.advance()  # skip opening quote
        chars = []

        while self.pos < self.length:
            char = self.peek()
            if char == '"':
                self.advance()  # skip closing quote
                return Token(TokenType.STRING, "".join(chars), start_line, start_column)
            if char == "\\":
                self.advance()
                if self.pos < self.length:
                    escaped = self.advance()
                    # Handle common escape sequences
                    if escaped == "n":
                        chars.append("\n")
                    elif escaped == "t":
                        chars.append("\t")
                    elif escaped == "\\":
                        chars.append("\\")
                    elif escaped == '"':
                        chars.append('"')
                    elif escaped == "\n":
                        # Line continuation - skip the newline
                        pass
                    else:
                        # Keep unknown escapes as-is
                        chars.append("\\")
                        chars.append(escaped)
            else:
                chars.append(self.advance())

        # Unterminated string
        raise SyntaxError(
            f"Unterminated string starting at {self.filename}:{start_line}:{start_column}"
        )

    def _read_atom_or_number(self, start_line: int, start_column: int) -> Token:
        """Read an atom or number."""
        chars = []

        while self.pos < self.length:
            char = self.peek()
            if char in self.DELIMITERS:
                # Handle escaped delimiters in atoms (e.g., \. \,)
                if char == "\\" and self.pos + 1 < self.length:
                    next_char = self.peek(1)
                    if next_char not in "\n\r^":
                        self.advance()  # skip backslash
                        chars.append(self.advance())  # add escaped char
                        continue
                break
            chars.append(self.advance())

        value = "".join(chars)

        if not value:
            # Empty atom - shouldn't happen, but handle it
            return self.next_token()

        # Try to parse as number
        try:
            int(value)
            return Token(TokenType.NUMBER, value, start_line, start_column)
        except ValueError:
            pass

        return Token(TokenType.ATOM, value, start_line, start_column)


def tokenize(source: str, filename: str = "<string>") -> list[Token]:
    """
    Tokenize ZIL source code.

    Args:
        source: ZIL source code string
        filename: Optional filename for error messages

    Returns:
        List of tokens (excluding EOF)
    """
    tokenizer = ZILTokenizer(source, filename)
    tokens = []
    for token in tokenizer:
        if token.type == TokenType.EOF:
            break
        tokens.append(token)
    return tokens
