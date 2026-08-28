"""Differential-test harness: kernel vs. an abstraction layer (comparison mode A).

The methodology (docs/design/state-graph-kernel.md §5): every abstraction layer
must, on games small enough to enumerate concretely, agree with the concrete
reference kernel (frotz.kernel) on the property in question. This module is the
machinery that checks that agreement.

**Comparison mode A = multi-goal reachability.** Instead of probing a single
victory goal, we derive a whole *set* of candidate goal atoms from the game —
every object-location and every boolean-property assignment (`static_atoms`) —
and ask, for each, "is a state satisfying this atom reachable?" The kernel's
answers form the **answer key**; a layer is sound-and-exact iff it reproduces
that key. Probing many atoms (not just victory) is what catches an abstraction
that over-collapses non-bisimilar states: some probed atom will separate them
even when victory doesn't. (The still-stronger structural check — bisimulation —
is mode B, deferred to gnusto-266.5.3.)

An `Analysis` is any object that, given a world and a set of atoms, labels each
`True` (reachable), `False` (provably unreachable), or `None` (unknown — its
search was incomplete). The kernel is one such analysis; future layers are
others. `differential` runs two analyses over the same atoms and reports where
they differ, distinguishing a *soundness violation* (the fatal kind: the
candidate says unreachable where the reference says reachable — a false NO) from
mere *imprecision* (the candidate over-approximates: reachable where the
reference says not — allowed for an over-approximating layer).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from grue import GrueWorld

from frotz.kernel import StateGraph, explore


# === Goal atoms ===============================================================


@dataclass(frozen=True)
class Atom:
    """A single-variable goal predicate: one state variable equals one value.

    ``kind="loc"``  → object ``obj`` is located at ``value`` (a room, ``@player``
                      for held, a container, or ``None`` for limbo).
    ``kind="prop"`` → object ``obj``'s property ``slot`` equals ``value``.
    """

    kind: str
    obj: str
    slot: str | None
    value: Any

    def __str__(self) -> str:
        if self.kind == "loc":
            if self.value == "@player":
                return f"held?({self.obj})"
            return f"loc({self.obj})={_fmt(self.value)}"
        return f":{self.slot}({self.obj})={_fmt(self.value)}"


def _fmt(v: Any) -> str:
    if v is None:
        return "nil"
    if v is True:
        return "true"
    if v is False:
        return "false"
    return str(v)


# Convenience constructors (used by the corpus to state expected facts).
def held(obj: str) -> Atom:
    return Atom("loc", obj, None, "@player")


def loc(obj: str, dest: str | None) -> Atom:
    return Atom("loc", obj, None, dest)


def prop(obj: str, slot: str, value: Any) -> Atom:
    return Atom("prop", obj, slot, value)


def atoms_in_state(fp: frozenset) -> set[Atom]:
    """The goal atoms true in one concrete state (a kernel fingerprint).

    The fingerprint is exactly the frozenset of ``(key, value)`` pairs the kernel
    tracks; we translate its ``loc``/``prop`` keys into `Atom`s (queue entries
    are not goal atoms and are skipped). So an atom is reachable iff it appears in
    *some* reached fingerprint — the whole answer-key computation is one BFS plus
    set membership.
    """
    out: set[Atom] = set()
    for key, val in fp:
        if key[0] == "loc":
            out.add(Atom("loc", key[1], None, val))
        elif key[0] == "prop":
            out.add(Atom("prop", key[1], key[2], val))
    return out


def static_atoms(world: GrueWorld) -> set[Atom]:
    """The candidate goal atoms probed for a world — derived statically.

    Locations: every object at every plausible destination (rooms, ``@player``,
    every container/surface, and limbo); the player at every room. Properties:
    every declared boolean property at both ``true`` and ``false``. This is a
    finite probe set that deliberately contains both reachable and unreachable
    atoms (e.g. a room the player can't get to, a flag that never flips), so the
    differential has real NO answers to check, not only YESes.

    Restricted to ``world.objects`` (the entities the kernel fingerprints); room
    properties aren't tracked in runtime state, so they're not probed here.
    Numeric/enum property domains are out of scope for mode A (they're the
    concern of the value-domain layer, 4.2) — only booleans are enumerated.
    """
    atoms: set[Atom] = set()
    rooms = set(world.rooms)
    containers = {
        n
        for n, o in world.objects.items()
        if o.properties.get("container") or o.properties.get("surface")
    }
    dests: set[str | None] = rooms | {"@player"} | containers | {None}
    player = world.player or "@player"

    for name in world.objects:
        if name == player:
            for r in rooms:
                atoms.add(Atom("loc", name, None, r))
            continue
        for d in dests:
            if d != name:
                atoms.add(Atom("loc", name, None, d))

    for name, obj in world.objects.items():
        for slot, val in obj.properties.items():
            if isinstance(val, bool):
                atoms.add(Atom("prop", name, slot, True))
                atoms.add(Atom("prop", name, slot, False))

    return atoms


# === Analyses =================================================================

# An answer maps each probed atom to True (reachable), False (provably not), or
# None (unknown — the analysis didn't finish).
Answer = dict[Atom, "bool | None"]


@runtime_checkable
class Analysis(Protocol):
    name: str

    def reachable(self, world: GrueWorld, atoms: set[Atom]) -> Answer: ...


def kernel_answers(
    world: GrueWorld, atoms: set[Atom], max_states: int = 100_000
) -> tuple[StateGraph, Answer]:
    """Run the concrete kernel and label every atom by reachability.

    An atom observed in some reached state is ``True``. If the BFS hit its cap
    (``hit_limit``), an *unobserved* atom is ``None`` (we can't claim it's
    unreachable from an incomplete search) — soundness stays honest. Only when
    the search ran to a fixpoint is an unobserved atom ``False``.
    """
    graph = explore(world, max_states=max_states)
    observed: set[Atom] = set()
    for fp in graph.fingerprints:
        observed |= atoms_in_state(fp)
    answer: Answer = {}
    for a in atoms:
        if a in observed:
            answer[a] = True
        elif graph.hit_limit:
            answer[a] = None
        else:
            answer[a] = False
    return graph, answer


@dataclass
class KernelAnalysis:
    """The reference analysis: the concrete kernel itself."""

    name: str = "kernel"
    max_states: int = 100_000

    def reachable(self, world: GrueWorld, atoms: set[Atom]) -> Answer:
        _, answer = kernel_answers(world, atoms, self.max_states)
        return answer


# === Reports ==================================================================


@dataclass
class GameReport:
    name: str
    num_states: int
    hit_limit: bool
    goal_reachable: bool
    answers: Answer


def kernel_report(name: str, world: GrueWorld, max_states: int = 100_000) -> GameReport:
    graph, answers = kernel_answers(world, static_atoms(world), max_states)
    return GameReport(
        name=name,
        num_states=graph.num_states,
        hit_limit=graph.hit_limit,
        goal_reachable=graph.goal_reachable(),
        answers=answers,
    )


def render_answer_key(rep: GameReport, max_atoms: int = 40) -> str:
    """A human-readable dump of one game's kernel answer key."""
    lines: list[str] = []
    goal = "REACHABLE" if rep.goal_reachable else "UNREACHABLE"
    cap = " (hit_limit)" if rep.hit_limit else ""
    lines.append(f"=== {rep.name} ===")
    lines.append(f"    states={rep.num_states}{cap}   victory={goal}")
    yes = sorted((a for a, v in rep.answers.items() if v is True), key=str)
    no = sorted((a for a, v in rep.answers.items() if v is False), key=str)
    unk = sorted((a for a, v in rep.answers.items() if v is None), key=str)
    lines.append(f"    atoms={len(rep.answers)}  (reachable={len(yes)} "
                 f"unreachable={len(no)} unknown={len(unk)})")

    def _block(label: str, atoms: list[Atom]) -> None:
        shown = atoms[:max_atoms]
        for a in shown:
            lines.append(f"      {label} {a}")
        if len(atoms) > len(shown):
            lines.append(f"      {label} ... (+{len(atoms) - len(shown)} more)")

    _block("YES", yes)
    _block(" NO", no)
    _block("  ?", unk)
    return "\n".join(lines)


# === Differential =============================================================


@dataclass(frozen=True)
class Disagreement:
    atom: Atom
    ref: bool | None
    cand: bool | None

    @property
    def unsound(self) -> bool:
        """A false NO: the candidate calls unreachable what the reference (the
        oracle) reached. This is the fatal class — the candidate *lost* a real
        state. (ref True, cand False.)"""
        return self.ref is True and self.cand is False

    def __str__(self) -> str:
        kind = "UNSOUND" if self.unsound else "imprecise"
        return f"[{kind}] {self.atom}: ref={_fmt(self.ref)} cand={_fmt(self.cand)}"


@dataclass
class DiffResult:
    game: str
    n_atoms: int
    disagreements: list[Disagreement]

    @property
    def agreements(self) -> int:
        return self.n_atoms - len(self.disagreements)

    @property
    def unsound(self) -> list[Disagreement]:
        return [d for d in self.disagreements if d.unsound]

    @property
    def ok(self) -> bool:
        return not self.disagreements

    @property
    def sound(self) -> bool:
        """Sound even if imprecise: no false NOs."""
        return not self.unsound

    def __str__(self) -> str:
        head = (
            f"{self.game}: {self.agreements}/{self.n_atoms} agree"
            f"  ({len(self.unsound)} unsound, "
            f"{len(self.disagreements) - len(self.unsound)} imprecise)"
        )
        body = "\n".join(f"    {d}" for d in sorted(self.disagreements, key=lambda d: str(d.atom)))
        return head + ("\n" + body if body else "")


def differential(
    name: str, world: GrueWorld, ref: Analysis, cand: Analysis
) -> DiffResult:
    """Compare a candidate analysis against a reference over one game's atoms.

    The reference is normally the kernel. A disagreement where the reference
    reached an atom the candidate calls unreachable is a *soundness violation*
    (false NO); the reverse is mere imprecision. `None`/unknown answers agree
    with anything only when equal.
    """
    atoms = static_atoms(world)
    ref_ans = ref.reachable(world, atoms)
    cand_ans = cand.reachable(world, atoms)
    dis: list[Disagreement] = []
    for a in atoms:
        r, c = ref_ans[a], cand_ans[a]
        if r != c:
            dis.append(Disagreement(a, r, c))
    return DiffResult(name, len(atoms), dis)
