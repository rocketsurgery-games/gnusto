"""The reference kernel, proven on the hand-enumerable Mini game.

These assertions are the anchor for every future abstraction: an abstraction is
sound iff it agrees with this concrete oracle on goal-reachability for games
small enough to enumerate.

Games are loaded via ``load_grue`` (not bare ``parse_grue``) so the runtime's
default behaviors from builtins.grue — take/drop/put/go — are present, exactly as
in real play.
"""

from grue import load_grue
from grue.runtime import GrueRuntime
from frotz.kernel import explore, fingerprint, enumerate_actions


MINI = """
(world :name "Mini" :player @player)
(victory :when (held? @gem))
(room @cell :description "Cell" :properties (:lit true)
  :exits ((east :to @hall :via @door)))
(room @hall :description "Hall" :properties (:lit true)
  :exits ((west :to @cell :via @door)))
(object @player :location @cell)
(object @key :location @cell :properties (:takeable true))
(object @gem :location @hall :properties (:takeable true))
(object @door :location @cell :properties (:openable true :open false)
  :behaviors (
    :through (fn () (if (:open @door) (success)
                        (blocked :reason closed :message "shut")))
    :open (fn ()
      (cond
        ((:open @door) (blocked :reason already-open :message "open"))
        (SOLVE)
        (true (blocked :reason locked :message "locked"))))))
"""

SOLVABLE = MINI.replace(
    "(SOLVE)", "((held? @key) '((set @door :open true) (success)))"
)
SEALED = MINI.replace("(SOLVE)", "")  # no way to open the door


def _load(tmp_path, source):
    (tmp_path / "g.grue").write_text(source)
    return load_grue(tmp_path / "g.grue")


def test_mini_goal_is_reachable(tmp_path):
    graph = explore(_load(tmp_path, SOLVABLE))
    assert not graph.hit_limit
    assert graph.goal_reachable()


def test_mini_is_small_and_finite(tmp_path):
    # Finite only because engine bookkeeping (the move counter) is projected out;
    # otherwise the state space is infinite. See kernel.BOOKKEEPING_PROPS.
    graph = explore(_load(tmp_path, SOLVABLE))
    assert not graph.hit_limit
    assert 4 <= graph.num_states <= 64  # 20 in practice


def test_permanently_locked_door_blocks_goal(tmp_path):
    # The door can never open, so the gem behind it is genuinely unreachable —
    # the oracle must say NO, not a false YES.
    graph = explore(_load(tmp_path, SEALED))
    assert not graph.goal_reachable()


def test_fingerprint_excludes_bookkeeping_and_is_exact(tmp_path):
    rt = GrueRuntime(_load(tmp_path, SOLVABLE))
    rt.reset()
    fp1 = fingerprint(rt)
    # Bumping the move counter must NOT change the fingerprint...
    rt.state.objects["@player"].properties["moves"] = 999
    assert fingerprint(rt) == fp1
    # ...but moving the key must.
    rt.state.objects["@key"].location = "@player"
    assert fingerprint(rt) != fp1


def test_enumerate_actions_is_nonempty_superset(tmp_path):
    rt = GrueRuntime(_load(tmp_path, SOLVABLE))
    rt.reset()
    acts = {str(a) for a in enumerate_actions(rt)}
    assert any(a.startswith("go ") for a in acts)
    assert "take @key" in acts
    assert "open @door" in acts


# --- Oracle-honesty: value-argument and multi-argument enumeration ---
#
# enumerate_actions claims to be a sound *superset* (never omit an action that
# could succeed). Two gaps used to violate that: value arguments (drawn from
# neither scope nor anywhere) and multi-arg behaviors (only one arg supplied).
# Both would make the oracle report a false NO. See gnusto-266.5.1.

# A safe opened by entering the right combination. The winning value "4271"
# never appears in object scope; it is only enumerable because it is a literal in
# the guard. Pre-fix the kernel could not generate `enter-code @safe 4271` and
# so reported the goal unreachable — a false NO.
COMBO = """
(world :name "Combo" :player @player)
(victory :when (:unlocked @safe))
(room @vault :description "Vault" :properties (:lit true))
(object @player :location @vault)
(object @safe :location @vault :properties (:unlocked false)
  :behaviors (
    :enter-code (fn (?code)
      (if (= ?code "4271")
        '((set @safe :unlocked true) (success))
        (blocked :reason wrong :message "nope")))))
"""


def test_value_argument_action_is_enumerated(tmp_path):
    rt = GrueRuntime(_load(tmp_path, COMBO))
    rt.reset()
    acts = {str(a) for a in enumerate_actions(rt)}
    assert "enter-code @safe 4271" in acts


def test_value_argument_goal_is_reachable(tmp_path):
    # The oracle must find the combination victory now that the guard literal is
    # in the candidate pool. Pre-fix this was a false NO.
    graph = explore(_load(tmp_path, COMBO))
    assert not graph.hit_limit
    assert graph.goal_reachable()


# A two-argument behavior: enumeration must supply the cartesian product of
# candidate objects, not a single argument.
TWOARG = """
(world :name "TwoArg" :player @player)
(victory :when (:joined @panel))
(room @lab :description "Lab" :properties (:lit true))
(object @player :location @lab)
(object @wire :location @lab :properties (:takeable true))
(object @bulb :location @lab :properties (:takeable true))
(object @panel :location @lab :properties (:joined false)
  :behaviors (
    :connect (fn (?a ?b)
      (if (and (= ?a @wire) (= ?b @bulb))
        '((set @panel :joined true) (success))
        (blocked :reason bad :message "no")))))
"""


def test_multiarg_action_is_enumerated(tmp_path):
    rt = GrueRuntime(_load(tmp_path, TWOARG))
    rt.reset()
    acts = {str(a) for a in enumerate_actions(rt)}
    # The specific winning pair must be present...
    assert "connect @panel @wire @bulb" in acts
    # ...and it must be a genuine 2-arg action, not a truncated 1-arg one.
    assert all(
        len(a.args) == 2
        for a in enumerate_actions(rt)
        if a.verb == "connect"
    )


def test_multiarg_goal_is_reachable(tmp_path):
    graph = explore(_load(tmp_path, TWOARG))
    assert not graph.hit_limit
    assert graph.goal_reachable()
