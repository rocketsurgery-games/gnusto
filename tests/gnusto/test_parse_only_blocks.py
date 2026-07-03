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
from gnusto.render import Focus, Narrate, Speak
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
