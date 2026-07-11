"""Static lints for Grue *game logic* (distinct from render specs, which have
their own linter in ``render.lint_render``).

The first check targets the event-queue footgun that caused the ``compulsion``
bug (yak gnusto-f95a.1 / gnusto-3306.1): a multi-stage event that dispatches on
a counter it advances, but is only ever queued with a finite countdown and never
re-queues itself. Under the ZIL-faithful one-shot contract (gnusto-aab0) such an
event fires exactly once, leaving its later stages unreachable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from .sexpr import Keyword, SExpr, SList, Symbol


@dataclass(frozen=True)
class LintError:
    """A static game-logic violation."""

    entity: str
    message: str
    severity: str = "warning"  # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.entity}: {self.message}"


# --- S-expression helpers ---------------------------------------------------


def _walk(node: SExpr | None) -> Iterator[SExpr]:
    """Yield ``node`` and every descendant S-expression (pre-order)."""
    if node is None:
        return
    yield node
    if isinstance(node, SList):
        for item in node.items:
            yield from _walk(item)


def _head(node: SExpr) -> str | None:
    """The head symbol name of a form, or None if not a symbol-headed list."""
    if isinstance(node, SList) and node.items and isinstance(node.items[0], Symbol):
        return node.items[0].name
    return None


def _key_name(node: SExpr) -> str | None:
    """Name of a Keyword or Symbol node (without the leading ``:``), else None."""
    if isinstance(node, Keyword):
        return node.name
    if isinstance(node, Symbol):
        return node.name
    return None


def _all_bodies(world: Any) -> Iterator[SExpr]:
    """Yield every code-bearing S-expression in the world (rooms, objects,
    events, defaults, functions, victory/defeat conditions)."""
    def entity_bodies(e: Any) -> Iterator[SExpr]:
        for attr in ("description", "ldesc", "render"):
            val = getattr(e, attr, None)
            if val is not None:
                yield val
        for b in getattr(e, "behaviors", []) or []:
            if b.body is not None:
                yield b.body
        for nf in getattr(e, "nested_forms", []) or []:
            yield nf
        for ex in getattr(e, "exits", []) or []:
            if getattr(ex, "when", None) is not None:
                yield ex.when

    for room in getattr(world, "rooms", {}).values():
        yield from entity_bodies(room)
    for obj in getattr(world, "objects", {}).values():
        yield from entity_bodies(obj)
    for event in getattr(world, "events", {}).values():
        if event.body is not None:
            yield event.body
        for nf in getattr(event, "nested_forms", []) or []:
            yield nf
    for beh in getattr(world, "defaults", {}).values():
        if beh.body is not None:
            yield beh.body
    for fn in getattr(world, "functions", {}).values():
        if getattr(fn, "body", None) is not None:
            yield fn.body
    victory = getattr(world, "victory", None)
    if victory is not None and getattr(victory, "when", None) is not None:
        yield victory.when
    for d in getattr(world, "defeat", {}).values():
        if getattr(d, "when", None) is not None:
            yield d.when


def _queue_countdowns(event_name: str, bodies: Iterator[SExpr]) -> list[SExpr | None]:
    """Every countdown a ``(queue <event_name> [countdown])`` is called with.
    A missing countdown is recorded as ``None`` (indefinite)."""
    found: list[SExpr | None] = []
    for body in bodies:
        for node in _walk(body):
            if (
                isinstance(node, SList)
                and _head(node) == "queue"
                and len(node.items) >= 2
                and _key_name(node.items[1]) == event_name
            ):
                found.append(node.items[2] if len(node.items) >= 3 else None)
    return found


def _self_requeues(event_name: str, body: SExpr | None) -> bool:
    """Does the event body contain a ``(queue <self> ...)``?"""
    for node in _walk(body):
        if (
            isinstance(node, SList)
            and _head(node) == "queue"
            and len(node.items) >= 2
            and _key_name(node.items[1]) == event_name
        ):
            return True
    return False


def _counter_dispatch(body: SExpr | None) -> tuple[str, str] | None:
    """If ``body`` is ``(condp = (:prop @ent) ...)`` — the self-advancing
    multi-stage counter idiom — return ``(entity, prop)``, else None."""
    if not isinstance(body, SList) or _head(body) != "condp" or len(body.items) < 3:
        return None
    pred, dispatch = body.items[1], body.items[2]
    if not (isinstance(pred, Symbol) and pred.name == "="):
        return None
    # dispatch is a property read like (:prop @ent)
    if (
        isinstance(dispatch, SList)
        and len(dispatch.items) == 2
        and isinstance(dispatch.items[0], Keyword)
    ):
        prop = dispatch.items[0].name
        ent = _key_name(dispatch.items[1])
        if ent is not None:
            return ent, prop
    return None


def _mutates_prop(body: SExpr | None, entity: str, prop: str) -> bool:
    """Does the body set/inc/dec ``(:prop entity)`` — i.e. advance the counter?"""
    for node in _walk(body):
        if not isinstance(node, SList) or len(node.items) < 3:
            continue
        head = _head(node)
        if head not in ("set", "set-prop", "inc", "dec"):
            continue
        if _key_name(node.items[1]) == entity and _key_name(node.items[2]) == prop:
            return True
    return False


def _is_indefinite(countdown: SExpr | None) -> bool:
    """A queue countdown is indefinite if omitted (None) or negative (ZIL -1)."""
    if countdown is None:
        return True
    if isinstance(countdown, int):
        return countdown < 0
    # Non-literal (computed) countdown: treat as unknown -> not provably finite.
    return True


# --- Lints ------------------------------------------------------------------


def lint_events(world: Any) -> list[LintError]:
    """Flag self-advancing counter events that can only fire once.

    An event is flagged when ALL of:
      * its ``:on-turn`` body dispatches via ``(condp = (:prop @ent) ...)`` and
        advances that same ``(:prop @ent)`` in a branch (a staged machine);
      * every static ``(queue <event> N)`` site uses a finite, non-negative
        countdown (never indefinite ``nil``/negative), and at least one exists;
      * the body never re-queues itself.

    Under the one-shot queue contract this event fires once and its later stages
    are unreachable — almost always a dropped chain (see the ``compulsion`` bug).
    Fix by re-queuing in the advancing branches (``(queue X 1)``) or, if it truly
    should run every turn, queue it indefinitely (``(queue X)``).
    """
    errors: list[LintError] = []
    for name, event in getattr(world, "events", {}).items():
        dispatch = _counter_dispatch(event.body)
        if dispatch is None:
            continue
        ent, prop = dispatch
        if not _mutates_prop(event.body, ent, prop):
            continue  # dispatches on a counter but doesn't advance it — not our case
        countdowns = _queue_countdowns(name, _all_bodies(world))
        if not countdowns or any(_is_indefinite(cd) for cd in countdowns):
            continue  # queued indefinitely (or never queued statically) — fine
        if _self_requeues(name, event.body):
            continue  # a proper chain
        errors.append(
            LintError(
                name,
                f"event dispatches on and advances (:{prop} {ent}) across stages "
                f"but is only queued with a finite countdown and never re-queues "
                f"itself; under the one-shot queue contract it fires once, leaving "
                f"later stages unreachable. Re-queue it in its advancing branches "
                f"(e.g. (queue {name} 1)), or queue it indefinitely (queue {name}).",
            )
        )
    return errors


def lint_world(world: Any) -> list[LintError]:
    """Run all game-logic lints. (Render specs: see render.lint_render.)"""
    return list(lint_events(world))
