"""Regression tests for the TUI room renderer (gnusto-ntr.29).

RoomEnter carries structured `list[ExitDetail]` (exits) and `list[EntityInfo]`
(objects/inventory) since the Epic B model switch. The TUI's render_block must
project those to display strings rather than joining the dataclasses directly
(which raised TypeError on the very first room render).
"""

from io import StringIO

from rich.console import Console

from gnusto.render import (
    Ambient,
    Caption,
    EntityInfo,
    ExitDetail,
    Focus,
    Narrate,
    NarrativeBlock,
    Reveal,
    RoomEnter,
    Sfx,
    Speak,
    Splash,
    Think,
)
from gnusto.commands import render_blocks_to_text
from gnusto.tui import SimpleTUI
from gnusto.web import block_to_dict


def test_render_blocks_to_text_projects_room_enter():
    """The CLI text renderer (used by the agent slash-command path for /look,
    /load) must read EntityInfo/ExitDetail display fields, not join the
    dataclasses as strings (gnusto-0bf7.11).
    """
    block = RoomEnter(
        room_id="@kitchen",
        name="Kitchen",
        description="A tidy kitchen.",
        exits=[ExitDetail(direction="west", destination="Living Room")],
        objects=[EntityInfo(id="@sack", name="brown sack")],
        inventory=[EntityInfo(id="@lamp", name="brass lantern")],
    )
    text = render_blocks_to_text([block])
    assert "Kitchen" in text
    assert "A tidy kitchen." in text
    assert "Exits: Living Room" in text
    assert "You see: brown sack" in text
    assert "Carrying: brass lantern" in text


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


# A factory for every narrative block type. The test below asserts this covers
# ALL NarrativeBlock subclasses, so a new block type can't be added without a
# renderer in both the TUI and the web serializer (gnusto-7256.4).
_BLOCK_FACTORIES = {
    Narrate: lambda: Narrate(text="prose"),
    Speak: lambda: Speak(speaker="@hacker", text="hi"),
    Think: lambda: Think(text="hmm"),
    Ambient: lambda: Ambient(text="a hum"),
    Reveal: lambda: Reveal(text="a key!", entity="@key"),
    Focus: lambda: Focus(text="a close look", entity="@idol"),
    Caption: lambda: Caption(text="Meanwhile..."),
    Splash: lambda: Splash(text="THE END", entity=None),
    Sfx: lambda: Sfx(text="kaboom"),
}

_EXPECTED_WEB_TYPE = {
    Narrate: "narrate",
    Speak: "speak",
    Think: "think",
    Ambient: "ambient",
    Reveal: "reveal",
    Focus: "focus",
    Caption: "caption",
    Splash: "splash",
    Sfx: "sfx",
}


def test_every_narrative_block_type_has_a_factory():
    """Adding a NarrativeBlock subclass forces adding it to the render tests."""
    missing = set(NarrativeBlock.__subclasses__()) - set(_BLOCK_FACTORIES)
    assert not missing, f"Add these block types to the render tests: {missing}"


def test_tui_renders_every_narrative_block():
    """No narrative block type is silently dropped by the TUI (Caption/Splash/Sfx
    used to fall through with no output)."""
    for cls, make in _BLOCK_FACTORIES.items():
        tui, buf = _tui_with_capture()
        tui.render_block(make())
        assert buf.getvalue().strip(), f"TUI produced no output for {cls.__name__}"


def test_web_serializes_every_narrative_block():
    """block_to_dict maps every narrative block to its real type, never 'unknown'."""
    for cls, make in _BLOCK_FACTORIES.items():
        d = block_to_dict(make())
        assert d["type"] == _EXPECTED_WEB_TYPE[cls], (
            f"web block_to_dict misrenders {cls.__name__}: {d['type']}"
        )


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
