#!/usr/bin/env python3
"""
Simple interactive game demo showing the DSL runtime end-to-end.

Run with: python examples/simple_game.py
"""

from zil.dsl import parse_world, GameState, Runtime

# A tiny game world defined in YAML
GAME_YAML = """
meta:
  name: "Tiny Adventure"
  author: "Demo"
  starting_room: COTTAGE

rooms:
  COTTAGE:
    description: "Cozy Cottage"
    long_description: |
      You are in a small, cozy cottage. Sunlight streams through
      a dusty window. A wooden door leads north to a garden.
    exits:
      north: GARDEN
    flags:
      - ONBIT

  GARDEN:
    description: "Overgrown Garden"
    long_description: |
      You stand in an overgrown garden. Weeds and wildflowers
      compete for space. The cottage is to the south, and a
      dark forest looms to the east.
    exits:
      south: COTTAGE
      east: FOREST
    flags:
      - ONBIT

  FOREST:
    description: "Dark Forest"
    long_description: |
      Tall trees block out most of the light. It's eerily quiet
      here. The garden is back to the west.
    exits:
      west: GARDEN
    flags:
      - ONBIT

objects:
  KEY:
    description: "brass key"
    long_description: "A small brass key lies here."
    initial_location: COTTAGE
    flags:
      - TAKEBIT
    synonyms:
      - KEY
      - BRASS

  LANTERN:
    description: "old lantern"
    long_description: "An old lantern sits on a shelf."
    initial_location: COTTAGE
    flags:
      - TAKEBIT
      - LIGHTBIT
    synonyms:
      - LANTERN
      - LAMP

  CHEST:
    description: "wooden chest"
    long_description: "A locked wooden chest rests against the wall."
    initial_location: FOREST
    flags:
      - CONTBIT
      - LOCKED
    synonyms:
      - CHEST
      - BOX

actions:
  TAKE:
    syntax:
      - "take [object]"
      - "get [object]"
    preconditions:
      - "(has-flag ?obj TAKEBIT)"
      - "(not (held? ?obj))"
    effects:
      - "(move! ?obj PLAYER)"
    messages:
      success: "Taken."
      failure: "You can't take that."

  DROP:
    syntax:
      - "drop [object]"
    preconditions:
      - "(held? ?obj)"
    effects:
      - "(move! ?obj (loc PLAYER))"
    messages:
      success: "Dropped."
      failure: "You're not holding that."

  INVENTORY:
    syntax:
      - "inventory"
      - "i"
    preconditions: []
    effects: []
    messages:
      success: ""

  UNLOCK:
    syntax:
      - "unlock [object]"
    preconditions:
      - "(has-flag ?obj LOCKED)"
      - "(held? KEY)"
    effects:
      - "(clear-flag! ?obj LOCKED)"
    messages:
      success: "Click! The lock opens."
      failure: "You can't unlock that."

victory:
  when: "(not (has-flag CHEST LOCKED))"
  message: "Congratulations! You've unlocked the treasure chest and won the game!"
"""


def main():
    # Parse the world definition
    world = parse_world(GAME_YAML)

    # Create initial game state
    state = GameState.from_world(world)

    # Create runtime
    runtime = Runtime(state)

    print("=" * 60)
    print(f"  {world.meta.name}")
    print("=" * 60)
    print("\nCommands: north/south/east/west, take <obj>, drop <obj>,")
    print("          unlock <obj>, inventory (i), look (l), quit\n")
    print("-" * 60)

    # Show initial room
    print(f"\n{runtime.describe_room()}")
    show_exits(runtime)

    # Main game loop
    while True:
        # Check victory
        won, msg = runtime.check_victory()
        if won:
            print(f"\n*** {msg} ***\n")
            break

        # Get input
        try:
            command = input("\n> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not command:
            continue

        # Parse and execute command
        result = execute_command(runtime, command)

        if result == "QUIT":
            print("Goodbye!")
            break
        elif result:
            print(result)


def show_exits(runtime):
    exits = runtime.describe_exits()
    if exits:
        print(f"Exits: {', '.join(exits)}")


def execute_command(runtime, command):
    """Parse and execute a command, updating runtime state."""
    parts = command.split()
    verb = parts[0]
    obj = parts[1].upper() if len(parts) > 1 else None

    # Movement
    directions = {"n": "north", "s": "south", "e": "east", "w": "west",
                  "north": "north", "south": "south", "east": "east", "west": "west"}
    if verb in directions:
        result = runtime.move(directions[verb])
        if result.success:
            runtime.state = result.new_state
            output = f"\n{runtime.describe_room()}"
            show_exits(runtime)
            return output
        else:
            return result.message

    # Look
    if verb in ("look", "l"):
        output = f"\n{runtime.describe_room()}"
        show_exits(runtime)
        return output

    # Inventory
    if verb in ("inventory", "i"):
        adapter = runtime._state  # Access state for inventory
        inv = [o.name.lower() for o in runtime.state.objects if o.location == "PLAYER"]
        if inv:
            return f"You are carrying: {', '.join(inv)}"
        else:
            return "You are empty-handed."

    # Quit
    if verb in ("quit", "q"):
        return "QUIT"

    # Object actions
    if verb in ("take", "get") and obj:
        result = runtime.execute_action("TAKE", obj)
        if result.success:
            runtime.state = result.new_state
        return result.message

    if verb == "drop" and obj:
        result = runtime.execute_action("DROP", obj)
        if result.success:
            runtime.state = result.new_state
        return result.message

    if verb == "unlock" and obj:
        result = runtime.execute_action("UNLOCK", obj)
        if result.success:
            runtime.state = result.new_state
        return result.message

    return "I don't understand that command."


if __name__ == "__main__":
    main()
