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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import load_grue, GrueRuntime
from .sexpr import parse, SExpr, SList, Symbol, Keyword, to_string, SExprError
from .expr import ExprEvaluator, EffectExecutor, EvalError


# === REPL Result Types ===
# These types know how to display themselves in the REPL

@dataclass
class QuitResult:
    """Signal to quit the REPL."""
    pass


@dataclass
class HelpResult:
    """Signal to show help."""
    pass


@dataclass
class ResetResult:
    """Signal that reset completed."""
    pass


@dataclass
class LocationResult:
    """Display location info."""
    room: str
    description: str
    visible: list[str]
    exits: dict[str, str]


@dataclass
class InventoryResult:
    """Display inventory."""
    items: list[str]


@dataclass
class ExitsResult:
    """Display exits."""
    exits: dict[str, str]


@dataclass
class StateResult:
    """Display full game state."""
    runtime: GrueRuntime


@dataclass
class ActionDone:
    """Result of a successful action (go/do)."""
    message: str
    context: list[tuple[str, Any]]
    effects: list[str]
    redirects: list[SExpr]
    location: LocationResult | None = None  # For movement


@dataclass
class ActionBlocked:
    """Result of a blocked action."""
    reason: str
    context: list[tuple[str, Any]]
    redirects: list[SExpr]


@dataclass
class ActionError:
    """Result of an error during action."""
    message: str


@dataclass
class EffectDone:
    """Result of executing an effect."""
    expr: str


@dataclass
class QueryValue:
    """Result of a query."""
    value: Any


# === REPL Evaluator ===

class ReplEvaluator:
    """Evaluate REPL expressions.

    Extends ExprEvaluator with REPL-specific commands that interact
    with the runtime.
    """

    def __init__(self, runtime: GrueRuntime):
        self.runtime = runtime
        self._base_eval = ExprEvaluator(runtime)
        self._effect_exec = EffectExecutor(runtime)

        # REPL-specific commands
        self._repl_commands = {
            "quit": self._cmd_quit,
            "help": self._cmd_help,
            "look": self._cmd_look,
            "inventory": self._cmd_inventory,
            "exits": self._cmd_exits,
            "state": self._cmd_state,
            "reset": self._cmd_reset,
            "go": self._cmd_go,
            "do": self._cmd_do,
        }

        # Effect commands
        self._effects = {"move!", "set-flag!", "clear-flag!", "set-prop!", "set!", "inc!"}

    def eval(self, expr: SExpr) -> Any:
        """Evaluate an expression and return a result."""
        if not isinstance(expr, SList) or len(expr) == 0:
            raise EvalError("Expected S-expression list")

        head = expr[0]
        if not isinstance(head, Symbol):
            raise EvalError(f"Expected command name, got {head}")

        cmd = head.name.lower()

        # Check REPL commands first
        if cmd in self._repl_commands:
            return self._repl_commands[cmd](expr)

        # Check effects
        if cmd in self._effects:
            self._effect_exec.execute(expr)
            return EffectDone(expr=to_string(expr))

        # Fall back to base evaluator (queries)
        result = self._base_eval.eval(expr)
        return QueryValue(value=result)

    # === Helper Methods ===

    def _extract_kwargs(self, expr: SList) -> dict[str, SExpr]:
        """Extract keyword arguments from an S-expression list."""
        kwargs = {}
        items = list(expr.items[1:])  # Skip the function name
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

    def _to_string(self, expr: SExpr) -> str:
        """Convert expression to string value."""
        if isinstance(expr, Symbol):
            return expr.name
        if isinstance(expr, str):
            return expr
        return str(self._base_eval.eval(expr))

    def _make_location_result(self) -> LocationResult:
        """Create a LocationResult from current state."""
        room = self.runtime.get_player_location()
        desc = self.runtime.get_room_description()
        inv_set = set(self.runtime.get_inventory())
        visible = [obj for obj in self.runtime.get_visible_objects() if obj not in inv_set]
        exits = self.runtime.get_exits()
        return LocationResult(room=room, description=desc, visible=visible, exits=exits)

    # === REPL Commands ===

    def _cmd_quit(self, expr: SList) -> QuitResult:
        return QuitResult()

    def _cmd_help(self, expr: SList) -> HelpResult:
        return HelpResult()

    def _cmd_look(self, expr: SList) -> LocationResult:
        return self._make_location_result()

    def _cmd_inventory(self, expr: SList) -> InventoryResult:
        return InventoryResult(items=self.runtime.get_inventory())

    def _cmd_exits(self, expr: SList) -> ExitsResult:
        return ExitsResult(exits=self.runtime.get_exits())

    def _cmd_state(self, expr: SList) -> StateResult:
        return StateResult(runtime=self.runtime)

    def _cmd_reset(self, expr: SList) -> ResetResult:
        self.runtime.reset()
        return ResetResult()

    def _cmd_go(self, expr: SList) -> ActionDone | ActionBlocked | ActionError:
        """Execute (go :direction DIR)."""
        try:
            kwargs = self._extract_kwargs(expr)
            direction = kwargs.get("direction")
            if direction is None:
                return ActionError(message="(go) requires :direction")

            dir_str = self._to_string(direction)
            # New API: do(target, verb, *args) - target ignored for "go"
            result = self.runtime.do("_movement", "go", dir_str)

            if result.outcome == "success":
                return ActionDone(
                    message=f"moved {dir_str}",
                    context=list(result.context) if result.context else [],
                    effects=[str(e) for e in result.effects_applied],
                    redirects=list(result.redirects) if result.redirects else [],
                    location=self._make_location_result(),
                )
            elif result.outcome == "blocked":
                return ActionBlocked(
                    reason=result.reason or "unknown",
                    context=list(result.context) if result.context else [],
                    redirects=list(result.redirects) if result.redirects else [],
                )
            else:
                return ActionError(message=result.error or result.reason or result.outcome)
        except EvalError as e:
            return ActionError(message=str(e))

    def _cmd_do(self, expr: SList) -> ActionDone | ActionBlocked | ActionError:
        """Execute (do :object TARGET :verb V [:arg1 A1 :arg2 A2 ...]).

        New API: runtime.do(target, verb, *args)

        Maps REPL kwargs to positional args based on verb:
        - :with → first positional arg (for unlock, give, etc.)
        - :topic → first positional arg (for ask-about)
        - :offer/:want → two positional args (for trade)
        """
        try:
            kwargs = self._extract_kwargs(expr)
            verb = kwargs.get("verb")
            target = kwargs.get("object")

            if verb is None:
                return ActionError(message="(do) requires :verb")
            if target is None:
                return ActionError(message="(do) requires :object (the target)")

            verb_str = self._to_string(verb)
            target_str = self._to_string(target)

            # Build positional args from kwargs based on verb semantics
            args: list[str] = []

            # Common patterns - map kwargs to positional args
            if "with" in kwargs:
                # :with is typically a key or instrument - first arg
                args.append(self._to_string(kwargs["with"]))
            if "topic" in kwargs:
                # :topic for ask-about, tell-about
                args.append(self._to_string(kwargs["topic"]))
            if "item" in kwargs:
                # :item for give
                args.append(self._to_string(kwargs["item"]))
            if "offer" in kwargs:
                # :offer for trade (first arg)
                args.append(self._to_string(kwargs["offer"]))
            if "want" in kwargs:
                # :want for trade (second arg)
                args.append(self._to_string(kwargs["want"]))

            result = self.runtime.do(target_str, verb_str, *args)

            if result.outcome == "success":
                return ActionDone(
                    message="",
                    context=list(result.context) if result.context else [],
                    effects=[str(e) for e in result.effects_applied],
                    redirects=list(result.redirects) if result.redirects else [],
                )
            elif result.outcome == "blocked":
                return ActionBlocked(
                    reason=result.reason or "unknown",
                    context=list(result.context) if result.context else [],
                    redirects=list(result.redirects) if result.redirects else [],
                )
            elif result.outcome == "default":
                return ActionDone(
                    message=f"default: {result.default_action}",
                    context=list(result.context) if result.context else [],
                    effects=[],
                    redirects=list(result.redirects) if result.redirects else [],
                )
            else:
                return ActionError(message=result.error or result.outcome)
        except EvalError as e:
            return ActionError(message=str(e))


# === Result Printer ===

def print_result(result: Any) -> bool:
    """Print a result. Returns False if should quit."""
    if isinstance(result, QuitResult):
        print("Goodbye!")
        return False

    if isinstance(result, HelpResult):
        print(__doc__)
        return True

    if isinstance(result, ResetResult):
        print("[Reset]")
        return True

    if isinstance(result, LocationResult):
        print(f"\n=== {result.room} ===")
        print(result.description)
        if result.visible:
            print(f"\nVisible: {', '.join(result.visible)}")
        if result.exits:
            exit_list = [f"{d} -> {r}" for d, r in result.exits.items()]
            print(f"Exits: {', '.join(exit_list)}")
        return True

    if isinstance(result, InventoryResult):
        if result.items:
            print(f"Inventory: {', '.join(result.items)}")
        else:
            print("Inventory: (empty)")
        return True

    if isinstance(result, ExitsResult):
        if result.exits:
            for direction, dest in result.exits.items():
                print(f"  {direction} -> {dest}")
        else:
            print("  (no exits)")
        return True

    if isinstance(result, StateResult):
        rt = result.runtime
        print("\n=== Game State ===")
        print(f"Player location: {rt.get_player_location()}")
        print(f"Score: {rt.state.globals.get('score', 0)}")
        print(f"Moves: {rt.state.globals.get('moves', 0)}")
        print(f"\nObjects:")
        for name, obj_state in sorted(rt.state.objects.items()):
            if name not in rt.state.rooms:
                flags_str = ", ".join(sorted(obj_state.flags)) if obj_state.flags else "(none)"
                print(f"  {name}: loc={obj_state.location}, flags=[{flags_str}]")
        return True

    if isinstance(result, ActionDone):
        if result.redirects:
            redirect_chain = " -> ".join(to_string(r) for r in result.redirects)
            print(f"[via {redirect_chain}]")
        ctx_info = ", ".join(f"{k}={v}" for k, v in result.context) if result.context else ""
        if result.message:
            msg = f"{result.message}" + (f", {ctx_info}" if ctx_info else "")
            print(f"[OK: {msg}]")
        elif ctx_info:
            print(f"[OK: {ctx_info}]")
        else:
            print("[OK]")
        for effect in result.effects:
            print(f"  Effect: {effect}")
        if result.location:
            print_result(result.location)
        return True

    if isinstance(result, ActionBlocked):
        if result.redirects:
            redirect_chain = " -> ".join(to_string(r) for r in result.redirects)
            print(f"[via {redirect_chain}]")
        print(f"[BLOCKED: {result.reason}]")
        for k, v in result.context:
            print(f"  {k}: {v}")
        return True

    if isinstance(result, ActionError):
        print(f"[ERROR: {result.message}]")
        return True

    if isinstance(result, EffectDone):
        print(f"[OK: {result.expr}]")
        return True

    if isinstance(result, QueryValue):
        value = result.value
        if isinstance(value, bool):
            print(f"=> {str(value).lower()}")
        elif isinstance(value, set):
            if value:
                print(f"=> ({' '.join(sorted(value))})")
            else:
                print("=> ()")
        elif isinstance(value, list):
            if value:
                print(f"=> ({' '.join(value)})")
            else:
                print("=> ()")
        elif value is None:
            print("=> nil")
        else:
            print(f"=> {value}")
        return True

    # Unknown result type - just print it
    print(f"=> {result}")
    return True


# === Main ===

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
    evaluator = ReplEvaluator(runtime)

    print(f"\n{'='*50}")
    print(f"  {world.name or path.stem}")
    if world.description:
        print(f"  {world.description}")
    print(f"{'='*50}")
    print("\nGrue REPL")
    print("Type (help) for commands.\n")

    # Initial look
    print_result(evaluator.eval(parse("(look)")))
    print()

    while True:
        try:
            line = input("grue> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not line:
            continue

        try:
            expr = parse(line)
            result = evaluator.eval(expr)
            if not print_result(result):
                break
        except SExprError as e:
            print(f"[Parse error: {e}]")
            continue
        except EvalError as e:
            print(f"[Error: {e}]")
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
