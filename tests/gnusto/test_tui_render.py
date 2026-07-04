"""Regression tests for the TUI room renderer (gnusto-ntr.29).

RoomEnter carries structured `list[ExitDetail]` (exits) and `list[EntityInfo]`
(objects/inventory) since the Epic B model switch. The TUI's render_block must
project those to display strings rather than joining the dataclasses directly
(which raised TypeError on the very first room render).
"""

from io import StringIO

from rich.console import Console

from gnusto.render import EntityInfo, ExitDetail, RoomEnter
from gnusto.tui import SimpleTUI


def _tui_with_capture():
    tui = SimpleTUI("games/lurkinghorror/", plain=True)
    buf = StringIO()
    tui.console = Console(file=buf, no_color=True, force_terminal=False, width=200)
    tui._can_display_images = False
    return tui, buf


def test_render_room_enter_projects_structured_exits_and_entities():
    tui, buf = _tui_with_capture()
    block = RoomEnter(
        room_id="@lab",
        name="Lab",
        description="A dim lab.",
        exits=[
            ExitDetail(direction="south", destination="Hall"),
            ExitDetail(direction="north", destination="Vault"),
        ],
        objects=[
            EntityInfo(id="@chair", name="chair"),
            EntityInfo(id="@pc", name="PC"),
        ],
        inventory=[EntityInfo(id="@key", name="brass key")],
        image=None,
    )

    # Must not raise (previously: TypeError joining ExitDetail as str).
    tui.render_block(block)

    out = buf.getvalue()
    assert "Exits: south, north" in out
    assert "chair" in out and "PC" in out
    assert "brass key" in out


def test_render_room_enter_without_exits_or_objects():
    tui, buf = _tui_with_capture()
    block = RoomEnter(
        room_id="@void",
        name="Void",
        description="Nothing here.",
        exits=[],
        objects=[],
        inventory=[],
        image=None,
    )
    tui.render_block(block)  # empty collections skip the join branches entirely
    assert "Void" in buf.getvalue()
