"""
GRUE World Parser - Parse .grue files into WorldDefinition structures.

This parser reads GRUE S-expression world files and converts them into
the dataclasses used by the runtime.

The parser is a thin orchestration layer that:
1. Tokenizes/parses S-expressions via sexpr.py
2. Dispatches top-level forms to handlers via forms.py

Grammar for top-level forms:
    (world :name "..." :description "...")
    (room NAME :description "..." :flags (...) :exits (...))
    (object NAME :description "..." :location LOC :flags (...) :behaviors (...))
    (victory :when EXPR :context (...))
    (defeat NAME :when EXPR :context (...))
"""

from pathlib import Path

from .sexpr import parse_all
from .forms import (
    FormDispatcher,
    FormParseError,
    GrueWorld,
    # Re-export dataclasses for backward compatibility
    GrueExit,
    GrueCase,
    GrueBehavior,
    GrueRoom,
    GrueObject,
    GrueVictory,
    GrueDefeat,
)

# Re-export error for backward compatibility
GrueParseError = FormParseError

# Re-export all dataclasses
__all__ = [
    "GrueParseError",
    "GrueExit",
    "GrueCase",
    "GrueBehavior",
    "GrueRoom",
    "GrueObject",
    "GrueVictory",
    "GrueDefeat",
    "GrueWorld",
    "GrueParser",
    "load_grue",
    "parse_grue",
]


class GrueParser:
    """Parse GRUE S-expression world files."""

    def __init__(self, strict: bool = True):
        """Initialize parser.

        Args:
            strict: If True, raise on unknown forms. If False, skip them.
        """
        self.dispatcher = FormDispatcher(strict=strict)

    def parse(self, source: str) -> GrueWorld:
        """Parse GRUE source into a GrueWorld."""
        exprs = parse_all(source)
        world = GrueWorld()
        self.dispatcher.dispatch_all(exprs, world)
        return world

    def parse_file(self, path: str | Path) -> GrueWorld:
        """Parse a .grue file."""
        with open(path, "r") as f:
            return self.parse(f.read())


def _load_defaults() -> GrueWorld:
    """Load the built-in builtins.grue file."""
    defaults_path = Path(__file__).parent / "builtins.grue"
    if defaults_path.exists():
        parser = GrueParser()
        return parser.parse_file(defaults_path)
    return GrueWorld()


def _merge_defaults(world: GrueWorld, defaults: GrueWorld) -> None:
    """Merge default behaviors into a world (in place).

    Only adds defaults for verbs not already defined in world.defaults.
    """
    for verb, behavior in defaults.defaults.items():
        if verb not in world.defaults:
            world.defaults[verb] = behavior


def load_grue(path: str | Path, include_defaults: bool = True) -> GrueWorld:
    """Load a GRUE world definition from a file or directory.

    If path is a file, parse it as a single GRUE source.
    If path is a directory, load and combine all .grue files (excluding reference/).

    Args:
        path: File or directory to load
        include_defaults: If True, merge built-in builtins.grue (default: True)
    """
    path = Path(path)

    if path.is_file():
        parser = GrueParser()
        world = parser.parse_file(path)
    elif path.is_dir():
        # Load main files in order, skip reference/ directory
        main_files = ["world.grue", "rooms.grue", "objects.grue", "barriers.grue"]
        combined_source = []

        for filename in main_files:
            file_path = path / filename
            if file_path.exists():
                combined_source.append(file_path.read_text())

        # Also load any other .grue files in the root (for custom additions)
        # Skip test files (*.test.grue)
        for file_path in sorted(path.glob("*.grue")):
            if file_path.name not in main_files and not file_path.name.endswith(".test.grue"):
                combined_source.append(file_path.read_text())

        world = parse_grue("\n".join(combined_source))
    else:
        raise FileNotFoundError(f"Path not found: {path}")

    if include_defaults:
        _merge_defaults(world, _load_defaults())

    return world


def parse_grue(source: str) -> GrueWorld:
    """Parse GRUE source text into a GrueWorld."""
    parser = GrueParser()
    return parser.parse(source)
