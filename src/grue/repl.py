"""
Grue REPL - Execute Grue S-expressions directly.

This REPL accepts raw Grue syntax for precise game logic validation.
No natural language parsing - just S-expressions.

Commands (meta):
    (look)                    - Describe current location
    (inventory)               - Show player inventory
    (state)                   - Show full game state
    (exits)                   - Show available exits
    (reset)                   - Reset to initial state
    (help)                    - Show this help
    (quit)                    - Exit REPL

Actions:
    (do :verb V :object O)                - Perform action
    (do :verb V :object O :with W)        - Action with instrument
    (go :direction D)                     - Move in direction

Queries (return values):
    (loc OBJ)                             - Object location
    (has-flag OBJ FLAG)                   - Check flag
    (prop OBJ PROP)                       - Get property
    (flags OBJ)                           - Get all flags
    (visible? OBJ)                        - Is object visible
    (held? OBJ)                           - Is object held
    (here? OBJ)                           - Is object here

Effects (modify state directly):
    (move! OBJ DEST)                      - Move object
    (set-flag! OBJ FLAG)                  - Set flag
    (clear-flag! OBJ FLAG)                - Clear flag
    (set-prop! OBJ PROP VAL)              - Set property

Usage:
    grue-repl game.grue
    grue-repl examples/outside-door.grue
"""

import sys
import readline  # noqa: F401 - For command history
from pathlib import Path

from . import load_grue, GrueRuntime
from .sexpr import parse, SExpr, SList, Symbol, Keyword, to_string, SExprError
from .expr import ExprEvaluator, EffectExecutor, EvalError


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
        print(f"\nVisible: {', '.join(visible)}")

    # Show exits
    exits = runtime.get_exits()
    if exits:
        exit_list = [f"{d} -> {r}" for d, r in exits.items()]
        print(f"Exits: {', '.join(exit_list)}")


def print_inventory(runtime: GrueRuntime) -> None:
    """Print player inventory."""
    inv = runtime.get_inventory()
    if inv:
        print(f"Inventory: {', '.join(inv)}")
    else:
        print("Inventory: (empty)")


def print_exits(runtime: GrueRuntime) -> None:
    """Print available exits."""
    exits = runtime.get_exits()
    if exits:
        for direction, dest in exits.items():
            print(f"  {direction} -> {dest}")
    else:
        print("  (no exits)")


def print_state(runtime: GrueRuntime) -> None:
    """Print full game state."""
    print("\n=== Game State ===")
    print(f"Player location: {runtime.get_player_location()}")
    print(f"Score: {runtime.state.globals.get('score', 0)}")
    print(f"Moves: {runtime.state.globals.get('moves', 0)}")
    print(f"\nObjects:")
    for name, obj_state in sorted(runtime.state.objects.items()):
        if name not in runtime.state.rooms:
            flags_str = ", ".join(sorted(obj_state.flags)) if obj_state.flags else "(none)"
            print(f"  {name}: loc={obj_state.location}, flags=[{flags_str}]")


def print_help() -> None:
    """Print help message."""
    print(__doc__)


def extract_keyword_args(expr: SList) -> dict[str, SExpr]:
    """Extract keyword arguments from an S-expression list.

    E.g., (do :verb open :object DOOR) -> {"verb": Symbol("open"), "object": Symbol("DOOR")}
    """
    kwargs = {}
    items = expr.items[1:]  # Skip the function name
    i = 0
    while i < len(items):
        if isinstance(items[i], Keyword):
            key = items[i].name
            if i + 1 < len(items):
                kwargs[key] = items[i + 1]
                i += 2
            else:
                raise EvalError(f"Keyword :{key} has no value")
        else:
            raise EvalError(f"Expected keyword, got: {items[i]}")
    return kwargs


def eval_to_string(expr: SExpr, evaluator: ExprEvaluator) -> str:
    """Evaluate expression and return string form."""
    if isinstance(expr, Symbol):
        return expr.name
    if isinstance(expr, str):
        return expr
    return str(evaluator.eval(expr))


def execute_repl_command(expr: SExpr, runtime: GrueRuntime) -> bool:
    """Execute a REPL command. Returns True if should continue, False to quit."""
    evaluator = ExprEvaluator(runtime)

    if not isinstance(expr, SList) or len(expr) == 0:
        print(f"[Error: Expected S-expression list]")
        return True

    head = expr[0]
    if not isinstance(head, Symbol):
        print(f"[Error: Expected command name, got {head}]")
        return True

    cmd = head.name.lower()

    # Meta commands
    if cmd == "quit":
        print("Goodbye!")
        return False

    if cmd == "help":
        print_help()
        return True

    if cmd == "look":
        print_location(runtime)
        return True

    if cmd == "inventory":
        print_inventory(runtime)
        return True

    if cmd == "exits":
        print_exits(runtime)
        return True

    if cmd == "state":
        print_state(runtime)
        return True

    if cmd == "reset":
        runtime.reset()
        print("[Reset]")
        print_location(runtime)
        return True

    # Movement command: (go :direction DIR)
    if cmd == "go":
        try:
            kwargs = extract_keyword_args(expr)
            direction = kwargs.get("direction")
            if direction is None:
                print("[Error: (go) requires :direction]")
                return True

            dir_str = eval_to_string(direction, evaluator)
            result = runtime.do("go", direction=dir_str)

            if result.outcome == "success":
                print(f"[OK: moved {dir_str}]")
                print_location(runtime)
            elif result.outcome == "blocked":
                ctx = dict(result.context) if result.context else {}
                print(f"[BLOCKED: {result.reason}]")
                for k, v in ctx.items():
                    print(f"  {k}: {v}")
            else:
                print(f"[{result.outcome.upper()}: {result.error or result.reason}]")
        except EvalError as e:
            print(f"[Error: {e}]")
        return True

    # Action command: (do :verb V :object O [:with W])
    if cmd == "do":
        try:
            kwargs = extract_keyword_args(expr)
            verb = kwargs.get("verb")
            obj = kwargs.get("object")

            if verb is None:
                print("[Error: (do) requires :verb]")
                return True

            verb_str = eval_to_string(verb, evaluator)

            # Build runtime kwargs
            runtime_kwargs = {}
            if "with" in kwargs:
                runtime_kwargs["with"] = eval_to_string(kwargs["with"], evaluator)
            if "on" in kwargs:
                runtime_kwargs["on"] = eval_to_string(kwargs["on"], evaluator)
            if "direction" in kwargs:
                runtime_kwargs["direction"] = eval_to_string(kwargs["direction"], evaluator)
            if "to" in kwargs:
                runtime_kwargs["to"] = eval_to_string(kwargs["to"], evaluator)

            if obj:
                obj_str = eval_to_string(obj, evaluator)
                result = runtime.do(verb_str, obj_str, **runtime_kwargs)
            else:
                result = runtime.do(verb_str, **runtime_kwargs)

            # Show redirects if any occurred (for user awareness)
            if result.redirects:
                redirect_chain = " -> ".join(to_string(r) for r in result.redirects)
                print(f"[via {redirect_chain}]")

            if result.outcome == "success":
                ctx_info = ", ".join(f"{k}={v}" for k, v in result.context) if result.context else ""
                if ctx_info:
                    print(f"[OK: {ctx_info}]")
                else:
                    print("[OK]")
                for effect in result.effects_applied:
                    print(f"  Effect: {effect}")
            elif result.outcome == "blocked":
                print(f"[BLOCKED: {result.reason}]")
                for k, v in result.context:
                    print(f"  {k}: {v}")
            elif result.outcome == "default":
                print(f"[DEFAULT: {result.default_action}]")
            elif result.outcome == "error":
                print(f"[ERROR: {result.error}]")
            else:
                print(f"[UNKNOWN OUTCOME: {result.outcome}]")

        except EvalError as e:
            print(f"[Error: {e}]")
        return True

    # State mutation effects
    if cmd in ("move!", "set-flag!", "clear-flag!", "set-prop!", "set!", "inc!"):
        try:
            executor = EffectExecutor(runtime)
            executor.execute(expr)
            print(f"[OK: {to_string(expr)}]")
        except EvalError as e:
            print(f"[Error: {e}]")
        return True

    # Query expressions - evaluate and print result
    try:
        result = evaluator.eval(expr)
        # Format result nicely
        if isinstance(result, bool):
            print(f"=> {str(result).lower()}")
        elif isinstance(result, set):
            if result:
                print(f"=> ({' '.join(sorted(result))})")
            else:
                print("=> ()")
        elif isinstance(result, list):
            if result:
                print(f"=> ({' '.join(result)})")
            else:
                print("=> ()")
        elif result is None:
            print("=> nil")
        else:
            print(f"=> {result}")
    except EvalError as e:
        print(f"[Error: {e}]")

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: grue-repl <file.grue>")
        print("\nExample: grue-repl examples/outside-door.grue")
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
    print("\nGrue REPL")
    print("Type (help) for commands.\n")

    print_location(runtime)
    print()

    while True:
        try:
            line = input("grue> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not line:
            continue

        # Allow multiple expressions on one line
        try:
            expr = parse(line)
            if not execute_repl_command(expr, runtime):
                break
        except SExprError as e:
            print(f"[Parse error: {e}]")
            continue

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
