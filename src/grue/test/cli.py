"""
Grue test CLI runner.

Usage:
    grue-test games/examples/outside-door.grue
    grue-test games/**/*.grue
    grue-test --verbose games/examples/
    python -m grue.test games/lurkinghorror/

Options:
    -v, --verbose    Show all test names, not just failures
    -q, --quiet      Only show summary
    --no-color       Disable colored output
"""

import argparse
import sys
from pathlib import Path

from .dsl import run_tests, TestSuiteResult, TestResult


# ANSI color codes
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def colorize(text: str, color: str, use_color: bool = True) -> str:
    if not use_color:
        return text
    return f"{color}{text}{Colors.RESET}"


def _should_load_directory(test_file: Path) -> Path | None:
    """
    Check if a test file's directory should be loaded as a multi-file world.

    Returns the directory path if it contains a main world file (world.grue or <dirname>.grue),
    otherwise returns None.
    """
    directory = test_file.parent
    dirname = directory.name

    # Check for world.grue or <dirname>.grue (e.g., lurkinghorror.grue)
    world_file = directory / "world.grue"
    if world_file.exists():
        return directory

    dirname_world = directory / f"{dirname}.grue"
    if dirname_world.exists():
        return directory

    return None


def find_test_files(paths: list[str]) -> list[tuple[Path, Path]]:
    """
    Find world/test file pairs from paths.

    Returns list of (world_path, test_path) tuples.
    World path may be a directory if the test is part of a multi-file world.
    """
    pairs = []
    seen_dirs = set()  # Track directories we've already processed

    for path_str in paths:
        path = Path(path_str)

        if path.is_file():
            if path.suffix == ".grue":
                if path.name.endswith(".test.grue"):
                    # Test file - check if we should load the directory
                    dir_path = _should_load_directory(path)
                    if dir_path:
                        # Multi-file world - load directory, but only once per directory
                        if dir_path not in seen_dirs:
                            pairs.append((dir_path, path))
                            seen_dirs.add(dir_path)
                        else:
                            # Already have this directory, just add the test file
                            # Find existing pair and note we have multiple tests
                            pairs.append((dir_path, path))
                    else:
                        # Single-file world
                        world_path = path.with_name(path.name.replace(".test.grue", ".grue"))
                        if world_path.exists():
                            pairs.append((world_path, path))
                        else:
                            print(f"Warning: No world file for {path}", file=sys.stderr)
                else:
                    # World file - find corresponding test
                    test_path = path.with_suffix(".test.grue")
                    if test_path.exists():
                        pairs.append((path, test_path))
                    else:
                        print(f"Warning: No test file for {path}", file=sys.stderr)

        elif path.is_dir():
            # Find all .test.grue files
            for test_file in path.glob("**/*.test.grue"):
                dir_path = _should_load_directory(test_file)
                if dir_path:
                    pairs.append((dir_path, test_file))
                else:
                    # Single-file world
                    world_file = test_file.with_name(test_file.name.replace(".test.grue", ".grue"))
                    if world_file.exists():
                        pairs.append((world_file, test_file))

    return pairs


def print_result(result: TestResult, verbose: bool, use_color: bool) -> None:
    """Print a single test result."""
    if result.passed:
        status = colorize("PASS", Colors.GREEN, use_color)
    elif result.error:
        status = colorize("ERROR", Colors.YELLOW, use_color)
    else:
        status = colorize("FAIL", Colors.RED, use_color)

    print(f"  [{status}] {result.name}")

    if result.error:
        print(f"         {colorize('Error:', Colors.YELLOW, use_color)} {result.error}")

    for failure in result.failures:
        print(f"         {colorize('-', Colors.RED, use_color)} {failure}")


def print_suite_result(
    suite: TestSuiteResult,
    verbose: bool,
    quiet: bool,
    use_color: bool
) -> None:
    """Print results for a test suite."""
    world_name = Path(suite.world_path).stem

    if not quiet:
        header = colorize(f"Testing {world_name}", Colors.BOLD + Colors.CYAN, use_color)
        print(f"\n{header}")

    if verbose:
        for result in suite.results:
            print_result(result, verbose, use_color)
    else:
        # Only show failures
        for result in suite.results:
            if not result.passed:
                print_result(result, verbose, use_color)

    # Summary
    if suite.passed == suite.total:
        summary = colorize(f"✓ {suite.passed}/{suite.total} passed", Colors.GREEN, use_color)
    else:
        failed = suite.failed + suite.errored
        summary = colorize(f"✗ {suite.passed}/{suite.total} passed, {failed} failed", Colors.RED, use_color)

    if not quiet or suite.passed != suite.total:
        print(f"  {summary}")


def main(argv: list[str] | None = None) -> int:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        prog="grue-test",
        description="Run Grue-native tests"
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="World files, test files, or directories to test"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show all test names, not just failures"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only show summary"
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )

    args = parser.parse_args(argv)
    use_color = not args.no_color and sys.stdout.isatty()

    # Find test files
    pairs = find_test_files(args.paths)

    if not pairs:
        print("No test files found", file=sys.stderr)
        return 1

    # Run tests
    total_passed = 0
    total_failed = 0
    total_errored = 0

    for world_path, test_path in pairs:
        try:
            result = run_tests(world_path, test_path)
            print_suite_result(result, args.verbose, args.quiet, use_color)
            total_passed += result.passed
            total_failed += result.failed
            total_errored += result.errored
        except Exception as e:
            print(f"\n{colorize('Error', Colors.RED, use_color)} loading {world_path}: {e}", file=sys.stderr)
            total_errored += 1

    # Final summary if multiple suites
    if len(pairs) > 1:
        total = total_passed + total_failed + total_errored
        if total_failed + total_errored == 0:
            summary = colorize(f"\n✓ All {total_passed} tests passed", Colors.GREEN + Colors.BOLD, use_color)
        else:
            summary = colorize(
                f"\n✗ {total_passed}/{total} passed, {total_failed + total_errored} failed",
                Colors.RED + Colors.BOLD,
                use_color
            )
        print(summary)

    return 0 if (total_failed + total_errored) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
