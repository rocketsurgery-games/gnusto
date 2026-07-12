"""Runtime error robustness (gnusto-160b).

Engine errors (undeclared property write, uncaught exception, redirect loop)
must (1) never leave partial state and (2) never be silently swallowed. These
tests pin both at the runtime and test-harness levels.
"""

from grue import GrueRuntime, parse_grue
from grue.test.dsl import TestRunner as _TestRunner
from grue.sexpr import parse


def _runtime(src):
    return GrueRuntime(parse_grue(src))


# An event whose effect list applies one write, then errors on an undeclared one.
_ATOMIC_SRC = """
(world :name "t" :player @p)
(room @r :description "R")
(object @p :location @r)
(object @x :location @r :properties (:count 0))
(event boom :location @r
  :on-turn '((set @x :count 5) (set @x :nope 9) (success)))
"""


def test_effect_error_is_atomic():
    rt = _runtime(_ATOMIC_SRC)
    rt.state.queues["boom"] = None
    results = rt.process_events()
    assert results[0].outcome == "error"
    # The earlier (set @x :count 5) must be rolled back, not committed.
    assert rt.state.objects["@x"].properties["count"] == 0


def test_action_error_is_atomic():
    src = """
    (world :name "t" :player @p)
    (room @r :description "R")
    (object @p :location @r)
    (object @lever :location @r :properties (:pulled false)
      :behaviors (:pull (fn () '((set ?self :pulled true) (set ?self :sparks 1) (success)))))
    """
    rt = _runtime(src)
    result = rt.do("@lever", "pull")
    assert result.outcome == "error"
    # :pulled must not be left committed after the undeclared :sparks write failed.
    assert rt.state.objects["@lever"].properties["pulled"] is False


def test_errored_event_fails_the_test_harness():
    """A fired event that errors must fail the test, not pass silently."""
    world = parse_grue(_ATOMIC_SRC)
    runner = _TestRunner(world)
    # Queue the event, then wait a turn so it fires; then a trivially-true assert.
    test = parse(
        '(test "should-fail-on-engine-error" '
        "(queue boom) (wait) (assert (loc? @p @r)))"
    )
    result = runner.run_test(test)
    assert not result.passed
    assert any("engine error" in f for f in result.failures)
