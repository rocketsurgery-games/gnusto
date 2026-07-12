"""Tests for save/restore (grue.save) and its REPL wiring (gnusto-1e9a).

Save/restore already existed and was wired into the gnusto CLI/web; these
tests lock in the round-trip contract and cover the new grue-repl commands
((save)/(load)/(saves)).
"""

from pathlib import Path

import pytest

from grue import GrueRuntime, parse_grue
from grue.repl import LoadResult, ReplEvaluator, SaveResult, SavesResult
from grue.save import list_saves, load_game, save_game
from grue.sexpr import parse

SOURCE = """
(world :player PLAYER :name "SaveTestGame")
(room LOBBY :description "A lobby" :properties (:lit true))
(room VAULT :description "A vault" :properties (:lit true))
(object PLAYER :location LOBBY :properties (:person true))
(object COIN :location LOBBY :properties (:takeable true :shiny false))
(event tick :on-turn '((dequeue tick) (success)))
"""


def _runtime():
    return GrueRuntime(parse_grue(SOURCE))


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """Redirect ~/.gnusto to a temp dir so tests never touch the real home."""
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))


def test_save_load_roundtrip():
    rt = _runtime()
    # Mutate state: move the coin, flip a property, queue an event.
    rt.state.objects["COIN"].location = "VAULT"
    rt.state.objects["COIN"].properties["shiny"] = True
    rt.state.objects["PLAYER"].location = "VAULT"
    rt.state.queues["tick"] = 3

    save_game(rt, "slot1")

    # Fresh runtime from the same world starts at defaults...
    rt2 = _runtime()
    assert rt2.state.objects["COIN"].location == "LOBBY"
    assert rt2.state.objects["COIN"].properties.get("shiny") is False
    assert "tick" not in rt2.state.queues

    # ...and load restores the saved state.
    _history, _summaries, warnings = load_game(rt2, "slot1")
    assert warnings == []
    assert rt2.state.objects["COIN"].location == "VAULT"
    assert rt2.state.objects["COIN"].properties["shiny"] is True
    assert rt2.state.objects["PLAYER"].location == "VAULT"
    assert rt2.state.queues.get("tick") == 3


def test_load_missing_slot_raises():
    rt = _runtime()
    with pytest.raises(FileNotFoundError):
        load_game(rt, "does-not-exist")


def test_list_saves_reports_slots():
    rt = _runtime()
    save_game(rt, "alpha")
    save_game(rt, "beta")
    slots = {slot for slot, _ts, _path in list_saves("SaveTestGame")}
    assert slots == {"alpha", "beta"}


def test_repl_save_load_commands():
    rt = _runtime()
    repl = ReplEvaluator(rt)

    # Mutate, then (save reptest) through the REPL.
    rt.state.objects["COIN"].location = "VAULT"
    save_res = repl.eval(parse("(save reptest)"))
    assert isinstance(save_res, SaveResult)
    assert "reptest" in save_res.path

    # (saves) lists it.
    saves_res = repl.eval(parse("(saves)"))
    assert isinstance(saves_res, SavesResult)
    assert any(slot == "reptest" for slot, _ts, _p in saves_res.saves)

    # A fresh runtime/REPL restores via (load reptest).
    rt2 = _runtime()
    repl2 = ReplEvaluator(rt2)
    assert rt2.state.objects["COIN"].location == "LOBBY"
    load_res = repl2.eval(parse("(load reptest)"))
    assert isinstance(load_res, LoadResult)
    assert rt2.state.objects["COIN"].location == "VAULT"


def test_repl_load_missing_reports_error():
    from grue.expr import EvalError

    repl = ReplEvaluator(_runtime())
    with pytest.raises(EvalError):
        repl.eval(parse("(load nope)"))
