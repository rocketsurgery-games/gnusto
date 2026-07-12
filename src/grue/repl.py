"""
Grue REPL - Execute Grue S-expressions directly.

This REPL accepts raw Grue syntax for precise game logic validation.
No natural language parsing - just S-expressions.

Meta:
    (look)                    - Describe current location
    (inventory)               - Show player inventory
    (state)                   - Show full game state
    (exits)                   - Show available exits
    (queues)                  - Show the live event queue with countdowns
    (save [slot])             - Save game state (default slot: "default")
    (load [slot])             - Load a saved game state
    (saves)                   - List saved games
    (reset)                   - Reset to initial state
    (help)                    - Show this help
    (quit)                    - Exit REPL

Game Actions (what the gameplay agent uses):
    (do TARGET :verb)                     - Perform action on target
    (do TARGET :verb ARG1 ARG2 ...)       - Action with arguments
    (go DIRECTION)                        - Move in direction
    (wait)                                - Pass time, process events
    (wait N) / (advance N)                - Pass N turns (timed/event mechanics)

Examples:
    (do @door :open)                      - Open the door
    (do @door :unlock @key)               - Unlock door with key
    (do @hacker :give @food)              - Give food to hacker
    (do @hacker :ask-about @keys)         - Ask hacker about keys

Queries (return values):
    (loc OBJ)                             - Object location
    (:prop OBJ)                           - Get property (keyword-as-function)
    (visible? OBJ)                        - Is object visible
    (held? OBJ)                           - Is object held
    (here? OBJ)                           - Is object here
    (contents CONTAINER)                  - Get contents of container
    (visible)                             - Get visible objects
    (exits)                               - Get exits as map
    (room-description)                    - Get current room description

Debug Effects (direct state mutation for testing/debugging):
    (move OBJ DEST)                       - Move object to location
    (set OBJ :prop VAL)                   - Set object property
    (inc OBJ :prop)                       - Increment property by 1
    (inc OBJ :prop N)                     - Increment property by N
    (queue EVENT)                         - Queue an event
    (dequeue EVENT)                       - Dequeue an event
    (take OBJ)                            - Move object to player inventory

Usage:
    grue-repl game.grue
    grue-repl examples/outside-door.grue
"""

import readline  # noqa: F401 - For command history
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import GrueRuntime, load_grue
from .expr import EffectExecutor, EvalError, ExprEvaluator
from .save import list_saves, load_game, save_game
from .sexpr import Keyword, SExpr, SExprError, SList, Symbol, parse, to_string


def _extract_blocked_message(
    reason: str | None,
    context: list[tuple[str, Any]] | None,
) -> str:
    """Extract or generate a message for a blocked action.

    Looks for a 'message' key in context, otherwise generates
    a human-readable message from the reason code.
    """
    # Check context for explicit message
    if context:
        for key, value in context:
            if key == "message":
                return str(value)

    # Generate default message from reason
    reason = reason or "unknown"
    default_messages = {
        "not-here": "You can't see any such thing.",
        "no-behavior": "You can't do that.",
        "no-exit": "You can't go that way.",
        "not-held": "You're not holding that.",
        "not-open": "It's not open.",
        "already-open": "It's already open.",
        "already-closed": "It's already closed.",
        "locked": "It's locked.",
        "not-takeable": "You can't take that.",
    }
    return default_messages.get(reason, f"Blocked: {reason}")


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
    vehicle: tuple[str, str] | None = None  # (vehicle_name, preposition) if in vehicle


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
    output: list[tuple[str, str | None, str]] = field(
        default_factory=list
    )  # [(type, entity, text), ...]
    reason: str | None = (
        None  # Success reason text (e.g., description for describe/examine)
    )


@dataclass
class ActionBlocked:
    """Result of a blocked action."""

    reason: str
    message: str
    context: list[tuple[str, Any]]
    redirects: list[SExpr]
    output: list[tuple[str, str | None, str]] = field(
        default_factory=list
    )  # [(type, entity, text), ...]


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


@dataclass
class WaitResult:
    """Result of waiting (passing time). ``turns`` process_events cycles run."""

    turns: int = 1


@dataclass
class QueuesResult:
    """Display the live event queue (event -> countdown)."""

    runtime: GrueRuntime


@dataclass
class EventResult:
    """Result of a fired event."""

    event_name: str
    outcome: str
    context: list[tuple[str, Any]]
    effects: list[str]
    error: str | None = None


@dataclass
class SaveResult:
    """Result of saving the game."""

    path: str


@dataclass
class LoadResult:
    """Result of loading the game."""

    warnings: list[str]
    location: "LocationResult | None" = None


@dataclass
class SavesResult:
    """List of available saves (slot, timestamp, path)."""

    saves: list[tuple[str, str, Any]]


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
            "wait": self._cmd_wait,
            "advance": self._cmd_wait,
            "queues": self._cmd_queues,
            "save": self._cmd_save,
            "load": self._cmd_load,
            "saves": self._cmd_saves,
        }

        # Effect commands (direct state mutation for testing/debugging)
        self._effects = {"move", "set", "inc", "queue", "dequeue", "take"}

    def eval(self, expr: SExpr) -> Any:
        """Evaluate an expression and return a result."""
        if not isinstance(expr, SList) or len(expr) == 0:
            raise EvalError("Expected S-expression list")

        head = expr[0]

        # Keywords as functions go directly to base evaluator
        if isinstance(head, Keyword):
            result = self._base_eval.eval(expr)
            return QueryValue(value=result)

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

    def _to_value(self, expr: SExpr) -> Any:
        """Convert expression to its value, preserving type (int, str, etc)."""
        if isinstance(expr, Symbol):
            return expr.name  # Symbols become strings
        if isinstance(expr, str):
            return expr
        if isinstance(expr, (int, float, bool)):
            return expr
        # Evaluate complex expressions
        return self._base_eval.eval(expr)

    def _make_location_result(self) -> LocationResult:
        """Create a LocationResult from current state."""
        room = self.runtime.get_player_room()  # Use room, not immediate location
        desc = self._base_eval.eval(parse("(room-description)"))
        visible = self.runtime.get_room_level_objects()
        exits = self._base_eval.eval(parse("(exits)"))
        vehicle = self.runtime.get_player_vehicle()
        return LocationResult(
            room=room, description=desc, visible=visible, exits=exits, vehicle=vehicle
        )

    # === REPL Commands ===

    def _cmd_quit(self, expr: SList) -> QuitResult:
        return QuitResult()

    def _cmd_help(self, expr: SList) -> HelpResult:
        return HelpResult()

    def _cmd_look(self, expr: SList) -> LocationResult:
        return self._make_location_result()

    def _cmd_inventory(self, expr: SList) -> InventoryResult:
        return InventoryResult(items=self._base_eval.eval(parse("(inventory)")))

    def _cmd_exits(self, expr: SList) -> ExitsResult:
        return ExitsResult(exits=self._base_eval.eval(parse("(exits)")))

    def _cmd_state(self, expr: SList) -> StateResult:
        return StateResult(runtime=self.runtime)

    def _cmd_reset(self, expr: SList) -> ResetResult:
        self.runtime.reset()
        return ResetResult()

    def _cmd_wait(self, expr: SList) -> WaitResult:
        """Execute (wait) / (wait N) / (advance N) - pass N turns (default 1)."""
        turns = 1
        if len(expr) >= 2:
            raw = expr[1]
            if not isinstance(raw, int) or raw < 1:
                raise EvalError("(wait N): N must be a positive integer")
            turns = raw
        return WaitResult(turns=turns)

    def _cmd_queues(self, expr: SList) -> QueuesResult:
        """Execute (queues) - show the live event queue with countdowns."""
        return QueuesResult(runtime=self.runtime)

    def _slot_arg(self, expr: SList, default: str = "default") -> str:
        """Extract an optional save-slot name from (cmd [slot])."""
        if len(expr) >= 2:
            return self._to_string(expr[1])
        return default

    def _cmd_save(self, expr: SList) -> "SaveResult":
        """Execute (save [slot]) - persist the runtime state to disk."""
        path = save_game(self.runtime, self._slot_arg(expr))
        return SaveResult(path=str(path))

    def _cmd_load(self, expr: SList) -> "LoadResult":
        """Execute (load [slot]) - restore runtime state from disk."""
        slot = self._slot_arg(expr)
        try:
            _history, _summaries, warnings = load_game(self.runtime, slot)
        except FileNotFoundError:
            raise EvalError(f"No save found for slot '{slot}'")
        return LoadResult(warnings=warnings, location=self._make_location_result())

    def _cmd_saves(self, expr: SList) -> "SavesResult":
        """Execute (saves) - list available saves for this game."""
        game_name = self.runtime.world.name or "unknown"
        return SavesResult(saves=list_saves(game_name))

    def _cmd_go(self, expr: SList) -> ActionDone | ActionBlocked | ActionError:
        """Execute (go DIRECTION)."""
        try:
            items = list(expr.items)[1:]  # Skip 'go'
            if len(items) < 1:
                return ActionError(message="(go) requires a direction")

            dir_str = self._to_string(items[0])
            # New API: do(target, verb, *args) - target ignored for "go"
            result = self.runtime.do("_movement", "go", dir_str)

            if result.outcome == "success":
                return ActionDone(
                    message=f"moved {dir_str}",
                    context=list(result.context) if result.context else [],
                    effects=[str(e) for e in result.effects_applied],
                    redirects=list(result.redirects) if result.redirects else [],
                    location=self._make_location_result(),
                    output=list(result.output) if result.output else [],
                    reason=result.reason,
                )
            elif result.outcome == "blocked":
                ctx = list(result.context) if result.context else []
                return ActionBlocked(
                    reason=result.reason or "unknown",
                    message=_extract_blocked_message(result.reason, ctx),
                    context=ctx,
                    redirects=list(result.redirects) if result.redirects else [],
                    output=list(result.output) if result.output else [],
                )
            else:
                return ActionError(
                    message=result.error or result.reason or result.outcome
                )
        except EvalError as e:
            return ActionError(message=str(e))

    def _cmd_do(self, expr: SList) -> ActionDone | ActionBlocked | ActionError:
        """Execute (do TARGET :verb arg1 arg2 ...).

        Examples:
            (do @door :open)
            (do @door :unlock @key)
            (do @hacker :give @food)
            (do @hacker :ask-about @keys)
            (do @hacker :trade @carton @master-key)
        """
        try:
            # Parse: (do TARGET :verb arg1 arg2 ...)
            items = list(expr.items)[1:]  # Skip 'do'

            if len(items) < 2:
                return ActionError(message="(do) requires TARGET :verb [args...]")

            target = items[0]
            verb_kw = items[1]

            # Verb must be a keyword
            if not isinstance(verb_kw, Keyword):
                return ActionError(
                    message=f"(do) verb must be a keyword, got {verb_kw}"
                )

            target_str = self._to_string(target)
            verb_str = verb_kw.name

            # Remaining items are positional args - preserve types (int, etc)
            args = [self._to_value(item) for item in items[2:]]

            result = self.runtime.do(target_str, verb_str, *args)

            if result.outcome == "success":
                return ActionDone(
                    message="",
                    context=list(result.context) if result.context else [],
                    effects=[str(e) for e in result.effects_applied],
                    redirects=list(result.redirects) if result.redirects else [],
                    output=list(result.output) if result.output else [],
                    reason=result.reason,
                )
            elif result.outcome == "blocked":
                ctx = list(result.context) if result.context else []
                return ActionBlocked(
                    reason=result.reason or "unknown",
                    message=_extract_blocked_message(result.reason, ctx),
                    context=ctx,
                    redirects=list(result.redirects) if result.redirects else [],
                    output=list(result.output) if result.output else [],
                )
            elif result.outcome == "default":
                return ActionDone(
                    message=f"default: {result.default_action}",
                    context=list(result.context) if result.context else [],
                    effects=[],
                    redirects=list(result.redirects) if result.redirects else [],
                    output=list(result.output) if result.output else [],
                    reason=result.reason,
                )
            else:
                return ActionError(message=result.error or result.outcome)
        except EvalError as e:
            return ActionError(message=str(e))


# === Result Printer ===


def _print_output(output: list[tuple[str, str | None, str]]) -> None:
    """Print the ordered player-facing output stream.

    Every output type (narrate/emphasize/focus/reveal/splash/sfx) prints its
    text; `say` prefixes the speaker. The REPL is a plain-text view, so the
    graphic-novel semantics collapse to lines here.
    """
    for out_type, entity, text in output:
        if out_type == "say":
            print(f'{entity}: "{text}"')
        else:
            print(text)


def _format_value(value: Any) -> str:
    """Format a value for REPL output."""
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, set):
        if value:
            return f"({' '.join(sorted(value))})"
        return "()"
    if isinstance(value, list):
        if value:
            return f"({' '.join(_format_value(v) for v in value)})"
        return "()"
    if isinstance(value, SList):
        return to_string(value)
    if isinstance(value, Symbol):
        return value.name
    if isinstance(value, Keyword):
        return f":{value.name}"
    # Fallback
    return str(value)


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

    if isinstance(result, SaveResult):
        print(f"[Saved to {result.path}]")
        return True

    if isinstance(result, LoadResult):
        for w in result.warnings:
            print(f"  Warning: {w}")
        print("[Loaded]")
        if result.location:
            print_result(result.location)
        return True

    if isinstance(result, SavesResult):
        if not result.saves:
            print("[No saves]")
        else:
            print("[Saves]")
            for slot, timestamp, _ in result.saves:
                print(f"  {slot}: {timestamp}")
        return True

    if isinstance(result, WaitResult):
        if result.turns > 1:
            print(f"[Time passes... x{result.turns}]")
        else:
            print("[Time passes...]")
        return True

    if isinstance(result, QueuesResult):
        queues = result.runtime.state.queues
        if not queues:
            print("[Queue empty]")
        else:
            print("[Event queue]")
            for event, countdown in queues.items():
                when = "indefinite" if countdown is None else f"countdown={countdown}"
                print(f"  {event}: {when}")
        return True

    if isinstance(result, LocationResult):
        # Show room name, with vehicle info if applicable
        if result.vehicle:
            vehicle_name, prep = result.vehicle
            print(f"\n=== {result.room}, {prep} {vehicle_name} ===")
        else:
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
        print(f"Score: {rt.get_object_property(rt.player_name, 'score') or 0}")
        print(f"Moves: {rt.get_object_property(rt.player_name, 'moves') or 0}")
        print(f"\nObjects:")
        for name, obj_state in sorted(rt.state.objects.items()):
            if name not in rt.state.rooms:
                # Extract flags (boolean True properties)
                flags = sorted(k for k, v in obj_state.properties.items() if v is True)
                flags_str = ", ".join(flags) if flags else "(none)"
                print(f"  {name}: loc={obj_state.location}, flags=[{flags_str}]")
        return True

    if isinstance(result, ActionDone):
        if result.redirects:
            redirect_chain = " -> ".join(to_string(r) for r in result.redirects)
            print(f"[via {redirect_chain}]")
        # Print structured output first (player-facing content)
        _print_output(result.output)
        ctx_info = (
            ", ".join(f"{k}={v}" for k, v in result.context) if result.context else ""
        )
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
        # Print structured output first (player-facing content)
        _print_output(result.output)
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

    if isinstance(result, EventResult):
        if result.outcome == "error":
            # A fired event that threw must be loud, not a silent no-op
            # (gnusto-160b).
            print(f"[EVENT ERROR: {result.event_name}] {result.error or 'engine error'}")
            return True
        print(f"[EVENT: {result.event_name}]")
        for k, v in result.context:
            print(f"  {k}: {v}")
        for effect in result.effects:
            print(f"  Effect: {effect}")
        return True

    if isinstance(result, QueryValue):
        value = result.value
        print(f"=> {_format_value(value)}")
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

    print(f"\n{'=' * 50}")
    print(f"  {world.name or path.stem}")
    if world.description:
        print(f"  {world.description}")
    print(f"{'=' * 50}")
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

        # Process events (game loop - events fire after each player action)
        # Only process after actions that advance time (do, go, wait). A
        # (wait N)/(advance N) runs the event loop N times.
        if isinstance(result, (ActionDone, ActionBlocked, WaitResult)):
            turns = result.turns if isinstance(result, WaitResult) else 1
            for _ in range(turns):
                event_results = runtime.process_events()
                for event_result in event_results:
                    # process_events tags each result with its event name
                    # (gnusto-0bf7.3).
                    event_name = event_result.event_name or "event"
                    print_result(
                        EventResult(
                            event_name=event_name,
                            outcome=event_result.outcome,
                            context=list(event_result.context)
                            if event_result.context
                            else [],
                            effects=[str(e) for e in event_result.effects_applied],
                            error=event_result.error,
                        )
                    )

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
