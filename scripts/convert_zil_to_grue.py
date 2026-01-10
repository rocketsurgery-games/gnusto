#!/usr/bin/env python3
"""
Convert ZIL game data to GRUE format.

Usage:
    python scripts/convert_zil_to_grue.py infocom/lurkinghorror -o lurking_horror.grue
    python scripts/convert_zil_to_grue.py infocom/lurkinghorror --dir games/lurkinghorror
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
    parser.add_argument("-o", "--output", help="Output file path (single file)")
    parser.add_argument("-d", "--dir", help="Output directory (multi-file)")
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
    elif args.dir:
        # Multi-file output to directory
        out_dir = Path(args.dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        files_written = []
        for filename, content in result.files.items():
            file_path = out_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            files_written.append(str(file_path))

        print(f"\nWrote {len(files_written)} files to {out_dir}/", file=sys.stderr)
        for f in files_written:
            print(f"  {f}", file=sys.stderr)
    elif args.output:
        Path(args.output).write_text(result.grue_source)
        print(f"\nWrote {args.output}", file=sys.stderr)
    else:
        # Default: multi-file output to games/<game>/
        game_id = Path(args.game_path).name
        out_dir = Path("games") / game_id
        out_dir.mkdir(parents=True, exist_ok=True)

        files_written = []
        for filename, content in result.files.items():
            file_path = out_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            files_written.append(str(file_path))

        print(f"\nWrote {len(files_written)} files to {out_dir}/", file=sys.stderr)
        for f in files_written:
            print(f"  {f}", file=sys.stderr)


if __name__ == "__main__":
    main()
