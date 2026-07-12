"""Tests for static game-logic lints (grue.lint).

Regression net for the event-queue footgun behind the `compulsion` bug
(gnusto-f95a.1 / gnusto-aab0 / gnusto-3306.1): a self-advancing counter event
queued only finitely that forgets to re-queue itself fires once, leaving later
stages unreachable.
"""

from pathlib import Path

from grue.lint import lint_events, lint_property_writes, lint_world
from grue.parser import load_grue, parse_grue

# A minimal self-advancing counter event, in three variants.
_BROKEN = """
(world :name "t" :player @p)
(room @r :description "R")
(object @p :location @r :properties (:comp-cnt 0))
(object @paper :location @r
  :behaviors (:read (fn () '((queue compulsion 2) (success)))))
(event compulsion :location @r
  :on-turn (condp = (:comp-cnt @p)
    0 `((set @p :comp-cnt 1) (narrate "page1") (success))
    1 `((set @p :comp-cnt 2) (narrate "page2") (success))
    `((dequeue compulsion) (success))))
"""

# Fixed by re-queuing in the advancing branches (the chain idiom).
_FIXED = _BROKEN.replace(
    '(set @p :comp-cnt 1) (narrate "page1")',
    '(set @p :comp-cnt 1) (queue compulsion 1) (narrate "page1")',
).replace(
    '(set @p :comp-cnt 2) (narrate "page2")',
    '(set @p :comp-cnt 2) (queue compulsion 1) (narrate "page2")',
)

# Fixed by queuing indefinitely (fires every turn until it dequeues itself).
_INDEFINITE = _BROKEN.replace("(queue compulsion 2)", "(queue compulsion)")


def test_flags_finite_counter_event_without_requeue():
    errors = lint_events(parse_grue(_BROKEN))
    assert len(errors) == 1
    assert errors[0].entity == "compulsion"
    assert "fires once" in errors[0].message


def test_self_requeue_clears_the_warning():
    assert lint_events(parse_grue(_FIXED)) == []


def test_indefinite_queue_clears_the_warning():
    assert lint_events(parse_grue(_INDEFINITE)) == []


# --- undeclared property writes (gnusto-3306.4) ---------------------------

# An event writing a literal @entity property it never declared (the class of
# bug behind the endgame hacker-returns crash, gnusto-4d05), plus a behavior
# writing an undeclared property on ?self.
_BAD_WRITES = """
(world :name "t" :player @p)
(room @r :description "R")
(object @p :location @r :properties (:comp-cnt 0))
(object @npc :location @r :properties (:person true))
(object @door :location @r :properties (:openable true)
  :behaviors (:kick (fn () '((set ?self :dented true) (success)))))
(event surprise :location @r
  :on-turn '((set @npc :invisible true) (success)))
"""


def test_flags_undeclared_literal_and_self_writes():
    errors = lint_property_writes(parse_grue(_BAD_WRITES))
    flagged = {(e.entity, e.message.split("(:")[1].split(" ")[0]) for e in errors}
    assert ("@npc", "invisible") in flagged  # literal @entity in an event
    assert ("@door", "dented") in flagged  # ?self in a behavior
    assert all(e.severity == "error" for e in errors)


def test_declared_and_implied_properties_are_clean():
    src = """
    (world :name "t" :player @p)
    (room @r :description "R")
    (object @p :location @r)
    ; :dented declared; :open is IMPLIED by :openable
    (object @door :location @r :properties (:openable true :dented false)
      :behaviors (:kick (fn () '((set ?self :dented true) (set ?self :open true) (success)))))
    """
    assert lint_property_writes(parse_grue(src)) == []


def test_unresolvable_targets_are_skipped():
    # A write to ?actor (not statically bound) can't be verified, so no flag.
    src = """
    (world :name "t" :player @p)
    (room @r :description "R")
    (object @p :location @r)
    (object @thing :location @r
      :behaviors (:zap (fn () '((set ?actor :zapped true) (success)))))
    """
    assert lint_property_writes(parse_grue(src)) == []


def test_lurking_horror_is_lint_clean():
    """The shipped conversion must stay lint-clean, so a re-introduced dropped
    chain (like the original `compulsion` bug) fails CI here."""
    path = Path(__file__).parent.parent.parent / "games" / "lurkinghorror"
    errors = lint_world(load_grue(path))
    assert errors == [], "\n".join(str(e) for e in errors)
