"""
IF Design Tools - CLI for game design validation and analysis.

Usage:
    grue-tool <command> [options]

Commands:
    reach     - Check if a state is reachable
    requires  - Show what's needed to achieve a state (coming soon)
    blockers  - Show what's blocking progress (coming soon)

Examples:
    grue-tool reach --to "(= (:location @axe) @player)" games/lurkinghorror
    grue-tool reach --to "@axe@player" games/testgame  # shorthand
"""

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any

from grue import load_grue
from grue.sexpr import parse, SList, Symbol, Keyword

from .effects import (
    analyze_effects,
    LocationRef,
    PropertyRef,
    QueueRef,
    StateRef,
)
from .backward import build_victory_constraints, collect_constraint_refs, collect_navigation_refs
from .explorer import explore_state_space, ExplorationMode, StateGraph


# =============================================================================
# Constraint Parsing - Convert Grue syntax to internal StateRef/target pairs
# =============================================================================

def parse_constraint_expr(expr_str: str) -> list[tuple[StateRef, str, Any]]:
    """Parse a Grue constraint expression into (StateRef, op, value) tuples.

    Supported formats:

    Full Grue syntax:
        (= (:location @axe) @player)           -> LocationRef(@axe) = @player
        (= (:prop @door locked) true)          -> PropertyRef(@door, locked) = true
        (>= (:count @frob) 2)                  -> PropertyRef(@frob, count) >= 2
        (not (= (:location @axe) @player))     -> LocationRef(@axe) != @player

    Shorthand syntax:
        @axe@player                            -> LocationRef(@axe) = @player
        @axe@room                              -> LocationRef(@axe) = @room
        @door:locked=true                      -> PropertyRef(@door, locked) = true
        @frob:count>=2                         -> PropertyRef(@frob, count) >= 2

    Returns list of (StateRef, operator, value) tuples.
    """
    expr_str = expr_str.strip()

    # Try shorthand first
    shorthand = _parse_shorthand(expr_str)
    if shorthand:
        return shorthand

    # Parse as full Grue s-expression
    try:
        sexpr = parse(expr_str)
        return _parse_sexpr_constraint(sexpr)
    except Exception as e:
        raise ValueError(f"Cannot parse constraint: {expr_str!r}: {e}")


def _parse_shorthand(expr: str) -> list[tuple[StateRef, str, Any]] | None:
    """Parse shorthand constraint syntax."""

    # @obj@room - location shorthand
    loc_match = re.match(r'^(@[\w-]+)@([\w-]+)$', expr)
    if loc_match:
        obj, room = loc_match.groups()
        return [(LocationRef(obj), '=', f'@{room}')]

    # @obj:prop>=value - property comparison
    prop_match = re.match(r'^(@[\w-]+):([\w-]+)(>=|<=|!=|=)(.+)$', expr)
    if prop_match:
        obj, prop, op, value = prop_match.groups()
        value = _parse_value(value)
        return [(PropertyRef(obj, prop), op, value)]

    # queue:event=true/false
    queue_match = re.match(r'^queue:([\w-]+)(=)(true|false)$', expr, re.IGNORECASE)
    if queue_match:
        event, op, value = queue_match.groups()
        return [(QueueRef(event), op, value.lower() == 'true')]

    return None


def _parse_value(value_str: str) -> Any:
    """Parse a value string to Python type."""
    value_str = value_str.strip()

    if value_str.lower() == 'true':
        return True
    if value_str.lower() == 'false':
        return False
    if value_str.lower() in ('nil', 'none', 'null'):
        return None

    # Try integer
    try:
        return int(value_str)
    except ValueError:
        pass

    # Object reference
    if value_str.startswith('@'):
        return value_str

    # String
    return value_str


def _parse_sexpr_constraint(sexpr: Any) -> list[tuple[StateRef, str, Any]]:
    """Parse a Grue s-expression constraint."""
    if not isinstance(sexpr, SList) or len(sexpr) < 2:
        raise ValueError(f"Expected s-expression, got: {sexpr}")

    head = sexpr[0]
    if not isinstance(head, Symbol):
        raise ValueError(f"Expected symbol, got: {head}")

    op_name = head.name

    # Handle (not ...)
    if op_name == 'not':
        inner = _parse_sexpr_constraint(sexpr[1])
        # Flip the operator
        result = []
        for ref, op, val in inner:
            new_op = '!=' if op == '=' else '=' if op == '!=' else op
            result.append((ref, new_op, val))
        return result

    # Handle (and ...) - multiple constraints
    if op_name == 'and':
        result = []
        for item in sexpr[1:]:
            result.extend(_parse_sexpr_constraint(item))
        return result

    # Comparison operators: =, !=, >=, <=, >, <
    if op_name in ('=', '!=', '>=', '<=', '>', '<'):
        if len(sexpr) != 3:
            raise ValueError(f"Comparison needs 2 args: {sexpr}")

        lhs = sexpr[1]
        rhs = sexpr[2]

        # Parse left-hand side - should be a property accessor
        ref = _parse_state_accessor(lhs)

        # Parse right-hand side - should be a value
        value = _parse_sexpr_value(rhs)

        return [(ref, op_name, value)]

    raise ValueError(f"Unknown constraint operator: {op_name}")


def _parse_state_accessor(sexpr: Any) -> StateRef:
    """Parse (:location @obj) or (:prop @obj name) to StateRef."""
    if not isinstance(sexpr, SList) or len(sexpr) < 2:
        raise ValueError(f"Expected accessor, got: {sexpr}")

    head = sexpr[0]
    if isinstance(head, Keyword):
        kw = head.name
    elif isinstance(head, Symbol) and str(head).startswith(':'):
        kw = str(head)[1:]
    else:
        raise ValueError(f"Expected keyword accessor, got: {head}")

    if kw == 'location':
        # (:location @obj)
        obj = _parse_object_ref(sexpr[1])
        return LocationRef(obj)

    if kw in ('prop', 'property'):
        # (:prop @obj name)
        if len(sexpr) < 3:
            raise ValueError(f":prop needs object and property name")
        obj = _parse_object_ref(sexpr[1])
        prop = _parse_symbol_name(sexpr[2])
        return PropertyRef(obj, prop)

    if kw == 'count':
        # (:count @obj) -> PropertyRef(@obj, 'count')
        obj = _parse_object_ref(sexpr[1])
        return PropertyRef(obj, 'count')

    # Generic property access: (:propname @obj)
    obj = _parse_object_ref(sexpr[1])
    return PropertyRef(obj, kw)


def _parse_object_ref(sexpr: Any) -> str:
    """Parse @object reference."""
    if isinstance(sexpr, Symbol):
        name = sexpr.name
        if name.startswith('@'):
            return name
        return f'@{name}'
    raise ValueError(f"Expected object reference, got: {sexpr}")


def _parse_symbol_name(sexpr: Any) -> str:
    """Parse a symbol to string name."""
    if isinstance(sexpr, Symbol):
        return sexpr.name
    if isinstance(sexpr, Keyword):
        return sexpr.name
    if isinstance(sexpr, str):
        return sexpr
    raise ValueError(f"Expected symbol, got: {sexpr}")


def _parse_sexpr_value(sexpr: Any) -> Any:
    """Parse a value from s-expression."""
    if isinstance(sexpr, Symbol):
        name = sexpr.name
        if name == 'true':
            return True
        if name == 'false':
            return False
        if name in ('nil', 'none'):
            return None
        if name.startswith('@'):
            return name
        return name
    if isinstance(sexpr, (int, float, bool)):
        return sexpr
    if isinstance(sexpr, str):
        return sexpr
    raise ValueError(f"Cannot parse value: {sexpr}")


# =============================================================================
# State Matching - Check if a state satisfies constraints
# =============================================================================

def state_satisfies(state_values: list[tuple[str, Any]],
                    constraints: list[tuple[StateRef, str, Any]]) -> tuple[bool, list[str]]:
    """Check if state values satisfy all constraints.

    State values use string keys like '@obj:location' or '@obj:prop'.
    Constraints use StateRef objects.

    Returns (satisfied, missing_constraints).
    """
    # State values use string keys
    state_dict = {ref: val for ref, val in state_values}
    missing = []

    for ref, op, expected in constraints:
        # Convert StateRef to string key format used in state
        ref_key = str(ref)  # e.g., '@key:location'
        actual = state_dict.get(ref_key)

        if op == '=':
            if actual != expected:
                missing.append(f"{ref} = {expected} (actual: {actual})")
        elif op == '!=':
            if actual == expected:
                missing.append(f"{ref} != {expected}")
        elif op == '>=':
            if actual is None or actual < expected:
                missing.append(f"{ref} >= {expected} (actual: {actual})")
        elif op == '<=':
            if actual is None or actual > expected:
                missing.append(f"{ref} <= {expected} (actual: {actual})")
        elif op == '>':
            if actual is None or actual <= expected:
                missing.append(f"{ref} > {expected} (actual: {actual})")
        elif op == '<':
            if actual is None or actual >= expected:
                missing.append(f"{ref} < {expected} (actual: {actual})")

    return len(missing) == 0, missing


# =============================================================================
# reach command - Reachability query
# =============================================================================

def cmd_reach(args: argparse.Namespace) -> int:
    """Execute the reach command."""

    # Parse target constraints
    try:
        target_constraints = parse_constraint_expr(args.to)
    except ValueError as e:
        print(f"Error parsing --to constraint: {e}", file=sys.stderr)
        return 1

    # Parse starting constraints (if any)
    from_constraints = []
    if args.from_state:
        try:
            from_constraints = parse_constraint_expr(args.from_state)
        except ValueError as e:
            print(f"Error parsing --from constraint: {e}", file=sys.stderr)
            return 1

    # Load game
    game_path = Path(args.game)
    if not game_path.exists():
        print(f"Error: {game_path} not found", file=sys.stderr)
        return 1

    try:
        world = load_grue(str(game_path))
    except Exception as e:
        print(f"Error loading game: {e}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"Game: {world.name or game_path}")
        print(f"Target: {args.to}")
        if from_constraints:
            print(f"From: {args.from_state}")
        print()

    # Extract state refs to track from constraints
    target_refs: set[StateRef] = {ref for ref, _, _ in target_constraints}
    target_refs.add(LocationRef('@player'))  # Always track player

    # If from_constraints specified, we'd need to find matching start state
    # For now, always start from initial state
    if from_constraints:
        print("Note: --from not yet fully implemented, starting from initial state")

    # Run exploration
    start_time = time.time()

    # By default, track only target refs + player location
    # This keeps state space manageable for simple queries
    all_refs = target_refs.copy()
    all_refs.add(LocationRef('@player'))

    # If --deep, use backward analysis to add victory-relevant refs
    if args.deep:
        effects = analyze_effects(world)
        victory_trees = build_victory_constraints(world, effects)
        constraint_refs = collect_constraint_refs(victory_trees)
        nav_refs = collect_navigation_refs(effects)
        all_refs |= constraint_refs | nav_refs

    if args.verbose:
        print(f"Tracking {len(all_refs)} state refs")

    # Explore
    graph, stats = explore_state_space(
        world,
        all_refs,
        max_depth=args.max_depth,
        mode=ExplorationMode.GUIDED,
        max_states=args.max_states,
    )

    elapsed = time.time() - start_time

    # Find states that satisfy target constraints
    matching_states = []
    closest_match = (0, None, [])  # (satisfied_count, node_id, missing)

    for node_id, node in graph.nodes.items():
        satisfied, missing = state_satisfies(list(node.state.values), target_constraints)
        if satisfied:
            matching_states.append(node_id)
        else:
            satisfied_count = len(target_constraints) - len(missing)
            if satisfied_count > closest_match[0]:
                closest_match = (satisfied_count, node_id, missing)

    # Report results
    if matching_states:
        # Find shortest path to any matching state
        shortest_path = None
        target_node_id = None

        for node_id in matching_states:
            path = graph.get_path_to(node_id)
            if path is not None and (shortest_path is None or len(path) < len(shortest_path)):
                shortest_path = path
                target_node_id = node_id

        print(f"Reachable: YES")
        if shortest_path:
            print(f"Steps: {len(shortest_path)}")
        print(f"States explored: {len(graph.nodes)}")
        print(f"Time: {elapsed:.2f}s")

        if shortest_path and not args.quiet:
            print(f"\nPath:")
            for i, action in enumerate(shortest_path, 1):
                target = action.target.replace("@", "")
                if action.args:
                    args_str = " ".join(a.replace("@", "") for a in action.args)
                    print(f"  {i:2}. {action.verb} {target} {args_str}")
                else:
                    print(f"  {i:2}. {action.verb} {target}")

        return 0
    else:
        print(f"Reachable: NO")
        print(f"States explored: {len(graph.nodes)}")
        print(f"Time: {elapsed:.2f}s")

        if closest_match[1] is not None:
            satisfied, _, missing = closest_match
            print(f"\nClosest approach: {satisfied}/{len(target_constraints)} constraints satisfied")
            print("Missing:")
            for m in missing:
                print(f"  - {m}")

        return 1


# =============================================================================
# Main CLI entry point
# =============================================================================

def main(args: list[str] | None = None) -> int:
    """Main entry point for grue-tool."""
    parser = argparse.ArgumentParser(
        prog='grue-tool',
        description='IF Design Tools - Game design validation and analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # reach subcommand
    reach_parser = subparsers.add_parser(
        'reach',
        help='Check if a state is reachable',
        description='Check if a target state is reachable from the initial state (or a specified starting state).',
    )
    reach_parser.add_argument(
        '--to',
        required=True,
        help='Target state constraint (Grue syntax or shorthand)',
    )
    reach_parser.add_argument(
        '--from',
        dest='from_state',
        help='Starting state constraint (default: initial state)',
    )
    reach_parser.add_argument(
        'game',
        help='Path to game directory or .grue file',
    )
    reach_parser.add_argument(
        '--max-depth',
        type=int,
        default=100,
        help='Maximum exploration depth (default: 100)',
    )
    reach_parser.add_argument(
        '--max-states',
        type=int,
        default=10000,
        help='Maximum states to explore (default: 10000)',
    )
    reach_parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Minimal output',
    )
    reach_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output',
    )
    reach_parser.add_argument(
        '--deep',
        action='store_true',
        help='Use backward analysis to track more relevant state (slower)',
    )
    reach_parser.set_defaults(func=cmd_reach)

    # Parse args
    opts = parser.parse_args(args)

    if opts.command is None:
        parser.print_help()
        return 1

    return opts.func(opts)


if __name__ == '__main__':
    sys.exit(main())
