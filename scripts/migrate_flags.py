#!/usr/bin/env python3
"""
Migrate :flags syntax to :properties with natural names.

Converts:
- :flags (TAKEBIT OPENBIT) → boolean properties merged into :properties
- (has-flag ?obj OPENBIT) → (:open ?obj)
- (set-flag ?obj OPENBIT) → (set ?obj :open true)
- (clear-flag ?obj OPENBIT) → (set ?obj :open false)
"""

import re
import sys
from pathlib import Path

# Mapping from old BIT names to natural property names
FLAG_MAP = {
    "TAKEBIT": "takeable",
    "OPENBIT": "open",
    "OPENABLE": "openable",
    "CONTBIT": "container",
    "SEARCHBIT": "searchable",
    "SURFACEBIT": "surface",
    "TRANSBIT": "transparent",
    "NDESCBIT": "nodesc",
    "INVISIBLE": "invisible",
    "DOORBIT": "door",
    "LOCKED": "locked",
    "VEHBIT": "vehicle",
    "PERSON": "person",
    "ONBIT": "on",
    "READBIT": "readable",
    "TRYTAKEBIT": "trytake",
    "TOUCHBIT": "touched",
    "WEAPONBIT": "weapon",
    "TOOLBIT": "tool",
    "FOODBIT": "food",
    "OUTSIDE": "outside",
    "WEARBIT": "wearable",
    "LIGHTBIT": "lit",
    "POWERBIT": "powered",
    "POWER": "powered",
    "FURNITURE": "furniture",
    "KEYBIT": "key",
    "ATTACKBIT": "attackable",
    "SLIMEBIT": "slime",
    "RMUNGBIT": "rmung",
    "RLANDBIT": "rland",
    # Article hints - convert to boolean for now, mx5 will handle semantic conversion
    "AN": "an",
    "NOABIT": "noabit",
    "NOTHEBIT": "nothebit",
    "THE": "the",
}


def convert_flag_name(flag: str) -> str:
    """Convert an old flag name to natural property name."""
    return FLAG_MAP.get(flag, flag.lower())


def convert_flags_to_properties(flags_str: str) -> str:
    """Convert ':flags (TAKEBIT OPENBIT)' to property key-value pairs."""
    # Extract flags from parentheses
    match = re.match(r'\(([^)]*)\)', flags_str.strip())
    if not match:
        return ""

    flags = match.group(1).split()
    props = []
    for flag in flags:
        natural_name = convert_flag_name(flag)
        props.append(f":{natural_name} true")

    return " ".join(props)


def migrate_file(content: str) -> str:
    """Migrate all flag-related patterns in file content."""

    # 1. Convert (has-flag ?obj FLAG) and (has-flag? ?obj FLAG) → (:prop ?obj)
    def replace_has_flag(m):
        obj = m.group(1)
        flag = m.group(2)
        prop = convert_flag_name(flag)
        return f"(:{prop} {obj})"

    content = re.sub(
        r'\(has-flag\??\s+(\S+)\s+([A-Z][A-Z0-9]*)\)',
        replace_has_flag,
        content
    )

    # 2. Convert (set-flag ?obj FLAG) and (set-flag! ?obj FLAG) → (set ?obj :prop true)
    def replace_set_flag(m):
        obj = m.group(1)
        flag = m.group(2)
        prop = convert_flag_name(flag)
        return f"(set {obj} :{prop} true)"

    content = re.sub(
        r'\(set-flag!?\s+(\S+)\s+([A-Z][A-Z0-9]*)\)',
        replace_set_flag,
        content
    )

    # 3. Convert (clear-flag ?obj FLAG) and (clear-flag! ?obj FLAG) → (set ?obj :prop false)
    def replace_clear_flag(m):
        obj = m.group(1)
        flag = m.group(2)
        prop = convert_flag_name(flag)
        return f"(set {obj} :{prop} false)"

    content = re.sub(
        r'\(clear-flag!?\s+(\S+)\s+([A-Z][A-Z0-9]*)\)',
        replace_clear_flag,
        content
    )

    # 4. Convert :flags (...) lines
    # This handles the case where :flags appears with or without :properties
    def replace_flags_line(m):
        indent = m.group(1)
        flags_content = m.group(2)
        props = convert_flags_to_properties(f"({flags_content})")
        return f"{indent}:properties ({props})"

    # Match :flags (FLAG1 FLAG2 ...) possibly spanning multiple lines
    content = re.sub(
        r'^(\s*):flags\s+\(([^)]+)\)\s*$',
        replace_flags_line,
        content,
        flags=re.MULTILINE
    )

    # 5. Merge :properties lines when :flags was converted and :properties already exists
    # Look for consecutive :properties lines and merge them
    def merge_properties(content: str) -> str:
        lines = content.split('\n')
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Check if this line has :properties and next line also has :properties
            if ':properties (' in line and i + 1 < len(lines) and ':properties (' in lines[i + 1]:
                # Extract properties from both lines, preserving trailing content
                match1 = re.search(r':properties\s+\(([^)]*)\)', line)
                match2 = re.search(r':properties\s+\(([^)]*)\)(.*)', lines[i + 1])
                if match1 and match2:
                    props1 = match1.group(1).strip()
                    props2 = match2.group(1).strip()
                    trailing = match2.group(2)  # Content after the :properties clause
                    combined = f"{props1} {props2}".strip()
                    # Replace first line's properties with merged, preserve trailing content
                    indent = re.match(r'^(\s*)', line).group(1)
                    result.append(f"{indent}:properties ({combined}){trailing}")
                    i += 2
                    continue
            result.append(line)
            i += 1
        return '\n'.join(result)

    content = merge_properties(content)

    return content


def main():
    if len(sys.argv) < 2:
        print("Usage: migrate_flags.py <file_or_dir> [--dry-run]")
        sys.exit(1)

    path = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv

    if path.is_file():
        files = [path]
    else:
        files = list(path.rglob("*.grue"))

    total_changes = 0
    for file in files:
        content = file.read_text()
        new_content = migrate_file(content)

        if content != new_content:
            total_changes += 1
            if dry_run:
                print(f"Would modify: {file}")
            else:
                file.write_text(new_content)
                print(f"Modified: {file}")

    print(f"\n{'Would modify' if dry_run else 'Modified'}: {total_changes} files")


if __name__ == "__main__":
    main()
