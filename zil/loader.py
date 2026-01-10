"""
ZIL Loader

Utilities for loading ZIL source files, with support for
INSERT-FILE directives and directory-wide parsing.
"""

from pathlib import Path

from .ast import ASTNode, Form, String
from .parser import parse
from .extractor import extract_game_data, GameData


def parse_file(filepath: Path | str) -> list[ASTNode]:
    """Parse a single ZIL file."""
    filepath = Path(filepath)
    source = filepath.read_text(encoding="utf-8", errors="replace")
    return parse(source, str(filepath))


def parse_directory(directory: Path | str) -> list[ASTNode]:
    """
    Parse all .zil files in a directory.

    This is the simple approach - just concatenates all files.
    Use parse_with_includes() for proper include-order parsing.
    """
    directory = Path(directory)
    all_ast: list[ASTNode] = []

    for zil_file in sorted(directory.glob("*.zil")):
        ast = parse_file(zil_file)
        all_ast.extend(ast)

    return all_ast


def parse_with_includes(
    main_file: Path | str,
    search_dirs: list[Path | str] | None = None,
) -> list[ASTNode]:
    """
    Parse a ZIL file and recursively process INSERT-FILE directives.

    Args:
        main_file: The main .zil file to start from
        search_dirs: Additional directories to search for included files.
                    The directory of main_file is always searched.

    Returns:
        Combined AST from all included files in proper order.
    """
    main_file = Path(main_file)
    base_dir = main_file.parent

    # Build search path
    search_path = [base_dir]
    if search_dirs:
        search_path.extend(Path(d) for d in search_dirs)

    # Track which files we've already processed
    processed: set[Path] = set()
    all_ast: list[ASTNode] = []

    def find_file(name: str) -> Path | None:
        """Find a file by name in the search path."""
        # Try with and without .zil extension
        candidates = [name, f"{name}.zil"]
        for search_dir in search_path:
            for candidate in candidates:
                filepath = search_dir / candidate
                if filepath.exists():
                    return filepath.resolve()
        return None

    def process_file(filepath: Path) -> None:
        """Process a file, handling INSERT-FILE directives."""
        filepath = filepath.resolve()
        if filepath in processed:
            return
        processed.add(filepath)

        ast = parse_file(filepath)

        for node in ast:
            # Check for INSERT-FILE directive
            if isinstance(node, Form) and node.operator:
                if node.operator.name == "INSERT-FILE":
                    # Get the filename argument
                    if node.args and isinstance(node.args[0], String):
                        include_name = node.args[0].value
                        include_path = find_file(include_name)
                        if include_path:
                            process_file(include_path)
                        else:
                            # File not found - could warn here
                            pass
                    continue

            # Not an INSERT-FILE, add to output
            all_ast.append(node)

    process_file(main_file)
    return all_ast


def load_game(
    path: Path | str,
    use_includes: bool = True,
) -> GameData:
    """
    Load a complete game from ZIL source.

    Args:
        path: Either a main .zil file or a directory of .zil files
        use_includes: If True and path is a file, follow INSERT-FILE directives.
                     If False or path is a directory, just load all .zil files.

    Returns:
        GameData extracted from the ZIL source.

    Example:
        data = load_game("infocom/lurkinghorror")
        print(f"Loaded {len(data.rooms)} rooms")
    """
    path = Path(path)

    if path.is_file():
        if use_includes:
            ast = parse_with_includes(path)
        else:
            ast = parse_file(path)
    elif path.is_dir():
        # Look for a main file first
        main_candidates = [
            path / f"{path.name}.zil",  # e.g., lurkinghorror/lurkinghorror.zil
            path / "main.zil",
            path / "game.zil",
        ]
        main_file = None
        for candidate in main_candidates:
            if candidate.exists():
                main_file = candidate
                break

        if main_file and use_includes:
            ast = parse_with_includes(main_file)
        else:
            ast = parse_directory(path)
    else:
        raise FileNotFoundError(f"Path not found: {path}")

    return extract_game_data(ast)
