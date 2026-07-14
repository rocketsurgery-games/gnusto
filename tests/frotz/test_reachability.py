"""Tests for the gated room-graph reachability core (frotz.reachability)."""

from grue import parse_grue
from frotz.reachability import (
    build_room_graph,
    reachable_rooms,
    is_reachable,
    required_barriers,
    sccs,
    regions,
    dark_rooms,
)


# Linear map with one gated middle edge and an alternative bypass:
#   a --north--> b --east[via @gate]--> c
#   a --------up------------> c            (bypass, ungated)
# plus a one-way drop d -> a, and a dark room e off c.
WORLD = """
(world :name "RG" :player @player)
(room @a :description "A"
  :exits ((north :to @b) (up :to @c) (down :to @d)))
(room @b :description "B"
  :exits ((south :to @a) (east :to @c :via @gate)))
(room @c :description "C"
  :exits ((west :to @b) (in :to @e)))
(room @d :description "D")            ; d is a sink: no way back up (one-way a->d)
(room @e :description "E dark" :properties (:lit false))
(object @player :location @a)
(object @gate :location @b :properties (:door true))
"""


def _g():
    return build_room_graph(parse_grue(WORLD))


def test_build_skips_blocked_and_dangling():
    world = parse_grue(
        """
        (world :name "X" :player @player)
        (room @a :description "A"
          :exits ((north :to @b) (west :blocked "wall") (east :to @ghost)))
        (room @b :description "B" :exits ((south :to @a)))
        (object @player :location @a)
        """
    )
    g = build_room_graph(world)
    dirs = {(e.src, e.dst, e.direction) for e in g.edges}
    assert ("@a", "@b", "north") in dirs
    assert ("@b", "@a", "south") in dirs
    # blocked exit (no :to) and dangling @ghost are excluded
    assert all(e.dst != "@ghost" for e in g.edges)
    assert not any(e.direction == "west" for e in g.edges)


def test_reachable_all_open():
    g = _g()
    # From @a everything is reachable (including via the gate, treated open).
    assert reachable_rooms(g, "@a") == {"@a", "@b", "@c", "@d", "@e"}
    # @d is a sink: only itself reachable.
    assert reachable_rooms(g, "@d") == {"@d"}


def test_reachable_respects_gate_predicate():
    g = _g()
    closed_gate = lambda e: e.via is None  # only ungated edges
    reached = reachable_rooms(g, "@a", closed_gate)
    # Still reach c via the ungated `up` bypass, then e; b via north; d via down.
    assert reached == {"@a", "@b", "@c", "@d", "@e"}
    # From b with the gate closed and no bypass, can't reach c directly...
    # but b->a->up->c still works, so c is reachable. Remove the bypass to check
    # the gate actually blocks: start at b, forbid going back to a.
    only_forward = lambda e: e.via is None and e.dst != "@a"
    assert reachable_rooms(g, "@b", only_forward) == {"@b"}


def test_required_barriers_none_when_bypass_exists():
    g = _g()
    # c is reachable from a without the gate (via `up`), so @gate is NOT required.
    assert is_reachable(g, "@a", "@c")
    assert required_barriers(g, "@a", "@c") == set()


def test_required_barriers_when_gate_dominates():
    # Remove the bypass: now the only route a->...->c is through the gate.
    world = parse_grue(
        """
        (world :name "RG2" :player @player)
        (room @a :description "A" :exits ((north :to @b)))
        (room @b :description "B" :exits ((south :to @a) (east :to @c :via @gate)))
        (room @c :description "C" :exits ((west :to @b)))
        (object @player :location @a)
        (object @gate :location @b :properties (:door true))
        """
    )
    g = build_room_graph(world)
    assert is_reachable(g, "@a", "@c")
    assert required_barriers(g, "@a", "@c") == {"@gate"}


def test_sccs_and_one_way_edges():
    g = _g()
    comps = {frozenset(c) for c in sccs(g)}
    # a,b,c,e form a cycle-connected region? a<->b (north/south), b->c gated,
    # c->b (west): b,c mutually reachable. a->b and b->a: a,b,c together. e is
    # reachable from c but c->e only (no e->c): e is its own SCC. d is a sink.
    reg = regions(g)
    assert reg["@b"] == reg["@c"]          # b and c are mutually reachable
    assert reg["@a"] == reg["@b"]          # a joins them (a<->b)
    assert reg["@e"] != reg["@c"]          # one-way c->e: separate region
    assert reg["@d"] != reg["@a"]          # one-way a->d: separate region
    # every room classified
    assert set(reg) == {"@a", "@b", "@c", "@d", "@e"}
    assert len(comps) == 3                 # {a,b,c}, {e}, {d}


def test_dark_rooms():
    assert dark_rooms(parse_grue(WORLD)) == {"@e"}
