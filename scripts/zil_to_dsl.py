#!/usr/bin/env python3
"""
Convert ZIL source files to DSL YAML format.

Usage:
    python scripts/zil_to_dsl.py infocom/lurkinghorror/*.zil -o output.yaml
    python scripts/zil_to_dsl.py cs.zil syntax.zil --name "My Game" --author "Me"
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from zil.parser import parse
from zil.extractor import extract_game_data, GameData
from zil.dsl import convert_zil_to_dsl


def main():
    parser = argparse.ArgumentParser(description="Convert ZIL to DSL YAML")
    parser.add_argument("files", nargs="+", help="ZIL source files to convert")
    parser.add_argument("-o", "--output", help="Output YAML file (stdout if omitted)")
    parser.add_argument("--name", default="Converted Game", help="Game name")
    parser.add_argument("--author", default="Unknown", help="Author name")
    parser.add_argument("--starting-room", help="Starting room name")
    parser.add_argument("--show-warnings", action="store_true", help="Show conversion warnings")
    parser.add_argument("--stats", action="store_true", help="Show statistics")

    args = parser.parse_args()

    # Parse all ZIL files
    combined_data = GameData()

    for filepath in args.files:
        path = Path(filepath)
        if not path.exists():
            print(f"Warning: {path} not found, skipping", file=sys.stderr)
            continue

        try:
            with open(path) as f:
                content = f.read()

            ast = parse(content)
            file_data = extract_game_data(ast)

            # Merge into combined data
            combined_data.rooms.update(file_data.rooms)
            combined_data.objects.update(file_data.objects)
            combined_data.routines.update(file_data.routines)
            combined_data.syntax.extend(file_data.syntax)
            combined_data.constants.update(file_data.constants)
            combined_data.globals.update(file_data.globals)
            combined_data.synonyms.update(file_data.synonyms)
            if file_data.directions:
                combined_data.directions = file_data.directions

            if args.stats:
                print(f"Parsed {path.name}:", file=sys.stderr)
                print(f"  Rooms: {len(file_data.rooms)}", file=sys.stderr)
                print(f"  Objects: {len(file_data.objects)}", file=sys.stderr)
                print(f"  Routines: {len(file_data.routines)}", file=sys.stderr)
                print(f"  Syntax: {len(file_data.syntax)}", file=sys.stderr)

        except Exception as e:
            print(f"Error parsing {path}: {e}", file=sys.stderr)
            continue

    # Convert to DSL
    result = convert_zil_to_dsl(
        combined_data,
        name=args.name,
        author=args.author,
        starting_room=args.starting_room,
    )

    if args.show_warnings and result.warnings:
        print("\n=== Conversion Warnings ===", file=sys.stderr)
        for warning in result.warnings:
            print(f"  - {warning}", file=sys.stderr)

    if args.stats:
        print("\n=== Combined Statistics ===", file=sys.stderr)
        print(f"Total rooms: {len(result.world.rooms)}", file=sys.stderr)
        print(f"Total objects: {len(result.world.objects)}", file=sys.stderr)
        print(f"Total actions: {len(result.world.actions)}", file=sys.stderr)
        print(f"Warnings: {len(result.warnings)}", file=sys.stderr)

    # Output YAML
    yaml_str = result.world.to_yaml()

    if args.output:
        with open(args.output, "w") as f:
            f.write(yaml_str)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(yaml_str)


if __name__ == "__main__":
    main()
