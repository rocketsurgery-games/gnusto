"""Completeness of the effect model.

The frotz effect analyzer must recognize every state mutation the runtime can
apply. Any gap is hidden state that silently corrupts every downstream tool
(reach, requires, depgraph, deadends). These tests pin the analyzer's coverage
to the runtime's authoritative vocabulary so a new effect can't land without a
matching analyzer handler.
"""

from grue import parse_grue
from grue.expr import EffectInterpreter
from frotz.effects import (
    analyze_effects,
    HANDLED_EFFECT_MUTATIONS,
    LocationRef,
    PropertyRef,
)
from frotz.backward import BackwardAnalyzer, Constraint


def test_analyzer_vocab_matches_runtime_vocab():
    """Drift guard: analyzer vocabulary == runtime effect vocabulary, exactly.

    If this fails, the runtime's EffectInterpreter.MUTATIONS gained or lost a
    head. Update frotz.effects: add a handler in `_walk_expr` (or remove the
    stale one) AND update HANDLED_EFFECT_MUTATIONS to match. See docs/frotz.md.
    """
    assert HANDLED_EFFECT_MUTATIONS == EffectInterpreter.MUTATIONS, (
        "frotz effect model is out of sync with the runtime effect vocabulary. "
        f"runtime-only: {EffectInterpreter.MUTATIONS - HANDLED_EFFECT_MUTATIONS}; "
        f"analyzer-only: {HANDLED_EFFECT_MUTATIONS - EffectInterpreter.MUTATIONS}"
    )


# A world exercising every property-writing effect head in a behavior body.
PROP_EFFECTS = """
(world :name "PropFx" :player @player)
(room @room :description "Room")
(object @player :location @room)
(object @widget :location @room
  :properties (:count 0 :size 3 :known false :data 0)
  :behaviors (
    :poke (fn ()
      '((inc @widget :count)
        (dec @widget :size)
        (set-in @widget (:data) 5)
        (expose @widget)
        (success)))))
"""


def test_property_writing_effects_are_modeled():
    world = parse_grue(PROP_EFFECTS)
    fx = analyze_effects(world)

    def modifiers(ref):
        return {(b.object, b.verb) for b in fx.modifies.get(ref, set())}

    # inc / dec / set-in / expose each register a modifier on their property.
    assert ("@widget", "poke") in modifiers(PropertyRef("@widget", "count"))
    assert ("@widget", "poke") in modifiers(PropertyRef("@widget", "size"))
    assert ("@widget", "poke") in modifiers(PropertyRef("@widget", "data"))
    assert ("@widget", "poke") in modifiers(PropertyRef("@widget", "known"))

    # inc / dec also read the current value.
    reads = {(b.object, b.verb) for b in fx.reads.get(PropertyRef("@widget", "count"), set())}
    assert ("@widget", "poke") in reads


# A world where a treasure must be deposited into a container (the defect-A case).
DEPOSIT = """
(world :name "Deposit" :player @player)
(room @room :description "Room")
(object @player :location @room)
(object @case :location @room :properties (:container true :open true))
(object @gem :location @room :properties (:takeable true))
"""


def test_runtime_put_enables_deposit_goal():
    """Regression for defect A: a deposit goal must have an achiever, not be
    treated as constant because `put` was unmodeled."""
    world = parse_grue(DEPOSIT)
    fx = analyze_effects(world)

    gem_loc = LocationRef("@gem")
    # runtime:put is a modifier of the gem's location...
    assert ("runtime", "put") in {(b.object, b.verb) for b in fx.modifies.get(gem_loc, set())}
    # ...and can target the container.
    assert "@case" in fx.modifies_to.get(gem_loc, {}).get(
        next(b for b in fx.modifies_to.get(gem_loc, {}) if b.verb == "put"), set()
    )

    # The backward analyzer now finds a real achiever (not a constant).
    an = BackwardAnalyzer(world, fx)
    tree = an.build_tree(Constraint(ref=gem_loc, operator="=", value="@case"), max_depth=8)
    assert not tree.root.is_constant
    assert tree.root.achievers, "deposit goal should have at least one achiever"
    assert any(a.behavior.verb == "put" for a in tree.root.achievers)
