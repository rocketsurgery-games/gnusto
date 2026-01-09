"""Tests for behavioral DSL extension."""

import pytest

from zil.dsl import (
    WorldParser,
    Object,
    Behavior,
    BehaviorCase,
    Symbol,
    SList,
    parse_world,
)


class TestBehaviorParsing:
    """Test parsing behavior definitions from YAML."""

    def test_parse_simple_behavior(self):
        """Test parsing a simple single-case behavior."""
        yaml = """
objects:
  LAMP:
    description: "brass lamp"
    behaviors:
      rub:
        message: "Rubbing the lamp has no effect."
"""
        world = parse_world(yaml)

        assert "LAMP" in world.objects
        lamp = world.objects["LAMP"]
        assert "rub" in lamp.behaviors

        rub = lamp.behaviors["rub"]
        assert rub.verb == "rub"
        assert len(rub.cases) == 1

        case = rub.cases[0]
        assert isinstance(case.when, Symbol)
        assert case.when.name == "true"  # Default case
        assert case.message == "Rubbing the lamp has no effect."
        assert case.do is None
        assert case.handled is True

    def test_parse_behavior_with_effect(self):
        """Test parsing a behavior with an effect."""
        yaml = """
objects:
  LAMP:
    behaviors:
      take:
        do: "(inc! SCORE 5)"
        message: "You take the lamp."
"""
        world = parse_world(yaml)
        lamp = world.objects["LAMP"]

        case = lamp.behaviors["take"].cases[0]
        assert isinstance(case.do, SList)
        assert case.do.items[0] == Symbol("inc!")
        assert case.message == "You take the lamp."

    def test_parse_behavior_with_condition(self):
        """Test parsing a behavior with an explicit condition."""
        yaml = """
objects:
  DOOR:
    behaviors:
      open:
        cases:
          - when: "(prop self locked)"
            message: "The door is locked."
          - when: "true"
            do: "(set-prop! self open true)"
            message: "The door opens."
"""
        world = parse_world(yaml)
        door = world.objects["DOOR"]

        open_behavior = door.behaviors["open"]
        assert len(open_behavior.cases) == 2

        # First case: locked check
        case1 = open_behavior.cases[0]
        assert isinstance(case1.when, SList)
        assert case1.when.items[0] == Symbol("prop")
        assert case1.message == "The door is locked."

        # Second case: default
        case2 = open_behavior.cases[1]
        assert isinstance(case2.when, Symbol)
        assert case2.when.name == "true"
        assert case2.message == "The door opens."

    def test_parse_behavior_handled_false(self):
        """Test parsing a behavior that doesn't consume the action."""
        yaml = """
objects:
  STONE:
    behaviors:
      take:
        do: "(queue I-COOL 20)"
        handled: false
"""
        world = parse_world(yaml)
        stone = world.objects["STONE"]

        case = stone.behaviors["take"].cases[0]
        assert case.handled is False

    def test_parse_complex_behavior(self):
        """Test parsing OUTSIDE-DOOR style behavior."""
        yaml = """
objects:
  OUTSIDE-DOOR:
    description: "outside door"
    flags: [DOORBIT, LOCKED, NDESCBIT, OPENABLE]
    properties:
      locked: true

    behaviors:
      through:
        cases:
          - when: "(has-flag (loc PLAYER) OUTSIDE)"
            do: "(go-direction IN)"
          - when: "true"
            do: "(go-direction OUT)"

      open:
        cases:
          - when: "(and (has-flag (loc PLAYER) OUTSIDE) (in-room? PLAYER MASS-AVE SMITH-ST))"
            message: "The door opens from this side."
          - when: "(has-flag (loc PLAYER) OUTSIDE)"
            message: "The door is securely locked."
          - when: "true"
            message: "You can open the door, but it shuts automatically immediately thereafter."

      unlock:
        cases:
          - when: "(and (has-flag (loc PLAYER) OUTSIDE) (= INSTRUMENT MASTER-KEY))"
            message: "The door is not keyed to this key."
          - when: "(has-flag (loc PLAYER) OUTSIDE)"
            message: "The door is securely locked."
"""
        world = parse_world(yaml)
        door = world.objects["OUTSIDE-DOOR"]

        # Check through behavior
        through = door.behaviors["through"]
        assert len(through.cases) == 2

        # Check open behavior
        open_b = door.behaviors["open"]
        assert len(open_b.cases) == 3
        assert "opens from this side" in open_b.cases[0].message
        assert "securely locked" in open_b.cases[1].message
        assert "shuts automatically" in open_b.cases[2].message

        # Check unlock behavior
        unlock = door.behaviors["unlock"]
        assert len(unlock.cases) == 2


class TestBehaviorSerialization:
    """Test serializing behaviors back to YAML."""

    def test_serialize_simple_behavior(self):
        """Test serializing a simple behavior to dict."""
        case = BehaviorCase(
            when=Symbol("true"),
            message="Hello!",
        )
        behavior = Behavior(verb="greet", cases=[case])

        d = behavior.to_dict()
        # Single default case uses compact form
        assert "cases" not in d
        assert d["message"] == "Hello!"

    def test_serialize_multi_case_behavior(self):
        """Test serializing a multi-case behavior."""
        from zil.dsl import parse

        case1 = BehaviorCase(
            when=parse("(prop self locked)"),
            message="Locked!",
        )
        case2 = BehaviorCase(
            when=Symbol("true"),
            message="Opened!",
        )
        behavior = Behavior(verb="open", cases=[case1, case2])

        d = behavior.to_dict()
        assert "cases" in d
        assert len(d["cases"]) == 2
        assert d["cases"][0]["when"] == "(prop self locked)"
        assert d["cases"][0]["message"] == "Locked!"
        # Default case doesn't emit 'when'
        assert "when" not in d["cases"][1]
        assert d["cases"][1]["message"] == "Opened!"

    def test_serialize_behavior_with_do(self):
        """Test serializing a behavior with effects."""
        from zil.dsl import parse

        case = BehaviorCase(
            when=Symbol("true"),
            do=parse("(move! self PLAYER)"),
            message="Taken.",
        )
        behavior = Behavior(verb="take", cases=[case])

        d = behavior.to_dict()
        assert d["do"] == "(move! self PLAYER)"
        assert d["message"] == "Taken."

    def test_serialize_handled_false(self):
        """Test that handled:false is serialized."""
        case = BehaviorCase(
            when=Symbol("true"),
            do=None,
            handled=False,
        )
        behavior = Behavior(verb="take", cases=[case])

        d = behavior.to_dict()
        assert d["handled"] is False

    def test_roundtrip(self):
        """Test that behavior roundtrips through parse/serialize."""
        yaml = """
objects:
  DOOR:
    behaviors:
      open:
        cases:
          - when: "(prop self locked)"
            message: "The door is locked."
          - message: "The door opens."
            do: "(set-flag! self OPENBIT)"
"""
        world = parse_world(yaml)

        # Serialize back
        output = world.to_yaml()

        # Parse again
        world2 = parse_world(output)

        # Check it matches
        door = world2.objects["DOOR"]
        open_b = door.behaviors["open"]
        assert len(open_b.cases) == 2
        assert "locked" in open_b.cases[0].message


class TestObjectWithBehaviors:
    """Test Object class with behaviors."""

    def test_object_has_empty_behaviors_by_default(self):
        """Test that Object has empty behaviors dict by default."""
        obj = Object(name="TEST")
        assert obj.behaviors == {}

    def test_object_to_dict_includes_behaviors(self):
        """Test that to_dict includes behaviors when present."""
        from zil.dsl import parse

        obj = Object(name="LAMP")
        obj.behaviors["rub"] = Behavior(
            verb="rub",
            cases=[BehaviorCase(when=Symbol("true"), message="Nothing happens.")]
        )

        d = obj.to_dict()
        assert "behaviors" in d
        assert "rub" in d["behaviors"]
        assert d["behaviors"]["rub"]["message"] == "Nothing happens."

    def test_object_to_dict_excludes_empty_behaviors(self):
        """Test that to_dict excludes behaviors when empty."""
        obj = Object(name="LAMP")

        d = obj.to_dict()
        assert "behaviors" not in d

    def test_object_with_zil_source(self):
        """Test that zil_source is preserved."""
        yaml = """
objects:
  DOOR:
    description: "a door"
    zil_source: |
      <ROUTINE DOOR-F ()
         <COND (<VERB? OPEN>
                <TELL "It opens." CR>)>>
"""
        world = parse_world(yaml)
        door = world.objects["DOOR"]
        assert door.zil_source is not None
        assert "ROUTINE DOOR-F" in door.zil_source
