"""Tests for the room-topology map + dangling-reference lint (grue.mapgraph)."""

from grue import parse_grue
from grue.mapgraph import build_map, to_dot, format_text


CLEAN = """
(world :name "Clean" :player @player)
(room @a :description "A" :exits ((north :to @b) (west :blocked "A wall.")))
(room @b :description "B" :exits ((south :to @a) (in :to @a :via @door)))
(object @player :location @a)
(object @door :location @b :properties (:door true))
(object @thing :location @a :properties (:takeable true))
"""

DANGLING = """
(world :name "Dangling" :player @player)
(room @a :description "A"
  :exits ((north :to @nowhere)          ; dangling exit target
          (east :to @b :via @ghostdoor)) ; dangling :via
  :visible (@phantom))                   ; dangling :visible
(room @b :description "B" :exits ((west :to @a)))
(object @player :location @a)
(object @orphan :location @limbo)        ; object in limbo
"""


def test_clean_world_has_no_dangling_refs():
    world = parse_grue(CLEAN)
    report = build_map(world)
    assert report.room_count == 2
    assert report.exit_count == 3          # a->b, b->a, b->a(via door)
    assert report.blocked_count == 1       # a west :blocked
    assert report.dangling == []


def test_dangling_exit_target_is_frontier():
    world = parse_grue(DANGLING)
    report = build_map(world)
    exit_d = report.dangling_of("exit")
    assert len(exit_d) == 1
    assert exit_d[0].source == "@a"
    assert exit_d[0].target == "@nowhere"
    assert report.frontier == ["@nowhere"]


def test_dangling_via_visible_and_limbo():
    world = parse_grue(DANGLING)
    report = build_map(world)
    assert {d.target for d in report.dangling_of("via")} == {"@ghostdoor"}
    assert {d.target for d in report.dangling_of("visible")} == {"@phantom"}
    limbo = report.dangling_of("location")
    assert len(limbo) == 1
    assert limbo[0].source == "@orphan"
    assert limbo[0].target == "@limbo"


def test_nil_location_is_not_limbo():
    """An explicit :location nil (abstract scenery) is intentional, not dangling."""
    world = parse_grue(
        """
        (world :name "Scenery" :player @player)
        (room @a :description "A" :visible (@fog))
        (object @player :location @a)
        (object @fog :location nil :properties (:nodesc true))
        """
    )
    report = build_map(world)
    assert report.dangling == []


def test_text_report_lists_frontier():
    world = parse_grue(DANGLING)
    text = format_text(world, build_map(world))
    assert "Frontier" in text
    assert "@nowhere" in text
    assert "@ghostdoor" in text


def test_dot_marks_frontier_dashed():
    world = parse_grue(DANGLING)
    dot = to_dot(world)
    assert 'digraph map' in dot
    assert '"@a" -> "@nowhere"' in dot
    # frontier node styled dashed/gray
    assert '"@nowhere" [style=dashed' in dot
