"""Tests for parse-only block derivation (gnusto-ntr.28).

In parse-only mode the ENGINE owns all text; the LLM only picks actions. These
tests pin the light presentation intent we derive from the action + engine
result: examine-style verbs on renderable entities become `focus` panels,
dialogue becomes `speak`, and everything else stays plain `narrate`. The model
never authors prose here, so there is nothing to fabricate.
"""

from types import SimpleNamespace

import gnusto.agent as agent
from gnusto.agent import GameSession
from gnusto.llm import ActionRequest
from gnusto.render import Focus, Narrate, Reveal, Sfx, Speak, Splash
from grue.repl import ActionBlocked, ActionDone, ActionError


def _session(monkeypatch, scene):
    """A GameSession stub carrying just what block derivation reads."""
    monkeypatch.setattr(
        agent, "build_scene_context", lambda state, runtime, game_dir: scene
    )
    sess = GameSession.__new__(GameSession)
    sess.runtime = object()
    sess.game_dir = None
    sess.get_state = lambda: SimpleNamespace(room="@room")
    return sess


def _done(*, output=None, reason=None):
    return ActionDone(
        message="",
        context=[],
        effects=[],
        redirects=[],
        output=output or [],
        reason=reason,
    )


def test_examine_renderable_entity_becomes_focus(monkeypatch):
    sess = _session(monkeypatch, {"@hacker": {"name": "hacker", "image": "/h.jpg"}})
    action = ActionRequest(tool="do_action", target="@hacker", verb="examine")
    result = _done(reason="A wiry figure hunched over a terminal.")

    blocks = sess._blocks_from_results([result], action)

    assert len(blocks) == 1
    assert isinstance(blocks[0], Focus)
    assert blocks[0].entity == "@hacker"
    assert blocks[0].deploy == "feature"
    # Text is the ENGINE's wording, verbatim.
    assert blocks[0].text == "A wiry figure hunched over a terminal."


def test_examine_artless_entity_stays_narrate(monkeypatch):
    sess = _session(monkeypatch, {"@hacker": {"name": "hacker", "image": None}})
    action = ActionRequest(tool="do_action", target="@hacker", verb="examine")
    blocks = sess._blocks_from_results([_done(reason="Just a guy.")], action)

    assert [type(b) for b in blocks] == [Narrate]


def test_non_examine_verb_stays_narrate(monkeypatch):
    sess = _session(monkeypatch, {"@hacker": {"name": "hacker", "image": "/h.jpg"}})
    action = ActionRequest(tool="do_action", target="@hacker", verb="take")
    blocks = sess._blocks_from_results([_done(reason="Taken.")], action)

    assert [type(b) for b in blocks] == [Narrate]


def test_room_target_not_focused(monkeypatch):
    sess = _session(monkeypatch, {"@room": {"name": "Lab", "image": "/room.jpg"}})
    action = ActionRequest(tool="do_action", target="@room", verb="look")
    blocks = sess._blocks_from_results([_done(reason="A dim lab.")], action)

    assert [type(b) for b in blocks] == [Narrate]


def test_say_output_becomes_speak(monkeypatch):
    sess = _session(monkeypatch, {})
    action = ActionRequest(tool="do_action", target="@hacker", verb="ask-about")
    result = _done(output=[("say", "@hacker", "It opens every door.")])
    blocks = sess._blocks_from_results([result], action)

    assert len(blocks) == 1
    assert isinstance(blocks[0], Speak)
    assert blocks[0].speaker == "@hacker"
    assert blocks[0].text == "It opens every door."


def test_blocked_message_is_relayed_not_fabricated(monkeypatch):
    sess = _session(monkeypatch, {})
    action = ActionRequest(tool="do_action", target="@pc", verb="login")
    result = ActionBlocked(
        reason="unknown",
        message="It would help if you turned on the computer first.",
        context=[],
        redirects=[],
    )
    blocks = sess._blocks_from_results([result], action)

    assert len(blocks) == 1
    assert isinstance(blocks[0], Narrate)
    assert blocks[0].text == "It would help if you turned on the computer first."


def test_error_is_relayed(monkeypatch):
    sess = _session(monkeypatch, {})
    blocks = sess._blocks_from_results([ActionError(message="boom")], None)
    assert [type(b) for b in blocks] == [Narrate]
    assert blocks[0].text == "boom"


def test_focus_applied_once_across_prose(monkeypatch):
    """Only the first descriptive prose block surfaces the art; the rest narrate."""
    sess = _session(monkeypatch, {"@idol": {"name": "idol", "image": "/i.jpg"}})
    action = ActionRequest(tool="do_action", target="@idol", verb="examine")
    result = _done(
        output=[("narrate", None, "A jade idol."), ("narrate", None, "It hums.")],
        reason="Its eyes seem to follow you.",
    )
    blocks = sess._blocks_from_results([result], action)

    assert isinstance(blocks[0], Focus)
    assert all(isinstance(b, Narrate) for b in blocks[1:])
    assert sum(isinstance(b, Focus) for b in blocks) == 1


def test_no_action_context_all_narrate(monkeypatch):
    """With no action (e.g. events), prose stays plain narrate."""
    sess = _session(monkeypatch, {"@hacker": {"name": "hacker", "image": "/h.jpg"}})
    blocks = sess._blocks_from_results([_done(reason="Something stirs.")], None)
    assert [type(b) for b in blocks] == [Narrate]


def _ctx_done(pairs):
    """A success carrying terminator-context text (pre-migration convention)."""
    return ActionDone(
        message="", context=list(pairs), effects=[], redirects=[], output=[]
    )


def test_multi_result_renders_every_text_in_order(monkeypatch):
    """The compulsion bug: an action message AND a following event's description
    must BOTH render, in order (the old `if not blocks` fallback dropped the 2nd).
    """
    sess = _session(monkeypatch, {})
    action = ActionRequest(tool="do_action", target="@more-box", verb="click")
    click = _ctx_done([("message", "You touch the MORE box, and a new page appears.")])
    # Event result (e.g. runtime ActionResult from process_events).
    page = SimpleNamespace(
        output=[],
        reason=None,
        context=[("page", 1), ("description", "Olde English gibberish.")],
    )
    blocks = sess._blocks_from_results([click, page], action)

    assert [type(b) for b in blocks] == [Narrate, Narrate]
    assert blocks[0].text == "You touch the MORE box, and a new page appears."
    assert blocks[1].text == "Olde English gibberish."  # no longer dropped


def test_context_text_keys_render_in_canonical_order(monkeypatch):
    # transition listed before message in the raw context, but message renders first.
    sess = _session(monkeypatch, {})
    result = _ctx_done(
        [("transition", "You faint..."), ("message", "The photo moves.")]
    )
    blocks = sess._blocks_from_results([result], None)
    assert [b.text for b in blocks] == ["The photo moves.", "You faint..."]


def test_hint_context_renders(monkeypatch):
    # Previously dropped entirely (not in the fallback key list).
    sess = _session(monkeypatch, {})
    result = _ctx_done([("hint", "I could stand a little snack, though.")])
    blocks = sess._blocks_from_results([result], None)
    assert [b.text for b in blocks] == ["I could stand a little snack, though."]


def test_output_effects_map_to_their_blocks(monkeypatch):
    """Engine output types (gnusto-7256.2) construct their render blocks."""
    sess = _session(monkeypatch, {})
    result = SimpleNamespace(
        output=[
            ("say", "@hacker", "Hey."),
            ("focus", "@idol", "A jade idol."),
            ("reveal", "@key", "A key glints."),
            ("splash", "@photo", "A mouth."),
            ("sfx", None, "KRA-KOOM"),
            ("emphasize", None, "The walls close in."),
            ("narrate", None, "Plain prose."),
        ],
        reason=None,
        context=[],
    )
    blocks = sess._blocks_from_results([result], None)

    assert [type(b) for b in blocks] == [
        Speak,
        Focus,
        Reveal,
        Splash,
        Sfx,
        Narrate,
        Narrate,
    ]
    assert blocks[1].entity == "@idol"
    assert blocks[2].entity == "@key"
    assert blocks[3].entity == "@photo"
    assert blocks[5].beat == "emphasis"  # emphasize
    assert blocks[6].beat is None  # plain narrate


def test_blocks_to_text_flattens_stream(monkeypatch):
    sess = _session(monkeypatch, {})
    blocks = [
        Narrate(text="The door creaks open."),
        Speak(speaker="@hacker", text="Losing, huh?"),
    ]
    assert (
        sess._blocks_to_text(blocks) == 'The door creaks open. @hacker: "Losing, huh?"'
    )
