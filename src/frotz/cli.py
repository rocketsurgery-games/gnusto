"""
Frotz CLI - IF Design Tools for Grue games.

Usage:
    frotz <command> [options]

Commands:
    reach     - Check if a state is reachable
    analyze   - Full state space analysis with victory path
    render    - Enumerate the render manifest + explosion-guard lint

Examples:
    frotz reach --to "@key@player" games/testgame
    frotz reach --to "(= (:location @player) @inf-2)" games/lurkinghorror
    frotz analyze games/testgame --dot states.dot
    frotz render games/lurkinghorror --briefs
"""

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any

from grue import load_grue
from grue.sexpr import Keyword, SList, Symbol, parse

from .backward import (
    build_victory_constraints,
    collect_constraint_refs,
    collect_navigation_refs,
)
from .effects import LocationRef, PropertyRef, QueueRef, StateRef, analyze_effects
from .explorer import ExplorationMode, StateGraph, explore_state_space

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
    loc_match = re.match(r"^(@[\w-]+)@([\w-]+)$", expr)
    if loc_match:
        obj, room = loc_match.groups()
        return [(LocationRef(obj), "=", f"@{room}")]

    # @obj:prop>=value - property comparison
    prop_match = re.match(r"^(@[\w-]+):([\w-]+)(>=|<=|!=|=)(.+)$", expr)
    if prop_match:
        obj, prop, op, value = prop_match.groups()
        value = _parse_value(value)
        return [(PropertyRef(obj, prop), op, value)]

    # queue:event=true/false
    queue_match = re.match(r"^queue:([\w-]+)(=)(true|false)$", expr, re.IGNORECASE)
    if queue_match:
        event, op, value = queue_match.groups()
        return [(QueueRef(event), op, value.lower() == "true")]

    return None


def _parse_value(value_str: str) -> Any:
    """Parse a value string to Python type."""
    value_str = value_str.strip()

    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False
    if value_str.lower() in ("nil", "none", "null"):
        return None

    # Try integer
    try:
        return int(value_str)
    except ValueError:
        pass

    # Object reference
    if value_str.startswith("@"):
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
    if op_name == "not":
        inner = _parse_sexpr_constraint(sexpr[1])
        # Flip the operator
        result = []
        for ref, op, val in inner:
            new_op = "!=" if op == "=" else "=" if op == "!=" else op
            result.append((ref, new_op, val))
        return result

    # Handle (and ...) - multiple constraints
    if op_name == "and":
        result = []
        for item in sexpr[1:]:
            result.extend(_parse_sexpr_constraint(item))
        return result

    # Comparison operators: =, !=, >=, <=, >, <
    if op_name in ("=", "!=", ">=", "<=", ">", "<"):
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
    elif isinstance(head, Symbol) and str(head).startswith(":"):
        kw = str(head)[1:]
    else:
        raise ValueError(f"Expected keyword accessor, got: {head}")

    if kw == "location":
        # (:location @obj)
        obj = _parse_object_ref(sexpr[1])
        return LocationRef(obj)

    if kw in ("prop", "property"):
        # (:prop @obj name)
        if len(sexpr) < 3:
            raise ValueError(f":prop needs object and property name")
        obj = _parse_object_ref(sexpr[1])
        prop = _parse_symbol_name(sexpr[2])
        return PropertyRef(obj, prop)

    if kw == "count":
        # (:count @obj) -> PropertyRef(@obj, 'count')
        obj = _parse_object_ref(sexpr[1])
        return PropertyRef(obj, "count")

    # Generic property access: (:propname @obj)
    obj = _parse_object_ref(sexpr[1])
    return PropertyRef(obj, kw)


def _parse_object_ref(sexpr: Any) -> str:
    """Parse @object reference."""
    if isinstance(sexpr, Symbol):
        name = sexpr.name
        if name.startswith("@"):
            return name
        return f"@{name}"
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
        if name == "true":
            return True
        if name == "false":
            return False
        if name in ("nil", "none"):
            return None
        if name.startswith("@"):
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


def state_satisfies(
    state_values: list[tuple[str, Any]], constraints: list[tuple[StateRef, str, Any]]
) -> tuple[bool, list[str]]:
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

        if op == "=":
            if actual != expected:
                missing.append(f"{ref} = {expected} (actual: {actual})")
        elif op == "!=":
            if actual == expected:
                missing.append(f"{ref} != {expected}")
        elif op == ">=":
            if actual is None or actual < expected:
                missing.append(f"{ref} >= {expected} (actual: {actual})")
        elif op == "<=":
            if actual is None or actual > expected:
                missing.append(f"{ref} <= {expected} (actual: {actual})")
        elif op == ">":
            if actual is None or actual <= expected:
                missing.append(f"{ref} > {expected} (actual: {actual})")
        elif op == "<":
            if actual is None or actual >= expected:
                missing.append(f"{ref} < {expected} (actual: {actual})")

    return len(missing) == 0, missing


# =============================================================================
# DOT Graph Generation
# =============================================================================


def generate_state_graph_dot(
    graph: StateGraph, highlight_path: list | None = None
) -> str:
    """Generate DOT graph of the actual state transition graph."""
    lines = [
        "digraph states {",
        "  rankdir=LR;",
        "  node [shape=box fontsize=10];",
        "  edge [fontsize=9];",
        "",
    ]

    # Build set of edges in the highlight path for styling
    path_edges: set[tuple[int, int]] = set()
    path_nodes: set[int] = set()
    if highlight_path:
        path_nodes.add(graph.initial_id)
        current = graph.initial_id
        for action in highlight_path:
            for edge in graph.edges:
                if edge.from_id == current and edge.action == action:
                    path_edges.add((edge.from_id, edge.to_id))
                    path_nodes.add(edge.to_id)
                    current = edge.to_id
                    break

    start_nodes = []
    victory_nodes = []
    defeat_nodes = []

    for node_id, node in graph.nodes.items():
        props = node.state.short_str().split(", ")
        player_loc = [p for p in props if p.startswith("player.loc=")]
        other_props = [p for p in props if not p.startswith("player.loc=")]

        label_lines = []
        if player_loc:
            label_lines.append(f"<b>{player_loc[0]}</b>")
        label_lines.extend(other_props)

        if node.is_victory:
            style = "style=filled fillcolor=green"
            label_lines.insert(0, "<b>VICTORY</b>")
            victory_nodes.append(f"s{node_id}")
        elif node.is_defeat:
            style = "style=filled fillcolor=red"
            label_lines.insert(0, "<b>DEFEAT</b>")
            defeat_nodes.append(f"s{node_id}")
        elif node_id == graph.initial_id:
            style = "style=filled fillcolor=lightblue"
            label_lines.insert(0, "<b>START</b>")
            start_nodes.append(f"s{node_id}")
        elif node_id in path_nodes:
            style = "style=filled fillcolor=lightyellow"
        else:
            style = ""

        html_label = "<br/>".join(label_lines)
        lines.append(f"  s{node_id} [label=<{html_label}> {style}];")

    lines.append("")
    if start_nodes:
        lines.append(f"  {{ rank=min; {'; '.join(start_nodes)}; }}")
    if victory_nodes or defeat_nodes:
        terminals = victory_nodes + defeat_nodes
        lines.append(f"  {{ rank=max; {'; '.join(terminals)}; }}")

    lines.append("")

    edge_actions: dict[tuple[int, int], list[str]] = {}
    for edge in graph.edges:
        key = (edge.from_id, edge.to_id)
        action_str = f"{edge.action.verb} {edge.action.target}"
        if edge.action.args:
            action_str += f" {' '.join(edge.action.args)}"
        action_str = action_str.replace("@", "")
        if key not in edge_actions:
            edge_actions[key] = []
        edge_actions[key].append(action_str)

    for (from_id, to_id), actions in edge_actions.items():
        label = "\\n".join(actions[:3])
        if len(actions) > 3:
            label += f"\\n+{len(actions) - 3} more"
        label = label.replace('"', '\\"')

        is_path_edge = (from_id, to_id) in path_edges
        if from_id == to_id:
            lines.append(
                f'  s{from_id} -> s{to_id} [label="{label}" style=dashed color=gray];'
            )
        elif is_path_edge:
            lines.append(
                f'  s{from_id} -> s{to_id} [label="{label}" penwidth=2 color=blue];'
            )
        else:
            lines.append(f'  s{from_id} -> s{to_id} [label="{label}"];')

    lines.append("}")
    return "\n".join(lines)


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
    target_refs.add(LocationRef("@player"))  # Always track player

    # If from_constraints specified, we'd need to find matching start state
    # For now, always start from initial state
    if from_constraints:
        print("Note: --from not yet fully implemented, starting from initial state")

    # Run exploration
    start_time = time.time()

    # By default, track only target refs + player location
    # This keeps state space manageable for simple queries
    all_refs = target_refs.copy()

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
        satisfied, missing = state_satisfies(
            list(node.state.values), target_constraints
        )
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
            if path is not None and (
                shortest_path is None or len(path) < len(shortest_path)
            ):
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

        # Generate DOT if requested
        if args.dot:
            dot_content = generate_state_graph_dot(graph, shortest_path)
            Path(args.dot).write_text(dot_content)
            print(f"\nState graph written to: {args.dot}")

        return 0
    else:
        print(f"Reachable: NO")
        print(f"States explored: {len(graph.nodes)}")
        print(f"Time: {elapsed:.2f}s")

        if closest_match[1] is not None:
            satisfied, _, missing = closest_match
            print(
                f"\nClosest approach: {satisfied}/{len(target_constraints)} constraints satisfied"
            )
            print("Missing:")
            for m in missing:
                print(f"  - {m}")

        # Generate DOT if requested
        if args.dot:
            dot_content = generate_state_graph_dot(graph)
            Path(args.dot).write_text(dot_content)
            print(f"\nState graph written to: {args.dot}")

        return 1


# =============================================================================
# analyze command - Full state space analysis
# =============================================================================


def cmd_analyze(args: argparse.Namespace) -> int:
    """Execute the analyze command (full state space exploration)."""

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
        print(f"Frotz - Analyzing: {world.name or game_path}")

    # Effect analysis
    effects = analyze_effects(world)

    if args.verbose:
        print(f"\n{'=' * 60}")
        print("Effect Analysis")
        print("=" * 60)
        print(effects.summary())

    if not world.victory:
        print("\nNo victory condition defined - skipping exploration")
        return 0

    # Constraint back-propagation
    victory_trees = build_victory_constraints(world, effects)

    if args.verbose:
        print(f"\n{'=' * 60}")
        print("Constraint Back-Propagation")
        print("=" * 60)
        print(f"Built {len(victory_trees)} constraint trees")

    # Collect state refs from constraints
    constraint_refs = collect_constraint_refs(victory_trees)
    constraint_refs.add(LocationRef("@player"))

    # Add navigation-relevant state refs
    nav_refs = collect_navigation_refs(effects)
    constraint_refs.update(nav_refs)

    if args.verbose:
        print(f"\nTracking {len(constraint_refs)} state refs")

    # State exploration
    if not args.quiet:
        print(f"\nExploring state space (max depth: {args.max_depth})...")

    start_time = time.time()
    mode = ExplorationMode.GUIDED_FIRST_VICTORY if args.fast else ExplorationMode.GUIDED
    graph, stats = explore_state_space(
        world, constraint_refs, args.max_depth, mode, None, args.max_states
    )
    elapsed = time.time() - start_time

    victory_path = graph.get_victory_path()
    victory_count = sum(1 for n in graph.nodes.values() if n.is_victory)
    defeat_count = sum(1 for n in graph.nodes.values() if n.is_defeat)

    # Walkthrough mode
    if args.walkthrough:
        if victory_path is None:
            print("No victory path found.", file=sys.stderr)
            return 1
        print(f"# Walkthrough ({len(victory_path)} steps)\n")
        for i, action in enumerate(victory_path, 1):
            target = action.target.replace("@", "")
            if action.args:
                args_str = " ".join(a.replace("@", "") for a in action.args)
                print(f"{i:2}. {action.verb} {target} {args_str}")
            else:
                print(f"{i:2}. {action.verb} {target}")
        return 0

    # Results
    print(f"\n{'=' * 60}")
    print("Results")
    print("=" * 60)
    if victory_path is not None:
        print(f"WINNABLE - Victory reachable in {len(victory_path)} steps")
        print(f"  States: {len(graph.nodes)}")
        print(f"  Transitions: {len(graph.edges)}")
        print(f"  Time: {elapsed:.2f}s")
        if defeat_count:
            print(f"  Defeat states: {defeat_count}")
    else:
        print("NO VICTORY PATH FOUND")
        print(f"  States explored: {len(graph.nodes)}")
        print(f"  Time: {elapsed:.2f}s")
        if defeat_count:
            print(f"  Defeat states: {defeat_count}")

    # Generate DOT if requested
    if args.dot:
        dot_content = generate_state_graph_dot(graph, victory_path)
        Path(args.dot).write_text(dot_content)
        print(f"\nState graph written to: {args.dot}")

    return 0 if victory_path is not None else 1


# =============================================================================
# render command - Enumerate the render manifest + explosion-guard lint
# =============================================================================

# Image formats tried (in order) when resolving an extension-less asset key.
SUPPORTED_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def _assets_dir(game_path: Path) -> Path:
    """Locate the assets directory for a game path (dir or entrypoint file)."""
    base = game_path if game_path.is_dir() else game_path.parent
    return base / "assets"


def _resolve_on_disk(assets: Path, key: str) -> Path | None:
    """Find the file for an extension-less asset key, or None if missing."""
    if (assets / key).is_file():  # literal key already carrying an extension
        return assets / key
    for ext in SUPPORTED_IMAGE_EXTS:
        if (assets / f"{key}{ext}").is_file():
            return assets / f"{key}{ext}"
    return None


def cmd_lint(args: argparse.Namespace) -> int:
    """Run the static game-logic lints (event-queue contract, ...)."""
    from grue.lint import lint_world

    game_path = Path(args.game)
    if not game_path.exists():
        print(f"Error: {game_path} not found", file=sys.stderr)
        return 1

    try:
        world = load_grue(str(game_path))
    except Exception as e:
        print(f"Error loading game: {e}", file=sys.stderr)
        return 1

    errors = lint_world(world)
    if not errors:
        print(f"✓ {world.name or game_path}: no lint issues")
        return 0

    n_err = sum(1 for e in errors if e.severity == "error")
    for e in errors:
        print(str(e))
    print(f"\n{len(errors)} issue(s) ({n_err} error, {len(errors) - n_err} warning)")
    # Errors fail the run; warnings alone fail only under --strict.
    if n_err or args.strict:
        return 1
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    """Enumerate the render manifest and run the explosion-guard lint."""
    from grue.render import assemble_style, build_render_manifest, lint_render

    game_path = Path(args.game)
    if not game_path.exists():
        print(f"Error: {game_path} not found", file=sys.stderr)
        return 1

    try:
        world = load_grue(str(game_path))
    except Exception as e:
        print(f"Error loading game: {e}", file=sys.stderr)
        return 1

    manifest = build_render_manifest(world)
    lint_errors = lint_render(world)
    # Shared style preamble, carried once rather than repeated per entry.
    style = assemble_style(getattr(world, "visual_style", None))

    # JSON dump (for external artist handoff / tooling).
    if args.json:
        import json

        payload = {
            "game": world.name or str(game_path),
            "style": style,
            "entries": [
                {
                    "key": e.key,
                    "entity": e.entity,
                    "kind": e.kind,
                    "variant": e.variant,
                    "brief": e.brief,
                }
                for e in manifest
            ],
            "lint": [
                {"entity": e.entity, "severity": e.severity, "message": e.message}
                for e in lint_errors
            ],
        }
        print(json.dumps(payload, indent=2))
        return 1 if any(e.severity == "error" for e in lint_errors) else 0

    assets = _assets_dir(game_path)
    if not args.quiet:
        print(f"Game: {world.name or game_path}")
        print(f"Assets: {assets}")
        print(f"Render keys: {len(manifest)}")
        if args.briefs and style:
            print(f"\nStyle (prepended to every brief):\n  {style}")
        print()

    # Manifest listing, with on-disk presence + the brief if requested.
    missing: list[str] = []
    manifest_keys = {e.key for e in manifest}
    for e in manifest:
        on_disk = _resolve_on_disk(assets, e.key)
        if on_disk is None:
            missing.append(e.key)
        mark = "ok " if on_disk else "MISS"
        variant = f" [{e.variant}]" if e.variant else ""
        print(f"  [{mark}] {e.key:<28} {e.entity}{variant}")
        if args.briefs:
            print(f"         {e.brief}")

    # Orphans: image files on disk with no corresponding manifest key.
    orphans: list[str] = []
    if assets.is_dir():
        for f in sorted(assets.iterdir()):
            if f.suffix.lower() in SUPPORTED_IMAGE_EXTS and f.stem not in manifest_keys:
                orphans.append(f.name)

    print()
    print(
        f"Resolved: {len(manifest) - len(missing)}/{len(manifest)}  "
        f"Missing: {len(missing)}  Orphans: {len(orphans)}"
    )
    if missing and args.verbose:
        print("Missing keys:")
        for k in missing:
            print(f"  - {k}")
    if orphans and args.verbose:
        print("Orphan files (no manifest key):")
        for o in orphans:
            print(f"  - {o}")

    # Lint results.
    errors = [e for e in lint_errors if e.severity == "error"]
    if lint_errors:
        print("\nLint:")
        for e in lint_errors:
            print(f"  {e}")
    else:
        print("\nLint: clean")

    if args.strict and (missing or orphans):
        return 1
    return 1 if errors else 0


# =============================================================================
# Main CLI entry point
# =============================================================================


def main(args: list[str] | None = None) -> int:
    """Main entry point for frotz CLI."""
    parser = argparse.ArgumentParser(
        prog="frotz",
        description="IF Design Tools - Game design validation and analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # reach subcommand
    reach_parser = subparsers.add_parser(
        "reach",
        help="Check if a state is reachable",
        description="Check if a target state is reachable from the initial state.",
    )
    reach_parser.add_argument(
        "--to",
        required=True,
        help="Target state constraint (Grue syntax or shorthand)",
    )
    reach_parser.add_argument(
        "--from",
        dest="from_state",
        help="Starting state constraint (default: initial state)",
    )
    reach_parser.add_argument(
        "game",
        help="Path to game directory or .grue file",
    )
    reach_parser.add_argument(
        "--max-depth",
        type=int,
        default=100,
        help="Maximum exploration depth (default: 100)",
    )
    reach_parser.add_argument(
        "--max-states",
        type=int,
        default=10000,
        help="Maximum states to explore (default: 10000)",
    )
    reach_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Minimal output",
    )
    reach_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    reach_parser.add_argument(
        "--deep",
        action="store_true",
        help="Use backward analysis to track more relevant state (slower)",
    )
    reach_parser.add_argument(
        "--dot",
        metavar="FILE",
        help="Output state graph in DOT format",
    )
    reach_parser.set_defaults(func=cmd_reach)

    # analyze subcommand
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Full state space analysis",
        description="Analyze game state space and find victory path.",
    )
    analyze_parser.add_argument(
        "game",
        help="Path to game directory or .grue file",
    )
    analyze_parser.add_argument(
        "--max-depth",
        type=int,
        default=100,
        help="Maximum exploration depth (default: 100)",
    )
    analyze_parser.add_argument(
        "--max-states",
        type=int,
        default=None,
        help="Maximum states to explore (default: unlimited)",
    )
    analyze_parser.add_argument(
        "--dot",
        metavar="FILE",
        help="Output state graph in DOT format",
    )
    analyze_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Minimal output",
    )
    analyze_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output (show effects, constraints)",
    )
    analyze_parser.add_argument(
        "--walkthrough",
        action="store_true",
        help="Output just the victory path as a walkthrough",
    )
    analyze_parser.add_argument(
        "--fast",
        action="store_true",
        help="Stop at first victory (faster but less complete)",
    )
    analyze_parser.set_defaults(func=cmd_analyze)

    # render subcommand
    render_parser = subparsers.add_parser(
        "render",
        help="Enumerate the render manifest and run the explosion-guard lint",
        description=(
            "Enumerate every pre-generatable image key from the game's :render / "
            ":rdesc specs, check on-disk coverage, and run the explosion-guard "
            "lint (room renders may not bake in object state; selector codomain "
            "must match declared :rdesc variants)."
        ),
    )
    render_parser.add_argument(
        "game",
        help="Path to game directory or .grue file",
    )
    render_parser.add_argument(
        "--briefs",
        action="store_true",
        help="Print the assembled generation brief for each key",
    )
    render_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the manifest + lint results as JSON (for artist/tooling handoff)",
    )
    render_parser.add_argument(
        "--strict",
        action="store_true",
        help="Also fail (exit 1) on missing or orphaned assets, not just lint errors",
    )
    render_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Minimal output",
    )
    render_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="List missing keys and orphan files",
    )
    render_parser.set_defaults(func=cmd_render)

    # lint subcommand
    lint_parser = subparsers.add_parser(
        "lint",
        help="Run static game-logic lints (event-queue contract, ...)",
        description=(
            "Static checks on game logic. Currently flags self-advancing counter "
            "events (condp on a property they mutate) that are only queued with a "
            "finite countdown and never re-queue themselves — under the one-shot "
            "queue contract they fire once, leaving later stages unreachable "
            "(the class of bug behind `compulsion`)."
        ),
    )
    lint_parser.add_argument(
        "game",
        help="Path to game directory or .grue file",
    )
    lint_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on warnings too (not just errors)",
    )
    lint_parser.set_defaults(func=cmd_lint)

    # Parse args
    opts = parser.parse_args(args)

    if opts.command is None:
        parser.print_help()
        return 1

    return opts.func(opts)


if __name__ == "__main__":
    sys.exit(main())
