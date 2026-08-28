"""A corpus of tiny, hand-enumerable games for differential testing.

Each `CorpusGame` is a small Grue source plus a handful of *hand-verified* anchor
facts (goal reachability and specific atom reachabilities). The anchors pin down
the concrete truth independently of the kernel, so a kernel regression that
silently redefined "reachable" would fail these — and every abstraction layer is
then differential-tested against the kernel across the same corpus
(`frotz.differential`).

The corpus is seeded to exercise the essentials *and* the shapes that stress each
planned abstraction layer, so a layer can be checked the moment it exists:

- ``mini`` / ``sealed`` — movement + a gated edge + a boolean gate; solvable vs.
  permanently-locked (a real NO).
- ``combo`` — a value-argument action (combination lock); exercises the oracle's
  source-literal argument pool.
- ``twoarg`` — a two-argument behavior; exercises multi-arg cartesian enumeration.
- ``counter`` — a numeric counter gate; stresses value-domain / numeric-interval
  abstraction (layer 4.2).
- ``oneway`` / ``oneway_ok`` — an irreversible descent; stresses the
  reversibility/directionality quotient (layer 4.3). The soft-locked variant is a
  genuine unwinnable state the oracle must detect.
- ``independent`` — two order-independent takes; stresses partial-order reduction
  (commuting operators, layer 4.3).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from frotz.differential import Atom, held, loc, prop


@dataclass
class CorpusGame:
    name: str
    source: str
    goal_reachable: bool
    anchors: list[tuple[Atom, bool]] = field(default_factory=list)


# --- movement + gate: solvable vs. sealed -------------------------------------

_MINI = """
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
        {SOLVE}
        (true (blocked :reason locked :message "locked"))))))
"""

MINI = CorpusGame(
    name="mini",
    source=_MINI.replace(
        "{SOLVE}", "((held? @key) '((set @door :open true) (success)))"
    ),
    goal_reachable=True,
    anchors=[
        (held("@gem"), True),
        (held("@key"), True),
        (loc("@player", "@hall"), True),
        (prop("@door", "open", True), True),
    ],
)

SEALED = CorpusGame(
    name="sealed",
    source=_MINI.replace("{SOLVE}", ""),  # nothing ever opens the door
    goal_reachable=False,
    anchors=[
        (held("@gem"), False),         # behind a door that never opens
        (loc("@player", "@hall"), False),
        (prop("@door", "open", True), False),
        (held("@key"), True),          # the key is still takeable
    ],
)


# --- value-argument action: a combination lock --------------------------------

COMBO = CorpusGame(
    name="combo",
    source="""
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
""",
    goal_reachable=True,
    anchors=[
        (prop("@safe", "unlocked", True), True),
        (prop("@safe", "unlocked", False), True),
    ],
)


# --- two-argument behavior ----------------------------------------------------

TWOARG = CorpusGame(
    name="twoarg",
    source="""
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
""",
    goal_reachable=True,
    anchors=[(prop("@panel", "joined", True), True)],
)


# --- numeric counter gate (stresses value-domain abstraction, 4.2) ------------

COUNTER = CorpusGame(
    name="counter",
    source="""
(world :name "Counter" :player @player)
(victory :when (:open @gate))
(room @start :description "Start" :properties (:lit true))
(object @player :location @start)
(object @gate :location @start :properties (:open false))
(object @lever :location @start :properties (:pulls 0)
  :behaviors (
    :pull (fn ()
      (if (>= (:pulls @lever) 3)
        '((set @gate :open true) (success))
        '((inc @lever :pulls) (success))))))
""",
    goal_reachable=True,
    anchors=[
        (prop("@gate", "open", True), True),
        (prop("@gate", "open", False), True),
    ],
)


# --- irreversible descent (stresses directionality quotient, 4.3) -------------
#
# Descending to the cave is one-way. The crystal is in the cave; the altar (which
# wins) is on the cliff. In the soft-locked variant there is no way back up, so
# you can never hold the crystal AND be at the altar: victory is genuinely
# unreachable, and the oracle must say so.

_ONEWAY = """
(world :name "OneWay" :player @player)
(victory :when (:offered @altar))
(room @cliff :description "Cliff" :properties (:lit true)
  :exits ((down :to @cave)))
(room @cave :description "Cave" :properties (:lit true){CAVE_EXIT})
(object @player :location @cliff)
(object @altar :location @cliff :properties (:offered false)
  :behaviors (
    :offer (fn ()
      (if (held? @crystal)
        '((set @altar :offered true) (success))
        (blocked :reason no-crystal :message "need the crystal")))))
(object @crystal :location @cave :properties (:takeable true))
"""

ONEWAY = CorpusGame(
    name="oneway",
    source=_ONEWAY.replace("{CAVE_EXIT}", ""),  # cave is a dead end: no way back up
    goal_reachable=False,
    anchors=[
        (prop("@altar", "offered", True), False),  # can never offer
        (held("@crystal"), True),                  # but you CAN grab it (then trapped)
        (loc("@player", "@cave"), True),
    ],
)

ONEWAY_OK = CorpusGame(
    name="oneway_ok",
    source=_ONEWAY.replace("{CAVE_EXIT}", "\n  :exits ((up :to @cliff))"),
    goal_reachable=True,
    anchors=[
        (prop("@altar", "offered", True), True),
        (held("@crystal"), True),
    ],
)


# --- order-independent takes (stresses partial-order reduction, 4.3) ----------

INDEPENDENT = CorpusGame(
    name="independent",
    source="""
(world :name "Independent" :player @player)
(victory :when (and (held? @coin) (held? @gem)))
(room @room :description "Room" :properties (:lit true))
(object @player :location @room)
(object @coin :location @room :properties (:takeable true))
(object @gem :location @room :properties (:takeable true))
""",
    goal_reachable=True,
    anchors=[
        (held("@coin"), True),
        (held("@gem"), True),
    ],
)


CORPUS: list[CorpusGame] = [
    MINI,
    SEALED,
    COMBO,
    TWOARG,
    COUNTER,
    ONEWAY,
    ONEWAY_OK,
    INDEPENDENT,
]
