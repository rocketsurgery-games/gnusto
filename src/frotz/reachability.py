"""Gated room-graph reachability.

The movement instance of the reversibility quotient described in
`docs/design/reachability-quotient.md`. Player movement is a reversible, local
operator, so instead of tracking `@player:location` as one of ~110 concrete
rooms we reason about it as a graph-reachability question, decoupled from the
puzzle state space. This module is the shared primitive behind three consumers:

- `requires` / `depgraph` — backward: which barriers are *required* to reach a
  target room (the barriers on every path);
- `map` connectivity — forward: which rooms are reachable from here under the
  current gate state;
- the explorer's location abstraction (yak gnusto-otr.14) — the SCC/region
  quotient of the movement graph.

All queries operate on the static room graph built from `room.exits`. Message-
only `:blocked` exits and exits whose `:to` is a dangling (undefined) room are
excluded (the map lint reports those separately).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from grue import GrueWorld


@dataclass(frozen=True)
class RoomEdge:
    """A directed, possibly-gated movement edge between two rooms."""

    src: str
    dst: str
    direction: str
    via: str | None = None  # barrier object gating this edge, if any


@dataclass
class RoomGraph:
    rooms: set[str]
    edges: list[RoomEdge] = field(default_factory=list)
    _adj: dict[str, list[RoomEdge]] = field(default_factory=dict)

    def out_edges(self, room: str) -> list[RoomEdge]:
        return self._adj.get(room, [])

    @property
    def barriers(self) -> set[str]:
        """All distinct :via barrier objects appearing on some edge."""
        return {e.via for e in self.edges if e.via is not None}


# A gate predicate decides whether an edge is currently traversable.
GatePred = Callable[[RoomEdge], bool]

_ALL_OPEN: GatePred = lambda e: True


def build_room_graph(world: GrueWorld) -> RoomGraph:
    """Build the directed room graph from the world's exits.

    Only real, traversable exits become edges: a message-only `:blocked` exit
    (``to is None``) or an exit whose destination isn't a defined room is skipped.
    """
    rooms = set(world.rooms)
    graph = RoomGraph(rooms=rooms)
    for rname, room in world.rooms.items():
        for ex in room.exits:
            if ex.to is None or ex.to not in rooms:
                continue
            edge = RoomEdge(src=rname, dst=ex.to, direction=ex.direction, via=ex.via)
            graph.edges.append(edge)
            graph._adj.setdefault(rname, []).append(edge)
    return graph


def reachable_rooms(
    graph: RoomGraph, start: str, is_open: GatePred = _ALL_OPEN
) -> set[str]:
    """Rooms reachable from ``start`` (inclusive) following traversable edges.

    ``is_open(edge)`` decides traversability; the default treats every edge as
    passable, giving pure topological connectivity. For sound *deadend* use pass
    a predicate that is an over-approximation of passability (unknown ⇒ open), so
    that a room absent from the result is provably unreachable.
    """
    seen = {start}
    stack = [start]
    while stack:
        room = stack.pop()
        for edge in graph.out_edges(room):
            if edge.dst not in seen and is_open(edge):
                seen.add(edge.dst)
                stack.append(edge.dst)
    return seen


def is_reachable(
    graph: RoomGraph, start: str, target: str, is_open: GatePred = _ALL_OPEN
) -> bool:
    """Whether ``target`` is reachable from ``start``."""
    return target in reachable_rooms(graph, start, is_open)


def required_barriers(graph: RoomGraph, start: str, target: str) -> set[str]:
    """The barriers whose edges form a directed cut between ``start`` and ``target``.

    A barrier ``B`` is returned iff removing all edges gated by ``B`` makes
    ``target`` unreachable from ``start`` in the directed graph.

    SOUNDNESS CAVEAT (see docs/design/reachability-quotient.md, conditions 1/2/4,
    and the gnusto-otr.14 findings). This is only a sound "must get past B"
    answer when the graph's edges reflect *actual directional traversability*. It
    does NOT on a naive static exit graph, because games declare edges that are
    dynamically one-way or state-asymmetric as ordinary bidirectional exits — the
    trap-door that slams shut on descent, a grate that only unlocks from below, a
    one-way chimney. Those spurious reverse edges create cycles that let the cut
    test route *around* a barrier that is physically unavoidable, so on such a
    graph this under-reports required barriers (empirically: on Zork it misses
    the kitchen window and trap-door). Treat the result as a *lower bound* until
    the movement model carries directional/gate-state honesty. The forward
    :func:`reachable_rooms` over-approximation is unaffected and remains sound for
    "provably unreachable" (deadend) claims.

    Assumes ``target`` is reachable with all edges open; callers should check
    :func:`is_reachable` first (an unreachable target vacuously has no *required*
    barrier, which would otherwise be indistinguishable from "no barriers").
    """
    if start == target:
        return set()
    required: set[str] = set()
    for barrier in graph.barriers:
        blocked_pred: GatePred = lambda e, b=barrier: e.via != b
        if not is_reachable(graph, start, target, blocked_pred):
            required.add(barrier)
    return required


def sccs(graph: RoomGraph, is_open: GatePred = _ALL_OPEN) -> list[frozenset[str]]:
    """Strongly-connected components over currently-passable edges (Tarjan).

    These are the movement *regions*: within an SCC the player can move freely
    both ways, so the region collapses to a single abstract location; edges
    between SCCs are one-way (irreversible) and stay real transitions. The result
    is the region quotient the explorer uses to abstract player location. Only
    edges accepted by ``is_open`` are considered, so the quotient is parameterized
    by the current gate state (see the design doc's soundness condition 4).
    """
    index_of: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    result: list[frozenset[str]] = []
    counter = 0

    # Iterative Tarjan to avoid recursion limits on large maps.
    for root in graph.rooms:
        if root in index_of:
            continue
        # work stack of (node, iterator-position)
        work: list[tuple[str, int]] = [(root, 0)]
        while work:
            node, pi = work[-1]
            if pi == 0:
                index_of[node] = low[node] = counter
                counter += 1
                stack.append(node)
                on_stack.add(node)
            edges = [e for e in graph.out_edges(node) if is_open(e)]
            if pi < len(edges):
                work[-1] = (node, pi + 1)
                succ = edges[pi].dst
                if succ not in index_of:
                    work.append((succ, 0))
                elif succ in on_stack:
                    low[node] = min(low[node], index_of[succ])
            else:
                # Done with node: if it's a root of an SCC, pop the component.
                if low[node] == index_of[node]:
                    comp: set[str] = set()
                    while True:
                        w = stack.pop()
                        on_stack.discard(w)
                        comp.add(w)
                        if w == node:
                            break
                    result.append(frozenset(comp))
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[node])
    return result


def regions(graph: RoomGraph, is_open: GatePred = _ALL_OPEN) -> dict[str, int]:
    """Map each room to a region id (its SCC index) under ``is_open``."""
    mapping: dict[str, int] = {}
    for rid, comp in enumerate(sccs(graph, is_open)):
        for room in comp:
            mapping[room] = rid
    return mapping


def dark_rooms(world: GrueWorld) -> set[str]:
    """Rooms that are unlit by default (ZIL rooms lacking ONBIT).

    Entering one without a carried light source is lethal, so reaching a dark
    room carries a light precondition (design-doc soundness condition 3). Callers
    that care about survival should treat edges into these rooms as gated by
    "player has a lit light source".
    """
    return {
        name
        for name, room in world.rooms.items()
        if not room.properties.get("lit", True)
    }
