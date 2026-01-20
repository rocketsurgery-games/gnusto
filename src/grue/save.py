"""
Save and load game state for Grue runtime.

Serializes game state to human-readable Grue S-expression format.
Designed for forward compatibility - unknown objects/events are skipped
with warnings, allowing old saves to work with updated game files.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

from .sexpr import parse, SList, Symbol, Keyword, SExpr

if TYPE_CHECKING:
    from .runtime import GrueRuntime


# Save file version for future compatibility
SAVE_VERSION = 1


@dataclass
class SaveData:
    """Parsed save file data."""
    version: int
    game: str
    saved: str
    objects: dict[str, dict[str, Any]]  # name -> {location, properties}
    queues: dict[str, int | None]  # event -> countdown
    history: list[dict[str, Any]]  # turn records


def get_save_dir(game_name: str) -> Path:
    """Get the save directory for a game, creating if needed."""
    save_dir = Path.home() / ".frotz-lm" / "saves" / game_name
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir


def get_save_path(game_name: str, slot: str = "default") -> Path:
    """Get the full path for a save file."""
    save_dir = get_save_dir(game_name)
    # Sanitize slot name
    safe_slot = "".join(c for c in slot if c.isalnum() or c in "-_")
    if not safe_slot:
        safe_slot = "default"
    return save_dir / f"{safe_slot}.save.grue"


def _escape_string(s: str) -> str:
    """Escape a string for Grue output."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _format_value(value: Any) -> str:
    """Format a Python value as Grue syntax."""
    if value is None:
        return "nil"
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        # Check if it looks like a symbol (@foo)
        if value.startswith("@"):
            return value
        return f'"{_escape_string(value)}"'
    elif isinstance(value, list):
        items = " ".join(_format_value(v) for v in value)
        return f"({items})"
    elif isinstance(value, dict):
        pairs = " ".join(f":{k} {_format_value(v)}" for k, v in value.items())
        return f"({pairs})"
    else:
        return f'"{_escape_string(str(value))}"'


def _format_properties(props: dict[str, Any]) -> str:
    """Format properties dict as Grue keyword args."""
    if not props:
        return "()"
    parts = []
    for key, value in sorted(props.items()):
        parts.append(f":{key} {_format_value(value)}")
    return f"({' '.join(parts)})"


def save_game(
    runtime: "GrueRuntime",
    slot: str = "default",
    turn_history: list[Any] | None = None,
) -> Path:
    """
    Save game state to a file.

    Args:
        runtime: The GrueRuntime to save
        slot: Save slot name (default: "default")
        turn_history: Optional list of TurnRecord objects from agent

    Returns:
        Path to the saved file
    """
    game_name = runtime.world.name or "unknown"
    path = get_save_path(game_name, slot)

    lines = [
        "; Grue save file",
        f"; Game: {game_name}",
        f"; Saved: {datetime.now().isoformat()}",
        "",
        "(save",
        f"  :version {SAVE_VERSION}",
        f'  :game "{_escape_string(game_name)}"',
        f'  :saved "{datetime.now().isoformat()}"',
        "",
        "  :objects (",
    ]

    # Save all object states
    for name in sorted(runtime.state.objects.keys()):
        obj_state = runtime.state.objects[name]
        loc = obj_state.location or "nil"
        props = _format_properties(obj_state.properties)
        lines.append(f"    ({name} :location {loc} :properties {props})")

    lines.append("  )")
    lines.append("")
    lines.append("  :queues (")

    # Save event queues
    for event in sorted(runtime.state.queues.keys()):
        countdown = runtime.state.queues[event]
        countdown_str = "nil" if countdown is None else str(countdown)
        lines.append(f"    ({event} {countdown_str})")

    lines.append("  )")

    # Save turn history if provided
    if turn_history:
        lines.append("")
        lines.append("  :history (")
        for turn in turn_history:
            room = turn.room
            command = _escape_string(turn.player_command)
            actions = " ".join(f'"{_escape_string(a)}"' for a in turn.actions)
            results = " ".join(f'"{_escape_string(r)}"' for r in turn.results)
            narrative = _escape_string(turn.narrative)
            lines.append(f'    (:room {room} :command "{command}" :actions ({actions}) :results ({results}) :narrative "{narrative}")')
        lines.append("  )")

    lines.append(")")
    lines.append("")

    path.write_text("\n".join(lines))
    return path


def _parse_value(expr: SExpr) -> Any:
    """Parse a Grue S-expression into a Python value."""
    if isinstance(expr, Symbol):
        name = expr.name
        if name == "nil":
            return None
        elif name == "true":
            return True
        elif name == "false":
            return False
        else:
            return name  # Keep symbols as strings (e.g., @player)
    elif isinstance(expr, str):
        return expr
    elif isinstance(expr, (int, float)):
        return expr
    elif isinstance(expr, SList):
        # Check if it's a property list (keywords)
        if expr.items and isinstance(expr.items[0], Keyword):
            return _parse_keyword_list(expr.items)
        # Otherwise it's a regular list
        return [_parse_value(item) for item in expr.items]
    else:
        return expr


def _parse_keyword_list(items: list[SExpr]) -> dict[str, Any]:
    """Parse a keyword argument list into a dict."""
    result = {}
    i = 0
    while i < len(items):
        if isinstance(items[i], Keyword):
            key = items[i].name
            if i + 1 < len(items):
                result[key] = _parse_value(items[i + 1])
                i += 2
            else:
                result[key] = None
                i += 1
        else:
            i += 1
    return result


def _parse_keyword_list_from_python(items: list[Any]) -> dict[str, Any]:
    """Parse a keyword argument list that's already been converted to Python values.

    Handles lists like: [':location', '@tunnel', ':properties', {...}]
    where keywords are strings starting with ':'.
    """
    result = {}
    i = 0
    while i < len(items):
        item = items[i]
        # Check for keyword (Keyword object or string starting with ':')
        if isinstance(item, Keyword):
            key = item.name
        elif isinstance(item, str) and item.startswith(":"):
            key = item[1:]
        else:
            i += 1
            continue

        if i + 1 < len(items):
            result[key] = items[i + 1]
            i += 2
        else:
            result[key] = None
            i += 1
    return result


def parse_save_file(path: Path) -> SaveData:
    """Parse a save file into SaveData."""
    content = path.read_text()
    expr = parse(content)

    if not isinstance(expr, SList) or not expr.items:
        raise ValueError("Invalid save file: expected (save ...)")

    if not isinstance(expr.items[0], Symbol) or expr.items[0].name != "save":
        raise ValueError("Invalid save file: expected (save ...)")

    # Parse the keyword arguments
    data = _parse_keyword_list(expr.items[1:])

    # Extract objects
    # Note: _parse_value already converted SList to Python list
    objects = {}
    for obj_expr in data.get("objects", []):
        if isinstance(obj_expr, list) and obj_expr:
            name = obj_expr[0]
            # Parse remaining items as keyword list
            obj_data = _parse_keyword_list_from_python(obj_expr[1:])
            objects[name] = {
                "location": obj_data.get("location"),
                "properties": obj_data.get("properties", {}),
            }

    # Extract queues
    queues = {}
    for queue_expr in data.get("queues", []):
        if isinstance(queue_expr, list) and len(queue_expr) >= 2:
            event = queue_expr[0]
            countdown = queue_expr[1]
            queues[event] = countdown

    # Extract history
    history = []
    for turn_expr in data.get("history", []):
        if isinstance(turn_expr, dict):
            history.append(turn_expr)

    return SaveData(
        version=data.get("version", 1),
        game=data.get("game", "unknown"),
        saved=data.get("saved", ""),
        objects=objects,
        queues=queues,
        history=history,
    )


def load_game(
    runtime: "GrueRuntime",
    slot: str = "default",
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Load game state from a file.

    Args:
        runtime: The GrueRuntime to load into
        slot: Save slot name (default: "default")

    Returns:
        Tuple of (turn_history as dicts, list of warnings)

    Raises:
        FileNotFoundError: If save file doesn't exist
    """
    game_name = runtime.world.name or "unknown"
    path = get_save_path(game_name, slot)

    if not path.exists():
        raise FileNotFoundError(f"Save file not found: {path}")

    save_data = parse_save_file(path)
    warnings = []

    # Check game name matches
    if save_data.game != game_name:
        warnings.append(f"Save is for '{save_data.game}', loading into '{game_name}'")

    # Reset runtime to initial state
    runtime.reset()

    # Apply saved object states
    for obj_name, obj_data in save_data.objects.items():
        if obj_name not in runtime.state.objects:
            warnings.append(f"Unknown object {obj_name}, skipping")
            continue

        obj_state = runtime.state.objects[obj_name]

        # Update location
        location = obj_data.get("location")
        if location and location != "nil":
            obj_state.location = location
        else:
            obj_state.location = None

        # Update properties
        saved_props = obj_data.get("properties", {})
        if isinstance(saved_props, dict):
            obj_state.properties.update(saved_props)

    # Apply saved queues
    runtime.state.queues.clear()
    for event, countdown in save_data.queues.items():
        if event not in runtime.world.events:
            warnings.append(f"Unknown event {event}, skipping")
            continue
        runtime.state.queues[event] = countdown

    return save_data.history, warnings


def list_saves(game_name: str) -> list[tuple[str, str, Path]]:
    """
    List available saves for a game.

    Returns:
        List of (slot_name, timestamp, path) tuples
    """
    save_dir = get_save_dir(game_name)
    saves = []

    for path in save_dir.glob("*.save.grue"):
        slot = path.stem.replace(".save", "")
        try:
            save_data = parse_save_file(path)
            saves.append((slot, save_data.saved, path))
        except Exception:
            saves.append((slot, "unknown", path))

    return sorted(saves, key=lambda x: x[1], reverse=True)
