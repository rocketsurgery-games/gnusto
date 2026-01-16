"""
Grue test framework package.

This package provides two testing approaches:

1. Grue-native tests (.test.grue files):
   - DSL-based tests written in S-expressions
   - Run with: grue-test games/lurkinghorror/
   - See dsl.py for test form documentation

2. Python/pytest tests:
   - GrueTestCase and GrueTestHarness for Python unit tests
   - See harness.py for usage examples

Usage:
    # Run grue-native tests
    grue-test games/lurkinghorror/
    python -m grue.test games/lurkinghorror/

    # Use in Python tests
    from grue.test import GrueTestCase, run_tests
"""

from .dsl import (
    TestRunner,
    TestResult,
    TestSuiteResult,
    run_tests,
    run_tests_from_string,
)

from .harness import (
    GrueTestHarness,
    GrueTestCase,
    StateSnapshot,
    ActionTrace,
    pytest_harness,
)

from .cli import main

__all__ = [
    # DSL-based testing
    "TestRunner",
    "TestResult",
    "TestSuiteResult",
    "run_tests",
    "run_tests_from_string",
    # Python/pytest testing
    "GrueTestHarness",
    "GrueTestCase",
    "StateSnapshot",
    "ActionTrace",
    "pytest_harness",
    # CLI
    "main",
]
