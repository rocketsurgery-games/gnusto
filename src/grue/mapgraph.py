"""Room-topology map + dangling-reference lint for Grue worlds.

This is a *conversion-support* tool (distinct from the winnability-focused frotz
analyses): it walks the static room graph and reports

  1. dangling references — exits ``:to`` a room that isn't defined, ``:via`` /
     ``:visible`` an object that isn't defined, and objects whose ``:location``
     is an undefined entity ("limbo"). During an incremental conversion these
     are usually the *frontier* (rooms a later slice will add), so they're
     informational by default; a stray one is almost always a typo.
  2. the connectivity graph itself, as text or Graphviz DOT, so a
     deliberately non-Euclidean area (a maze) can be eyeballed against the
     source it was converted from.

Used by ``frotz map``. Mirrors the structure of ``grue.lint`` / ``grue.render``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .parser import GrueWorld


@dataclass
class DanglingRef:
    """A reference from a defined entity to an undefined one."""

    kind: str  # "exit" | "via" | "visible" | "location"
    source: str  # the room/object doing the referencing
    detail: str  # extra context (e.g. the exit direction); may be ""
    target: str  # the undefined name being referenced


@dataclass
class MapReport:
    room_count: int
    exit_count: int  # traversable exits (those with a :to)
    blocked_count: int  # message-only :blocked exits
    dangling: list[DanglingRef] = field(default_factory=list)

    def dangling_of(self, kind: str) -> list[DanglingRef]:
        return [d for d in self.dangling if d.kind == kind]

    @property
    def frontier(self) -> list[str]:
        """Distinct undefined rooms referenced by exits (the "what's left" set)."""
        seen: dict[str, None] = {}
        for d in self.dangling:
            if d.kind == "exit":
                seen.setdefault(d.target, None)
        return list(seen)


def build_map(world: GrueWorld) -> MapReport:
    """Walk the world's rooms/objects and collect topology + dangling refs."""
    known_rooms = set(world.rooms)
    known_entities = known_rooms | set(world.objects)

    dangling: list[DanglingRef] = []
    exit_count = 0
    blocked_count = 0

    for rname, room in world.rooms.items():
        for ex in room.exits:
            if ex.to is None:
                # Message-only blocked exit: no destination to resolve.
                if ex.blocked is not None:
                    blocked_count += 1
                if ex.via is not None and ex.via not in known_entities:
                    dangling.append(DanglingRef("via", rname, ex.direction, ex.via))
                continue
            exit_count += 1
            if ex.to not in known_rooms:
                dangling.append(DanglingRef("exit", rname, ex.direction, ex.to))
            if ex.via is not None and ex.via not in known_entities:
                dangling.append(DanglingRef("via", rname, ex.direction, ex.via))
        for vis in room.visible:
            if vis not in known_entities:
                dangling.append(DanglingRef("visible", rname, "", vis))

    for oname, obj in world.objects.items():
        loc = obj.location
        if loc is not None and loc not in known_entities:
            dangling.append(DanglingRef("location", oname, "", loc))

    return MapReport(
        room_count=len(world.rooms),
        exit_count=exit_count,
        blocked_count=blocked_count,
        dangling=dangling,
    )


# --- Text rendering ---------------------------------------------------------

_DIR_ABBR = {
    "north": "N", "south": "S", "east": "E", "west": "W",
    "ne": "NE", "nw": "NW", "se": "SE", "sw": "SW",
    "up": "U", "down": "D", "in": "IN", "out": "OUT",
}


def _dir(d: str) -> str:
    return _DIR_ABBR.get(d, d.upper())


def format_text(world: GrueWorld, report: MapReport, show_rooms: bool = False) -> str:
    lines: list[str] = []
    name = world.name or "(unnamed world)"
    lines.append(f"{name} — map")
    lines.append(
        f"  {report.room_count} rooms, {report.exit_count} traversable exits, "
        f"{report.blocked_count} blocked-message exits"
    )

    exit_d = report.dangling_of("exit")
    via_d = report.dangling_of("via")
    vis_d = report.dangling_of("visible")
    loc_d = report.dangling_of("location")

    if exit_d:
        lines.append("")
        lines.append(f"Frontier — {len(report.frontier)} undefined rooms referenced by exits:")
        # Group by target room, listing who points at it.
        by_target: dict[str, list[str]] = {}
        for d in exit_d:
            by_target.setdefault(d.target, []).append(f"{d.source} {_dir(d.detail)}")
        for target in sorted(by_target):
            srcs = ", ".join(sorted(by_target[target]))
            lines.append(f"  {target:<24} <- {srcs}")

    if via_d:
        lines.append("")
        lines.append(f"Dangling :via barriers ({len(via_d)}) — likely a typo:")
        for d in sorted(via_d, key=lambda x: (x.target, x.source)):
            lines.append(f"  {d.target:<24} <- {d.source} {_dir(d.detail)}")

    if vis_d:
        lines.append("")
        lines.append(f"Dangling :visible objects ({len(vis_d)}) — likely a typo:")
        for d in sorted(vis_d, key=lambda x: (x.target, x.source)):
            lines.append(f"  {d.target:<24} <- {d.source}")

    if loc_d:
        lines.append("")
        lines.append(f"Objects in limbo ({len(loc_d)}) — :location is an undefined entity:")
        for d in sorted(loc_d, key=lambda x: (x.source)):
            lines.append(f"  {d.source:<24} -> {d.target}")

    if not report.dangling:
        lines.append("")
        lines.append("  No dangling references — every exit, barrier, and location resolves.")

    if show_rooms:
        lines.append("")
        lines.append("Rooms:")
        for rname in sorted(world.rooms):
            room = world.rooms[rname]
            parts: list[str] = []
            for ex in room.exits:
                if ex.to is not None:
                    tag = f"{_dir(ex.direction)}->{ex.to}"
                    if ex.via is not None:
                        tag += f"(via {ex.via})"
                    parts.append(tag)
                elif ex.blocked is not None:
                    parts.append(f"{_dir(ex.direction)}->[blocked]")
            dark = room.properties.get("lit") is False
            flag = " [dark]" if dark else ""
            lines.append(f"  {rname:<22}{flag} {'  '.join(parts)}")

    return "\n".join(lines)


# --- Graphviz DOT -----------------------------------------------------------

def to_dot(world: GrueWorld) -> str:
    """Render the room graph as Graphviz DOT.

    Defined rooms are solid boxes; undefined frontier rooms are dashed/gray.
    Edges are labeled with the exit direction. Blocked-message exits are omitted
    (they have no destination).
    """
    known = set(world.rooms)
    lines: list[str] = ["digraph map {", "  rankdir=LR;", "  node [shape=box, fontsize=10];"]
    frontier: set[str] = set()

    for rname, room in world.rooms.items():
        for ex in room.exits:
            if ex.to is None:
                continue
            if ex.to not in known:
                frontier.add(ex.to)
            style = ' style=dashed' if ex.via is not None else ""
            lines.append(f'  "{rname}" -> "{ex.to}" [label="{ex.direction}"{style}];')

    for rname, room in world.rooms.items():
        if room.properties.get("lit") is False:
            lines.append(f'  "{rname}" [fillcolor="#dddddd", style=filled];')

    for target in sorted(frontier):
        lines.append(f'  "{target}" [style=dashed, color=gray, fontcolor=gray];')

    lines.append("}")
    return "\n".join(lines)
