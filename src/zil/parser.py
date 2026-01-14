"""
ZIL Parser

Converts a stream of tokens into an Abstract Syntax Tree.

ZIL has two main compound structures:
- Forms: <OPERATOR args...> - function calls, definitions
- Lists: (items...) - property lists, data

The parser handles nested structures recursively.
"""

from typing import Union

from .ast import Atom, Number, String, Form, List, ASTNode
from .tokenizer import Token, TokenType, ZILTokenizer


class ParseError(Exception):
    """Error during parsing."""

    def __init__(self, message: str, token: Token | None = None):
        self.token = token
        if token:
            super().__init__(f"{message} at line {token.line}, column {token.column}")
        else:
            super().__init__(message)


class ZILParser:
    """
    Parser for ZIL source code.

    Usage:
        parser = ZILParser(source_code)
        ast = parser.parse()  # Returns list of top-level forms
    """

    def __init__(self, source: str, filename: str = "<string>"):
        self.tokenizer = ZILTokenizer(source, filename)
        self.filename = filename
        self.current_token: Token | None = None
        self._advance()

    def _advance(self) -> Token | None:
        """Move to the next token."""
        self.current_token = next(iter(self.tokenizer), None)
        return self.current_token

    def _expect(self, token_type: TokenType) -> Token:
        """Expect a specific token type, raise error if not found."""
        if self.current_token is None:
            raise ParseError(f"Expected {token_type.name}, got end of file")
        if self.current_token.type != token_type:
            raise ParseError(
                f"Expected {token_type.name}, got {self.current_token.type.name}",
                self.current_token,
            )
        token = self.current_token
        self._advance()
        return token

    def parse(self) -> list[ASTNode]:
        """
        Parse the entire source and return a list of top-level forms.

        In ZIL, a source file consists of a sequence of forms and
        sometimes standalone strings (used as section comments).
        """
        results: list[ASTNode] = []

        while self.current_token and self.current_token.type != TokenType.EOF:
            node = self._parse_expr()
            if node is not None:
                results.append(node)

        return results

    def _parse_expr(self) -> ASTNode | None:
        """Parse a single expression."""
        if self.current_token is None:
            return None

        token = self.current_token
        token_type = token.type

        # Handle comment token - skip the following expression
        if token_type == TokenType.COMMENT:
            self._advance()  # skip the ; token
            # Now skip the following expression (form or list)
            self._skip_commented_expr()
            # Continue to get the next real expression
            return self._parse_expr()

        if token_type == TokenType.FORM_OPEN:
            return self._parse_form()

        if token_type == TokenType.LIST_OPEN:
            return self._parse_list()

        if token_type == TokenType.STRING:
            self._advance()
            return String(value=token.value, line=token.line, column=token.column)

        if token_type == TokenType.NUMBER:
            self._advance()
            return Number(value=int(token.value), line=token.line, column=token.column)

        if token_type == TokenType.ATOM:
            self._advance()
            return Atom(name=token.value, line=token.line, column=token.column)

        if token_type in (TokenType.FORM_CLOSE, TokenType.LIST_CLOSE):
            # This is not an error - it signals end of list/form to caller
            return None

        if token_type == TokenType.EOF:
            return None

        raise ParseError(f"Unexpected token type: {token_type}", token)

    def _skip_commented_expr(self) -> None:
        """Skip a commented-out expression (form or list)."""
        if self.current_token is None:
            return

        token_type = self.current_token.type

        if token_type == TokenType.FORM_OPEN:
            self._skip_form()
        elif token_type == TokenType.LIST_OPEN:
            self._skip_list()
        # For atoms, strings, numbers - just skip one token
        elif token_type in (TokenType.ATOM, TokenType.STRING, TokenType.NUMBER):
            self._advance()
        # Nested comment - skip ; and then the expression after it
        elif token_type == TokenType.COMMENT:
            self._advance()
            self._skip_commented_expr()

    def _skip_form(self) -> None:
        """Skip a form including all nested content."""
        if self.current_token and self.current_token.type == TokenType.FORM_OPEN:
            self._advance()  # skip <
            depth = 1
            while self.current_token and depth > 0:
                if self.current_token.type == TokenType.FORM_OPEN:
                    depth += 1
                elif self.current_token.type == TokenType.FORM_CLOSE:
                    depth -= 1
                elif self.current_token.type == TokenType.LIST_OPEN:
                    self._skip_list()
                    continue
                self._advance()

    def _skip_list(self) -> None:
        """Skip a list including all nested content."""
        if self.current_token and self.current_token.type == TokenType.LIST_OPEN:
            self._advance()  # skip (
            depth = 1
            while self.current_token and depth > 0:
                if self.current_token.type == TokenType.LIST_OPEN:
                    depth += 1
                elif self.current_token.type == TokenType.LIST_CLOSE:
                    depth -= 1
                elif self.current_token.type == TokenType.FORM_OPEN:
                    self._skip_form()
                    continue
                self._advance()

    def _parse_form(self) -> Form:
        """Parse a form: <elements...>"""
        open_token = self.current_token
        assert open_token is not None
        self._expect(TokenType.FORM_OPEN)

        elements: list[ASTNode] = []

        while self.current_token and self.current_token.type != TokenType.FORM_CLOSE:
            if self.current_token.type == TokenType.EOF:
                raise ParseError("Unterminated form", open_token)
            expr = self._parse_expr()
            if expr is not None:
                elements.append(expr)

        self._expect(TokenType.FORM_CLOSE)
        return Form(elements=elements, line=open_token.line, column=open_token.column)

    def _parse_list(self) -> List:
        """Parse a list: (elements...)"""
        open_token = self.current_token
        assert open_token is not None
        self._expect(TokenType.LIST_OPEN)

        elements: list[ASTNode] = []

        while self.current_token and self.current_token.type != TokenType.LIST_CLOSE:
            if self.current_token.type == TokenType.EOF:
                raise ParseError("Unterminated list", open_token)
            expr = self._parse_expr()
            if expr is not None:
                elements.append(expr)

        self._expect(TokenType.LIST_CLOSE)
        return List(elements=elements, line=open_token.line, column=open_token.column)


def parse(source: str, filename: str = "<string>") -> list[ASTNode]:
    """
    Parse ZIL source code into an AST.

    Args:
        source: ZIL source code string
        filename: Optional filename for error messages

    Returns:
        List of top-level AST nodes (forms and strings)
    """
    parser = ZILParser(source, filename)
    return parser.parse()
