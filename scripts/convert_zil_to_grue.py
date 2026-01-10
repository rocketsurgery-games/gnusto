#!/usr/bin/env python3
"""
Convert ZIL game data to GRUE format.

Usage:
    python scripts/convert_zil_to_grue.py infocom/lurkinghorror -o lurking_horror.grue
    python scripts/convert_zil_to_grue.py infocom/zork1 --stdout
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from zil.loader import load_game
from grue.converter import convert_zil_to_grue


def main():
    parser = argparse.ArgumentParser(description="Convert ZIL to GRUE format")
    parser.add_argument("game_path", help="Path to ZIL game directory")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout")
    parser.add_argument("--name", help="Game name override")
    parser.add_argument("--starting-room", help="Starting room override")

    args = parser.parse_args()

    # Load game
    print(f"Loading {args.game_path}...", file=sys.stderr)
    try:
        data = load_game(args.game_path)
    except Exception as e:
        print(f"Error loading game: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded: {len(data.rooms)} rooms, {len(data.objects)} objects, {len(data.routines)} routines", file=sys.stderr)

    # Determine game name
    game_name = args.name
    if not game_name:
        # Try to infer from path
        path = Path(args.game_path)
        game_name = path.name.replace("-", " ").replace("_", " ").title()

    # Convert
    result = convert_zil_to_grue(
        data,
        name=game_name,
        starting_room=args.starting_room,
    )

    # Print warnings
    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):", file=sys.stderr)
        for w in result.warnings[:20]:  # Show first 20
            print(f"  - {w}", file=sys.stderr)
        if len(result.warnings) > 20:
            print(f"  ... and {len(result.warnings) - 20} more", file=sys.stderr)

    # Print stats
    print(f"\nStats:", file=sys.stderr)
    for key, val in result.stats.items():
        print(f"  {key}: {val}", file=sys.stderr)

    # Output
    if args.stdout:
        print(result.grue_source)
    elif args.output:
        Path(args.output).write_text(result.grue_source)
        print(f"\nWrote {args.output}", file=sys.stderr)
    else:
        # Default output name
        output_path = f"{Path(args.game_path).name}.grue"
        Path(output_path).write_text(result.grue_source)
        print(f"\nWrote {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
