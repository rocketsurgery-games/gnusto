"""Tests for the renderable-asset catalog fed to the LLM (gnusto-4ac5.5).

The catalog grounds the LLM's reveal/focus/splash entity references in what is
ACTUALLY renderable, so it surfaces real art instead of guessing.
"""

from types import SimpleNamespace

import gnusto.agent as agent
from gnusto.agent import GameSession


def _fake_session():
    """A minimal stand-in carrying just what _renderable_catalog reads."""
    return SimpleNamespace(runtime=object(), game_dir=None)


def test_catalog_lists_only_entities_with_art(monkeypatch):
    monkeypatch.setattr(
        agent,
        "build_scene_context",
        lambda state, runtime, game_dir: {
            "@room": {"name": "Lab", "image": "/assets/lab.jpg"},
            "@hacker": {"name": "the hacker", "image": "/assets/hacker.jpg"},
            "@ghost": {"name": "a ghost", "image": None},  # no art -> excluded
        },
    )
    state = SimpleNamespace(room="@room")
    catalog = GameSession._renderable_catalog(_fake_session(), state)
    # room is excluded (auto-established); art-less entity excluded
    assert "@hacker (the hacker)" in catalog
    assert "@room" not in catalog
    assert "@ghost" not in catalog


def test_catalog_empty_when_no_art(monkeypatch):
    monkeypatch.setattr(
        agent,
        "build_scene_context",
        lambda state, runtime, game_dir: {
            "@x": {"name": "x", "image": None},
        },
    )
    state = SimpleNamespace(room="@room")
    assert GameSession._renderable_catalog(_fake_session(), state) == ""


def test_catalog_survives_scene_context_error(monkeypatch):
    def boom(state, runtime, game_dir):
        raise RuntimeError("no runtime")

    monkeypatch.setattr(agent, "build_scene_context", boom)
    state = SimpleNamespace(room="@room")
    assert GameSession._renderable_catalog(_fake_session(), state) == ""
