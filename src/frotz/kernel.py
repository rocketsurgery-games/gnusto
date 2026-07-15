"""Reference kernel for state-graph analysis.

A first-principles restart (see docs/design/state-graph-kernel.md). This is the
*ground truth*: a concrete, fully-unabstracted breadth-first enumeration of a
game's reachable state graph. It is deliberately tiny so that its correctness is
self-evident, and it is the ORACLE against which every later abstraction
(cone-of-influence projection, value-domain / numeric-interval abstraction, the
reversibility quotient) is differential-tested — an abstraction is sound iff, on
every game small enough to enumerate concretely, it agrees with this kernel on
the property in question (reachability of the goal).

It does not scale, and is not meant to. Scaling is the job of the abstraction
layers built on top, each with its own soundness obligation.

## The transition system (the formal object)

A game is a deterministic labeled transition system (S, A, ->, s0, phi):

- S  — concrete states: a total assignment to every state variable (each
       object's location and properties, and every event-queue countdown).
       Finite, because every variable has a finite domain.
- A  — actions: (target, verb, args) the player/engine can invoke.
- -> — the transition function `step`, given by the runtime's *pure* effect
       interpreter: dispatch the behavior, apply its effect list. Deterministic
       because effects are pure and randomness has been removed.
- s0 — the initial state (`runtime.reset()`).
- phi— the goal predicate (the world victory condition, or a supplied target).

Reachability of phi is decidable here by construction (finite S, deterministic
->): BFS terminates and is both sound and complete. That is the whole point —
this is the definition the abstractions must preserve.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

from grue import GrueWorld
from grue.runtime import GrueRuntime, GameState


# A canonical concrete state: the frozenset of (variable-key, value) pairs over
# the state variables. Two states are equal iff every tracked variable agrees —
# so the visited-set dedup here is exact (identity), never a lossy fingerprint.
Fingerprint = frozenset

# Engine bookkeeping properties excluded from the fingerprint. These are written
# by the runtime on every successful action (the move/turn counter, score) but
# are pure output — no behavior guard branches on them and no goal we analyze
# reads them. Including them makes the "fully concrete" state space INFINITE (the
# move counter grows without bound), so even the reference kernel must apply this
# one, obviously-sound projection to be finite at all. It is the degenerate case
# of cone-of-influence reduction (drop variables no guard/goal reads); the
# general, computed version is the first real abstraction layer built on top.
BOOKKEEPING_PROPS = frozenset({"moves", "score"})


def _hashable(v: Any) -> Any:
    if isinstance(v, list):
        return tuple(_hashable(x) for x in v)
    if isinstance(v, dict):
        return tuple(sorted((k, _hashable(x)) for k, x in v.items()))
    return v


def fingerprint(
    rt: GrueRuntime, ignore_props: frozenset[str] = BOOKKEEPING_PROPS
) -> Fingerprint:
    """The concrete state as a hashable value, minus engine bookkeeping."""
    items: list[tuple] = []
    for name, obj in rt.state.objects.items():
        items.append((("loc", name), obj.location))
        for prop, val in obj.properties.items():
            if prop in ignore_props:
                continue
            items.append((("prop", name, prop), _hashable(val)))
    for event, countdown in rt.state.queues.items():
        items.append((("queue", event), countdown))
    return frozenset(items)


@dataclass(frozen=True)
class Action:
    target: str
    verb: str
    args: tuple = ()

    def __str__(self) -> str:
        a = " " + " ".join(str(x) for x in self.args) if self.args else ""
        return f"{self.verb} {self.target}{a}".strip()


# Verbs that never denote a player-invokable action (engine-internal).
_INTERNAL_VERBS = frozenset({"through", "describe", "fdesc", "on-enter", "on-exit"})


def enumerate_actions(rt: GrueRuntime) -> list[Action]:
    """A sound *superset* of the actions available in the current state.

    Completeness obligation: this must include every action that could succeed,
    so BFS misses no reachable state. Over-approximating is safe — spurious
    actions simply come back blocked and add no edge. We therefore enumerate
    generously: every exit direction, every declared behavior verb on every
    in-scope object (with every in-scope object as a candidate argument), and the
    runtime defaults take/drop/put.
    """
    actions: list[Action] = []
    room = rt.get_player_room()
    scope = sorted(set(rt.get_visible_objects(for_description=False)) | set(rt.get_inventory()))

    # Movement: one action per real exit.
    if room in rt.world.rooms:
        for ex in rt.world.rooms[room].exits:
            if ex.to is not None:
                actions.append(Action(target=ex.to, verb="go", args=(ex.direction,)))

    # Declared behaviors on in-scope objects.
    for name in scope:
        obj = rt.world.objects.get(name)
        if obj is None or not getattr(obj, "behaviors", None):
            continue
        for beh in obj.behaviors:
            if beh.verb in _INTERNAL_VERBS:
                continue
            if not beh.params:
                actions.append(Action(target=name, verb=beh.verb))
            else:
                for arg in scope:
                    actions.append(Action(target=name, verb=beh.verb, args=(arg,)))

    # Runtime default actions on takeable objects. `put` targets only genuine
    # containers/surfaces (matching the effect model's put footprint); allowing
    # put into arbitrary objects manufactures a combinatorial blowup of bogus
    # nesting states that no real action produces.
    containers = sorted(
        n
        for n in scope
        if (o := rt.world.objects.get(n)) is not None
        and (o.properties.get("container") or o.properties.get("surface"))
    )
    for name in scope:
        obj = rt.world.objects.get(name)
        if obj is None or not obj.properties.get("takeable"):
            continue
        actions.append(Action(target=name, verb="take"))
        actions.append(Action(target=name, verb="drop"))
        for dest in containers:
            if dest != name:
                actions.append(Action(target=name, verb="put", args=(dest,)))

    actions.append(Action(target="_wait", verb="wait"))
    return actions


def step(
    rt: GrueRuntime, snapshot: GameState, action: Action
) -> GameState | None:
    """Apply `action` to `snapshot`; return the successor state, or None if the
    action didn't succeed (blocked/error). Pure: `snapshot` is not mutated."""
    rt.state = snapshot.copy()
    if action.verb == "wait":
        rt.process_events()
        return rt.state
    result = rt.do(action.target, action.verb, *action.args)
    if result.outcome != "success":
        return None
    rt.process_events()
    return rt.state


@dataclass
class StateGraph:
    fingerprints: dict[Fingerprint, int] = field(default_factory=dict)
    edges: list[tuple[int, Action, int]] = field(default_factory=list)
    goal_ids: set[int] = field(default_factory=set)
    initial_id: int = 0
    hit_limit: bool = False

    @property
    def num_states(self) -> int:
        return len(self.fingerprints)

    def goal_reachable(self) -> bool:
        return bool(self.goal_ids)


def explore(
    world: GrueWorld,
    goal: Callable[[GrueRuntime], bool] | None = None,
    max_states: int = 100_000,
) -> StateGraph:
    """Enumerate the concrete reachable state graph by BFS.

    `goal` defaults to the world's victory condition. Sound and complete for the
    concrete semantics up to `max_states` (past which `hit_limit` is set — the
    honest signal that this game is beyond the concrete kernel and needs the
    abstraction layers).
    """
    rt = GrueRuntime(world)
    rt.reset()

    def is_goal() -> bool:
        if goal is not None:
            return goal(rt)
        return rt.check_victory()

    graph = StateGraph()
    snaps: dict[int, GameState] = {}

    fp0 = fingerprint(rt)
    graph.fingerprints[fp0] = 0
    snaps[0] = rt.state.copy()
    if is_goal():
        graph.goal_ids.add(0)

    queue: deque[int] = deque([0])
    while queue:
        sid = queue.popleft()
        snap = snaps[sid]
        for action in enumerate_actions_from(rt, snap):
            succ = step(rt, snap, action)
            if succ is None:
                continue
            fp = fingerprint(rt)  # rt.state == succ after step
            if fp in graph.fingerprints:
                graph.edges.append((sid, action, graph.fingerprints[fp]))
                continue
            nid = len(graph.fingerprints)
            graph.fingerprints[fp] = nid
            snaps[nid] = succ.copy()
            graph.edges.append((sid, action, nid))
            if is_goal():
                graph.goal_ids.add(nid)
            if len(graph.fingerprints) >= max_states:
                graph.hit_limit = True
                return graph
            queue.append(nid)
    return graph


def enumerate_actions_from(rt: GrueRuntime, snapshot: GameState) -> list[Action]:
    """Enumerate actions as seen from `snapshot` (restores state first)."""
    rt.state = snapshot.copy()
    return enumerate_actions(rt)
