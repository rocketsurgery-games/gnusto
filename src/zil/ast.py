"""
Abstract Syntax Tree nodes for ZIL.

ZIL is a Lisp-like language with these main constructs:
- Atoms: symbols like ROOM, OBJECT, FOO
- Numbers: integers like 42, -1
- Strings: "quoted text"
- Forms: <OPERATOR args...> - function calls using angle brackets
- Lists: (items...) - data lists using parentheses
"""

from dataclasses import dataclass, field
from typing import Union


@dataclass
class Node:
    """Base class for all AST nodes."""

    # Source location for error reporting
    line: int = 0
    column: int = 0


@dataclass
class Atom(Node):
    """
    A symbol/identifier in ZIL.

    Examples: ROOM, OBJECT, FOO, P?NORTH, V-TAKE

    Atoms can have prefixes that indicate their type:
    - No prefix: regular symbol
    - , (comma): global variable reference
    - . (period): local variable reference
    - P? : property name
    - V- : verb routine
    """

    name: str = ""

    def __repr__(self) -> str:
        return f"Atom({self.name!r})"


@dataclass
class Number(Node):
    """An integer literal."""

    value: int = 0

    def __repr__(self) -> str:
        return f"Number({self.value})"


@dataclass
class String(Node):
    """A string literal (double-quoted)."""

    value: str = ""

    def __repr__(self) -> str:
        return f"String({self.value!r})"


@dataclass
class Form(Node):
    """
    A function call form using angle brackets: <OPERATOR args...>

    Examples:
        <TELL "Hello">
        <COND (<VERB? TAKE> <RTRUE>)>
        <ROOM FOO (IN ROOMS) (DESC "A room")>

    The first element is typically the operator/function name.
    """

    elements: list["ASTNode"] = field(default_factory=list)

    @property
    def operator(self) -> Union["Atom", None]:
        """Return the first element as the operator, if it's an atom."""
        if self.elements and isinstance(self.elements[0], Atom):
            return self.elements[0]
        return None

    @property
    def args(self) -> list["ASTNode"]:
        """Return all elements after the operator."""
        return self.elements[1:] if self.elements else []

    def __repr__(self) -> str:
        return f"Form({self.elements!r})"


@dataclass
class List(Node):
    """
    A data list using parentheses: (items...)

    Used for property lists in object definitions:
        (IN ROOMS)
        (DESC "A dark room")
        (FLAGS LIGHTBIT CONTBIT)
        (NORTH TO KITCHEN)
    """

    elements: list["ASTNode"] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"List({self.elements!r})"


# Type alias for any AST node
ASTNode = Union[Atom, Number, String, Form, List]
