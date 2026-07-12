"""Parse-only sense-act loop behavior (gnusto-ntr.31).

Parse-only used to be one-shot: it executed the model's whole action batch
blindly and stopped after a single iteration. It now runs a text-free loop that
short-circuits a batch on the first block, feeds results back, and continues
toward the request under three bounds: `needs_player_input`, a repeated-block
guard, and `max_iterations`. These tests drive `process_input` with a scripted
LLM and a stubbed executor so the control flow is deterministic.
"""

import types

from gnusto.agent import GameSession
from gnusto.llm import ActionRequest, AgentResponse
from grue.repl import ActionBlocked, ActionDone


def _act(verb, tool="do_action", target="@pc"):
    return ActionRequest(tool=tool, target=target, verb=verb)


def _resp(verbs, needs_player_input=False):
    return AgentResponse(
        actions=[_act(v) for v in verbs],
        blocks=[],
        needs_player_input=needs_player_input,
    )


def _ok(verb):
    return ActionDone(
        message=f"{verb} ok", context=[], effects=[], redirects=[], output=[]
    )


def _blocked(verb):
    return ActionBlocked(
        reason="unknown", message=f"{verb} blocked", context=[], redirects=[]
    )


def _make_session(responses, blocked_verbs=()):
    """A parse-only GameSession with a scripted LLM and a stubbed executor.

    Returns (session, executed) where `executed` records the verb of every action
    the loop actually ran (so short-circuit / bounds are observable).
    """
    sess = GameSession.__new__(GameSession)
    sess.parsing_only = True
    sess.debug = False
    sess.turn_history = []
    sess.summaries = []
    sess.knowledge = types.SimpleNamespace(observe_turn=lambda **kw: None)
    sess._maybe_summarize = lambda: None
    sess._build_messages = lambda state, ui: [{"role": "system", "content": "x"}]
    fake_state = types.SimpleNamespace(room="@room", to_context_string=lambda: "STATE")
    sess.get_state = lambda: fake_state
    sess._blocks_from_results = lambda raw, action: []

    executed: list[str] = []

    def fake_exec(action):
        executed.append(action.verb)
        result = (
            _blocked(action.verb) if action.verb in blocked_verbs else _ok(action.verb)
        )
        return ([result], result.message)

    sess._execute_action = fake_exec

    queue = list(responses)
    calls = {"n": 0}

    def fake_chat(messages):
        calls["n"] += 1
        return queue.pop(0)

    sess.llm = types.SimpleNamespace(
        chat_structured=lambda messages: fake_chat(messages)
    )
    sess._llm_calls = calls
    return sess, executed


def test_short_circuit_stops_batch_at_first_block():
    # One speculative batch: sit-at ok, login blocked, password should NOT run.
    sess, executed = _make_session(
        [
            _resp(["sit-at", "login", "password"]),
            _resp([], needs_player_input=True),  # nothing left -> stop
        ],
        blocked_verbs={"login"},
    )
    sess.process_input("sit and log in")
    assert executed == ["sit-at", "login"]  # password never executed


def test_needs_player_input_stops_after_executing():
    sess, executed = _make_session([_resp(["look"], needs_player_input=True)])
    sess.process_input("look")
    assert executed == ["look"]
    assert sess._llm_calls["n"] == 1


def test_continuation_runs_multiple_steps_to_completion():
    # Engine feeds back after each step; model drives power-on -> login -> password.
    sess, executed = _make_session(
        [
            _resp(["turn-on"]),
            _resp(["login"]),
            _resp(["password"], needs_player_input=True),
        ]
    )
    sess.process_input("log in")
    assert executed == ["turn-on", "login", "password"]
    assert sess._llm_calls["n"] == 3


def test_repeated_block_guard_stops_banging():
    # Model keeps retrying the same blocked action; guard stops after the repeat.
    sess, executed = _make_session(
        [
            _resp(["login"]),
            _resp(["login"]),
            _resp(["login"]),  # should never be reached
        ],
        blocked_verbs={"login"},
    )
    sess.process_input("log in")
    assert executed == ["login", "login"]  # first block records, second repeats -> stop
    assert sess._llm_calls["n"] == 2


def test_max_iterations_bounds_the_loop():
    # A model that never yields would loop forever without the hard cap.
    sess, executed = _make_session([_resp(["wait"]) for _ in range(10)])
    sess.process_input("wait around", max_iterations=3)
    assert executed == ["wait", "wait", "wait"]
    assert sess._llm_calls["n"] == 3


def _wait_resp(needs_player_input=False):
    # A real wait TOOL (not a do_action verb'd "wait").
    return AgentResponse(
        actions=[ActionRequest(tool="wait", verb="wait")],
        blocks=[],
        needs_player_input=needs_player_input,
    )


def test_idle_wait_is_single_turn_with_beat():
    # A wait the engine says nothing about stops after ONE turn (gnusto-0bf7.2)
    # even though the model left needs_player_input=False, and still emits a
    # minimal beat so the turn isn't blank (gnusto-0bf7.1).
    sess, executed = _make_session([_wait_resp() for _ in range(5)])
    emitted: list = []
    sess.process_input("wait", on_blocks=lambda bs: emitted.extend(bs))
    assert len(executed) == 1  # did not auto-repeat
    assert sess._llm_calls["n"] == 1
    assert any(getattr(b, "text", "") == "Time passes." for b in emitted)


def test_bare_wait_stops_even_when_events_fire():
    # A bare "wait" (no until/for qualifier) is a single turn even when the turn
    # produces incidental event narration — otherwise it overshoots timed windows
    # like the endgame throw (gnusto-f0b8).
    sess, executed = _make_session([_wait_resp() for _ in range(5)])
    sess._blocks_from_results = lambda raw, action: [
        types.SimpleNamespace(text="Something dramatic happens.")
    ]
    sess.process_input("wait")
    assert len(executed) == 1
    assert sess._llm_calls["n"] == 1


def test_wait_with_engine_text_keeps_going():
    # Waiting FOR a condition keeps going: those turns DO produce engine text
    # (e.g. elevator in-transit narration), so the idle guard never trips and
    # the loop runs until the model yields (gnusto-0bf7.2).
    sess, executed = _make_session(
        [_wait_resp(), _wait_resp(), _wait_resp(needs_player_input=True)]
    )
    sess._blocks_from_results = lambda raw, action: [
        types.SimpleNamespace(text="The elevator descends.")
    ]
    sess.process_input("wait for the elevator")
    assert len(executed) == 3
