"""Differential-test harness + corpus (comparison mode A: multi-goal reachability).

Three things are asserted here:

1. **Anchors** — the kernel's answer key matches the hand-verified facts on every
   corpus game (pins the concrete truth independently of the kernel, so a kernel
   regression is caught).
2. **Self-differential** — the kernel agrees with itself on every atom of every
   game (validates the harness plumbing and the kernel's determinism).
3. **Teeth** — a deliberately-wrong analysis is *caught*: a false NO is flagged
   unsound; an over-approximation is flagged imprecise-but-sound. Without this,
   "the layer agrees with the kernel" would be an untested claim.
"""

import pytest

from grue import load_grue

from frotz.differential import (
    Analysis,
    Answer,
    Atom,
    DiffResult,
    KernelAnalysis,
    differential,
    kernel_report,
    static_atoms,
    held,
)
from .corpus import CORPUS, MINI, SEALED, CorpusGame


def _load(tmp_path, game: CorpusGame):
    (tmp_path / f"{game.name}.grue").write_text(game.source)
    return load_grue(tmp_path / f"{game.name}.grue")


@pytest.mark.parametrize("game", CORPUS, ids=lambda g: g.name)
def test_kernel_matches_hand_verified_anchors(tmp_path, game: CorpusGame):
    world = _load(tmp_path, game)
    report = kernel_report(game.name, world)
    assert not report.hit_limit, f"{game.name} exceeded the concrete kernel"
    assert report.goal_reachable is game.goal_reachable
    for atom, expected in game.anchors:
        assert report.answers.get(atom) is expected, (
            f"{game.name}: {atom} expected {expected}, "
            f"kernel says {report.answers.get(atom)}"
        )


@pytest.mark.parametrize("game", CORPUS, ids=lambda g: g.name)
def test_self_differential_agrees_everywhere(tmp_path, game: CorpusGame):
    world = _load(tmp_path, game)
    result = differential(game.name, world, KernelAnalysis(), KernelAnalysis())
    assert result.ok, str(result)
    assert result.agreements == result.n_atoms


# --- The harness must catch a wrong layer ------------------------------------


class _Mislabel:
    """A mock analysis: the kernel's answers, with chosen atoms forced to a value.

    Stands in for a buggy abstraction layer so we can prove the differential
    detects it. `force` maps an atom to the (wrong) answer this analysis reports.
    """

    name = "mislabel"

    def __init__(self, force: dict[Atom, "bool | None"]):
        self._force = force
        self._kernel = KernelAnalysis()

    def reachable(self, world, atoms: set[Atom]) -> Answer:
        answer = dict(self._kernel.reachable(world, atoms))
        for atom, val in self._force.items():
            if atom in answer:
                answer[atom] = val
        return answer


def test_harness_flags_a_false_no_as_unsound(tmp_path):
    # Claim a genuinely-reachable atom (the gem, in the solvable Mini) is
    # unreachable — the exact "over-collapsed → lost a state" failure mode.
    world = _load(tmp_path, MINI)
    bad = _Mislabel({held("@gem"): False})
    result = differential("mini", world, KernelAnalysis(), bad)
    assert not result.ok
    assert not result.sound            # a false NO is a soundness violation
    assert any(d.atom == held("@gem") and d.unsound for d in result.disagreements)


def test_harness_flags_over_approximation_as_imprecise_but_sound(tmp_path):
    # Claim an unreachable atom (the gem, behind the never-opening sealed door)
    # IS reachable — an over-approximation: not exact, but not a false NO.
    world = _load(tmp_path, SEALED)
    over = _Mislabel({held("@gem"): True})
    result = differential("sealed", world, KernelAnalysis(), over)
    assert not result.ok               # disagrees on that atom...
    assert result.sound                # ...but commits no false NO
    assert result.unsound == []


def test_static_atoms_has_both_reachable_and_unreachable(tmp_path):
    # Mode A only has teeth if the probe set contains real NOs as well as YESes.
    world = _load(tmp_path, MINI)
    report = kernel_report("mini", world)
    values = set(report.answers.values())
    assert True in values and False in values
    assert len(static_atoms(world)) == len(report.answers)
