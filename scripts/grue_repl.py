#!/usr/bin/env python3
"""
Interactive REPL for testing GRUE world definitions.

Usage:
    python scripts/grue_repl.py examples/outside-door.grue
    python scripts/grue_repl.py game.grue
"""

import sys
import readline  # For command history
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from grue import load_grue, GrueRuntime


def print_location(runtime: GrueRuntime) -> None:
    """Print current location details."""
    room = runtime.get_player_location()
    desc = runtime.get_room_description()
    print(f"\n=== {room} ===")
    print(desc)

    # Show objects in the room (not in inventory)
    inventory = set(runtime.get_inventory())
    visible = [obj for obj in runtime.get_visible_objects() if obj not in inventory]
    if visible:
        print(f"\nYou can see: {', '.join(visible)}")

    # Show exits
    exits = runtime.get_exits()
    if exits:
        exit_list = [f"{d} -> {r}" for d, r in exits.items()]
        print(f"Exits: {', '.join(exit_list)}")


def print_inventory(runtime: GrueRuntime) -> None:
    """Print player inventory."""
    inv = runtime.get_inventory()
    if inv:
        print(f"You are carrying: {', '.join(inv)}")
    else:
        print("You are empty-handed.")


def print_help() -> None:
    """Print help message."""
    print("""
Commands:
  look, l          - Describe current location
  inventory, i     - Show what you're carrying
  go <direction>   - Move in a direction (n/s/e/w/in/out/up/down)
  <verb> <object>  - Perform action on object (open door, take key, etc.)
  <verb> <obj> with <obj2> - Action with instrument (unlock door with key)

  state            - Show raw game state
  flags <object>   - Show object flags
  reset            - Reset to initial state
  quit, q          - Exit

Direction shortcuts: n/s/e/w/ne/nw/se/sw/u/d/in/out
""")


def parse_command(line: str) -> tuple[str, str | None, dict]:
    """Parse a command line into verb, object, and kwargs."""
    parts = line.strip().lower().split()
    if not parts:
        return "", None, {}

    verb = parts[0]
    obj = None
    kwargs = {}

    # Direction shortcuts
    dir_map = {
        "n": "north", "s": "south", "e": "east", "w": "west",
        "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest",
        "u": "up", "d": "down",
    }

    # All valid directions
    all_directions = {
        "north", "south", "east", "west", "up", "down", "in", "out",
        "northeast", "northwest", "southeast", "southwest",
    }

    # Handle movement shortcuts (just direction word)
    if verb in dir_map:
        return "go", None, {"direction": dir_map[verb]}
    if verb in all_directions:
        return "go", None, {"direction": verb}

    # Handle "go <direction>"
    if verb == "go" and len(parts) > 1:
        direction = parts[1]
        if direction in dir_map:
            return "go", None, {"direction": dir_map[direction]}
        if direction in all_directions:
            return "go", None, {"direction": direction}

    if len(parts) == 1:
        return verb, None, {}

    # Look for "with" clause
    if "with" in parts:
        with_idx = parts.index("with")
        obj = parts[1] if with_idx > 1 else None
        if with_idx + 1 < len(parts):
            kwargs["with"] = parts[with_idx + 1].upper()
        parts = parts[:with_idx]

    # Object is second word (uppercased for matching)
    if len(parts) > 1:
        obj = parts[1].upper()

    return verb, obj, kwargs


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/grue_repl.py <file.grue>")
        print("\nExample: python scripts/grue_repl.py examples/outside-door.grue")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: {path} not found")
        sys.exit(1)

    print(f"Loading {path}...")
    world = load_grue(path)
    runtime = GrueRuntime(world)

    print(f"\n{'='*50}")
    print(f"  {world.name or path.stem}")
    if world.description:
        print(f"  {world.description}")
    print(f"{'='*50}")

    print_location(runtime)
    print("\nType 'help' for commands.\n")

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not line:
            continue

        verb, obj, kwargs = parse_command(line)

        # Meta commands
        if verb in ("quit", "q", "exit"):
            print("Goodbye!")
            break

        if verb == "help":
            print_help()
            continue

        if verb in ("look", "l"):
            print_location(runtime)
            continue

        if verb in ("inventory", "i"):
            print_inventory(runtime)
            continue

        if verb == "state":
            print("\n=== Game State ===")
            print(f"Player location: {runtime.get_player_location()}")
            print(f"Score: {runtime.state.globals.get('score', 0)}")
            print(f"Moves: {runtime.state.globals.get('moves', 0)}")
            print(f"\nObjects:")
            for name, obj_state in runtime.state.objects.items():
                if name not in runtime.state.rooms:
                    print(f"  {name}: loc={obj_state.location}, flags={obj_state.flags}")
            continue

        if verb == "flags":
            if obj and obj in runtime.state.objects:
                flags = runtime.state.objects[obj].flags
                print(f"{obj} flags: {flags}")
            else:
                print(f"Unknown object: {obj}")
            continue

        if verb == "reset":
            runtime.reset()
            print("Game reset.")
            print_location(runtime)
            continue

        # Game commands
        if verb == "go":
            direction = kwargs.get("direction")
            if not direction:
                print("Go where?")
                continue
            result = runtime.do("go", direction=direction)
        elif obj:
            result = runtime.do(verb, obj, **kwargs)
        else:
            print(f"What do you want to {verb}?")
            continue

        # Show result
        if result.outcome == "success":
            if result.context:
                ctx_info = ", ".join(f"{k}={v}" for k, v in result.context)
                print(f"[OK: {ctx_info}]")
            else:
                print("[OK]")
            if result.effects_applied:
                for effect in result.effects_applied:
                    print(f"  Effect: {effect}")
            # Show new location if we moved
            if verb == "go":
                print_location(runtime)

        elif result.outcome == "blocked":
            print(f"[BLOCKED: {result.reason}]")
            if result.context:
                for key, val in result.context:
                    print(f"  {key}: {val}")

        elif result.outcome == "redirect":
            print(f"[REDIRECT: {result.redirect_action}]")

        elif result.outcome == "error":
            print(f"[ERROR: {result.error}]")

        # Check win/lose
        if runtime.check_victory():
            print("\n*** VICTORY! ***")
            if world.victory and world.victory.context:
                for key, val in world.victory.context:
                    print(f"  {key}: {val}")

        defeat = runtime.check_defeat()
        if defeat:
            print(f"\n*** DEFEAT: {defeat} ***")


if __name__ == "__main__":
    main()
