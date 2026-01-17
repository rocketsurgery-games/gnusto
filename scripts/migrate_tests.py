#!/usr/bin/env python3
"""Migrate Grue tests from :action/:expect style to sequential style.

Transforms:
    (test "name"
      :setup ((effects))
      :action (do ...)
      :expect ((pred1) (pred2)))

To:
    (test "name"
      :setup ((effects))
      (do ...)
      (assert (pred1))
      (assert (pred2)))

Also handles test-group forms.
"""

import sys
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grue.sexpr import parse_all, to_string, SList, Symbol, Keyword


def pretty_print_test(test: SList, indent: int = 0) -> str:
    """Pretty-print a test form with proper indentation."""
    ind = "  " * indent

    if len(test) < 2:
        return f"{ind}{to_string(test)}"

    head = test[0]
    if not isinstance(head, Symbol) or head.name != "test":
        return f"{ind}{to_string(test)}"

    name = test[1]
    lines = [f'{ind}(test "{name}"' if isinstance(name, str) else f"{ind}(test {to_string(name)}"]

    # Collect setup and body forms
    setup = None
    body_forms = []

    i = 2
    items = list(test.items)
    while i < len(items):
        item = items[i]
        if isinstance(item, Keyword) and item.name == "setup" and i + 1 < len(items):
            setup = items[i + 1]
            i += 2
        elif isinstance(item, SList):
            body_forms.append(item)
            i += 1
        else:
            i += 1

    # Add setup if present
    if setup is not None:
        lines.append(f"{ind}  :setup {to_string(setup)}")

    # Add body forms
    for form in body_forms:
        lines.append(f"{ind}  {to_string(form)}")

    lines[-1] += ")"
    return "\n".join(lines)


def pretty_print_test_group(group: SList) -> str:
    """Pretty-print a test-group form."""
    if len(group) < 2:
        return to_string(group)

    head = group[0]
    if not isinstance(head, Symbol) or head.name != "test-group":
        return to_string(group)

    name = group[1]
    lines = [f'(test-group "{name}"' if isinstance(name, str) else f"(test-group {to_string(name)}"]

    # Collect setup and nested tests
    setup = None
    tests = []

    i = 2
    items = list(group.items)
    while i < len(items):
        item = items[i]
        if isinstance(item, Keyword) and item.name == "setup" and i + 1 < len(items):
            setup = items[i + 1]
            i += 2
        elif isinstance(item, SList) and len(item) > 0:
            first = item[0]
            if isinstance(first, Symbol) and first.name == "test":
                tests.append(item)
            else:
                tests.append(item)
            i += 1
        else:
            i += 1

    # Add setup if present
    if setup is not None:
        lines.append(f"  :setup {to_string(setup)}")

    # Add tests
    for test in tests:
        if isinstance(test, SList) and len(test) > 0:
            first = test[0]
            if isinstance(first, Symbol) and first.name == "test":
                lines.append("")  # Blank line between tests
                lines.append(pretty_print_test(test, indent=1))
            else:
                lines.append(f"  {to_string(test)}")

    lines.append(")")
    return "\n".join(lines)


def migrate_test_form(test: SList) -> SList:
    """Migrate a single (test ...) form to sequential style."""
    if len(test) < 2:
        return test

    head = test[0]
    if not isinstance(head, Symbol) or head.name != "test":
        return test

    # Parse the test form
    name = test[1]
    setup_effects = None
    action = None
    expect_predicates = []
    other_forms = []

    i = 2
    items = list(test.items)

    while i < len(items):
        item = items[i]

        if isinstance(item, Keyword):
            if item.name == "setup" and i + 1 < len(items):
                setup_effects = items[i + 1]
                i += 2
            elif item.name == "action" and i + 1 < len(items):
                action = items[i + 1]
                i += 2
            elif item.name == "expect" and i + 1 < len(items):
                expect_list = items[i + 1]
                if isinstance(expect_list, SList):
                    expect_predicates = list(expect_list.items)
                i += 2
            else:
                i += 1
        elif isinstance(item, SList):
            # Already a sequential form (do, assert, etc.)
            other_forms.append(item)
            i += 1
        else:
            i += 1

    # If no :action keyword, this is already sequential style
    if action is None:
        return test

    # Build new test form
    new_items = [Symbol("test"), name]

    if setup_effects is not None:
        new_items.append(Keyword("setup"))
        new_items.append(setup_effects)

    # Add the action as a bare form
    new_items.append(action)

    # Add any existing sequential forms
    for form in other_forms:
        new_items.append(form)

    # Convert expect predicates to assert forms
    for pred in expect_predicates:
        assert_form = SList([Symbol("assert"), pred])
        new_items.append(assert_form)

    return SList(new_items)


def migrate_test_sequence(seq: SList) -> SList:
    """Migrate a (test-sequence ...) form to (test ...) form.

    test-sequence with (step :action A :expect E) becomes
    test with (A) (assert E1) (assert E2)
    """
    if len(seq) < 2:
        return seq

    head = seq[0]
    if not isinstance(head, Symbol) or head.name != "test-sequence":
        return seq

    name = seq[1]
    new_items: list = [Symbol("test"), name]

    # Collect setup from first step (if any) as the test setup
    initial_setup = None

    i = 2
    items = list(seq.items)

    while i < len(items):
        item = items[i]

        if isinstance(item, SList) and len(item) > 0:
            first = item[0]
            if isinstance(first, Symbol) and first.name == "step":
                # Parse step: (step :setup S :action A :expect E)
                step_setup = None
                step_action = None
                step_expects = []

                j = 1
                step_items = list(item.items)
                while j < len(step_items):
                    si = step_items[j]
                    if isinstance(si, Keyword) and j + 1 < len(step_items):
                        val = step_items[j + 1]
                        if si.name == "setup":
                            step_setup = val
                        elif si.name == "action":
                            step_action = val
                        elif si.name == "expect":
                            if isinstance(val, SList):
                                step_expects = list(val.items)
                        j += 2
                    else:
                        j += 1

                # First step's setup becomes the test setup
                if initial_setup is None and step_setup is not None:
                    initial_setup = step_setup

                # Add action
                if step_action is not None:
                    new_items.append(step_action)

                # Add expects as asserts
                for pred in step_expects:
                    new_items.append(SList([Symbol("assert"), pred]))

        i += 1

    # Insert setup after name if present
    if initial_setup is not None:
        # Insert at position 2 (after test and name)
        new_items.insert(2, Keyword("setup"))
        new_items.insert(3, initial_setup)

    return SList(new_items)


def migrate_test_group(group: SList) -> SList:
    """Migrate a (test-group ...) form."""
    if len(group) < 2:
        return group

    head = group[0]
    if not isinstance(head, Symbol) or head.name != "test-group":
        return group

    new_items = [head, group[1]]  # test-group and name

    i = 2
    items = list(group.items)

    while i < len(items):
        item = items[i]

        if isinstance(item, Keyword):
            # Pass through group-level keywords like :setup
            if i + 1 < len(items):
                new_items.append(item)
                new_items.append(items[i + 1])
                i += 2
            else:
                new_items.append(item)
                i += 1
        elif isinstance(item, SList) and len(item) > 0:
            first = item[0]
            if isinstance(first, Symbol) and first.name == "test":
                # Migrate nested test
                new_items.append(migrate_test_form(item))
            else:
                new_items.append(item)
            i += 1
        else:
            new_items.append(item)
            i += 1

    return SList(new_items)


def migrate_file(path: Path) -> tuple[str, int]:
    """Migrate a test file and return (content, count of migrated tests)."""
    content = path.read_text()

    # Extract leading comments
    leading_comments = []
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped.startswith(';') or stripped == '':
            leading_comments.append(line)
        else:
            break

    forms = parse_all(content)

    migrated_count = 0
    result_parts = []

    # Add leading comments
    if leading_comments:
        result_parts.append('\n'.join(leading_comments))

    for form in forms:
        if not isinstance(form, SList) or len(form) == 0:
            result_parts.append(to_string(form))
            continue

        head = form[0]
        if isinstance(head, Symbol):
            if head.name == "test":
                # Check if it needs migration
                has_action = any(
                    isinstance(item, Keyword) and item.name == "action"
                    for item in form.items
                )
                if has_action:
                    migrated_count += 1
                new_form = migrate_test_form(form)
                result_parts.append(pretty_print_test(new_form))
            elif head.name == "test-group":
                # Count tests within group that need migration
                for item in form.items:
                    if isinstance(item, SList) and len(item) > 0:
                        h = item[0]
                        if isinstance(h, Symbol) and h.name == "test":
                            for sub in item.items:
                                if isinstance(sub, Keyword) and sub.name == "action":
                                    migrated_count += 1
                                    break
                new_form = migrate_test_group(form)
                result_parts.append(pretty_print_test_group(new_form))
            elif head.name == "test-sequence":
                # Migrate test-sequence to test
                migrated_count += 1
                new_form = migrate_test_sequence(form)
                result_parts.append(pretty_print_test(new_form))
            elif head.name in ("def", "defn"):
                # Preserve definitions
                result_parts.append(to_string(form))
            else:
                result_parts.append(to_string(form))
        else:
            result_parts.append(to_string(form))

    result = '\n\n'.join(result_parts) + '\n'
    return result, migrated_count


def main():
    if len(sys.argv) < 2:
        print("Usage: migrate_tests.py <file.test.grue> [...]")
        print("       migrate_tests.py --all  # migrate all test files")
        sys.exit(1)

    if sys.argv[1] == "--all":
        test_files = list(Path("games/lurkinghorror").glob("*.test.grue"))
    else:
        test_files = [Path(p) for p in sys.argv[1:]]

    total_migrated = 0
    for path in test_files:
        try:
            new_content, count = migrate_file(path)
            if count > 0:
                path.write_text(new_content)
                print(f"Migrated {count} tests in {path}")
                total_migrated += count
            else:
                print(f"No changes needed: {path}")
        except Exception as e:
            print(f"Error migrating {path}: {e}")

    print(f"\nTotal migrated: {total_migrated} tests")


if __name__ == "__main__":
    main()
