"""Tests for GRUE world parser."""

import pytest
from pathlib import Path

from grue import (
    parse_grue,
    load_grue,
    GrueWorld,
    GrueRoom,
    GrueObject,
    GrueParseError,
    Symbol,
    SList,
)


class TestBasicParsing:
    """Test basic GRUE parsing."""

    def test_empty_world(self):
        """Parse minimal world definition."""
        source = '(world :name "Test" :description "A test world")'
        world = parse_grue(source)

        assert world.name == "Test"
        assert world.description == "A test world"
        assert len(world.rooms) == 0
        assert len(world.objects) == 0

    def test_simple_room(self):
        """Parse a simple room."""
        source = """
        (room LOBBY
          :description "The main lobby"
          :flags (INSIDE LIT))
        """
        world = parse_grue(source)

        assert "LOBBY" in world.rooms
        room = world.rooms["LOBBY"]
        assert room.name == "LOBBY"
        assert room.description == "The main lobby"
        assert "INSIDE" in room.flags
        assert "LIT" in room.flags

    def test_room_with_exits(self):
        """Parse a room with exits."""
        source = """
        (room LOBBY
          :description "The main lobby"
          :flags (INSIDE LIT)
          :exits
            ((north :to HALLWAY)
             (out :to STREET :via FRONT-DOOR)))
        """
        world = parse_grue(source)

        room = world.rooms["LOBBY"]
        assert len(room.exits) == 2

        # Find exits by direction
        north_exit = next(e for e in room.exits if e.direction == "north")
        out_exit = next(e for e in room.exits if e.direction == "out")

        assert north_exit.to == "HALLWAY"
        assert north_exit.via is None

        assert out_exit.to == "STREET"
        assert out_exit.via == "FRONT-DOOR"

    def test_simple_object(self):
        """Parse a simple object."""
        source = """
        (object KEY
          :description "A brass key"
          :location PLAYER
          :flags (TAKEABLE))
        """
        world = parse_grue(source)

        assert "KEY" in world.objects
        obj = world.objects["KEY"]
        assert obj.name == "KEY"
        assert obj.description == "A brass key"
        assert obj.location == "PLAYER"
        assert "TAKEABLE" in obj.flags

    def test_object_with_properties(self):
        """Parse an object with properties."""
        source = """
        (object DOOR
          :description "A wooden door"
          :location LOBBY
          :flags (DOOR LOCKED)
          :properties
            ((lock-type electronic)
             (key-required MASTER-KEY)))
        """
        world = parse_grue(source)

        obj = world.objects["DOOR"]
        assert obj.properties["lock-type"] == "electronic"
        assert obj.properties["key-required"] == "MASTER-KEY"


class TestBehaviorParsing:
    """Test behavior parsing."""

    def test_simple_behavior(self):
        """Parse a simple behavior with one case."""
        source = """
        (object DOOR
          :description "A door"
          :location LOBBY
          :flags (DOOR)
          :behaviors (
            :open (cond
              (true (success)))))
        """
        world = parse_grue(source)

        obj = world.objects["DOOR"]
        assert len(obj.behaviors) == 1

        behavior = obj.behaviors[0]
        assert behavior.verb == "open"
        assert len(behavior.cases) == 1

        case = behavior.cases[0]
        assert case.outcome == "success"
        assert case.when is True

    def test_behavior_with_condition(self):
        """Parse a behavior with a complex condition."""
        source = """
        (object DOOR
          :description "A door"
          :location LOBBY
          :flags (DOOR LOCKED)
          :behaviors (
            :open (cond
              ((not (has-flag ?self LOCKED)) (success))
              (true (blocked :reason locked)))))
        """
        world = parse_grue(source)

        behavior = world.objects["DOOR"].behaviors[0]
        assert len(behavior.cases) == 2

        # First case has a condition
        case1 = behavior.cases[0]
        assert isinstance(case1.when, SList)
        assert case1.outcome == "success"

        # Second case is the fallback
        case2 = behavior.cases[1]
        assert case2.when is True
        assert case2.outcome == "blocked"
        assert case2.reason == "locked"

    def test_behavior_with_effects(self):
        """Parse a behavior that has effects."""
        source = """
        (object DOOR
          :description "A door"
          :location LOBBY
          :flags (DOOR LOCKED)
          :behaviors (
            :unlock (cond
              ((= ?with KEY) (success :effects ((clear-flag! ?self LOCKED)))))))
        """
        world = parse_grue(source)

        case = world.objects["DOOR"].behaviors[0].cases[0]
        assert len(case.effects) == 1
        assert isinstance(case.effects[0], SList)

    def test_behavior_with_context(self):
        """Parse a behavior with context hints."""
        source = """
        (object DOOR
          :description "A door"
          :location LOBBY
          :behaviors (
            :open (cond
              (true (success :context ((mechanism push-bar)
                                       (note auto-closing)))))))
        """
        world = parse_grue(source)

        case = world.objects["DOOR"].behaviors[0].cases[0]
        assert len(case.context) == 2
        assert ("mechanism", "push-bar") in case.context
        assert ("note", "auto-closing") in case.context

    def test_behavior_with_default(self):
        """Parse a behavior with default action."""
        source = """
        (object DOOR
          :description "A door"
          :location LOBBY
          :behaviors (
            :through (cond
              (true (default :action (go :direction in))))))
        """
        world = parse_grue(source)

        case = world.objects["DOOR"].behaviors[0].cases[0]
        assert case.outcome == "default"
        assert isinstance(case.action, SList)


class TestVictoryDefeat:
    """Test victory and defeat conditions."""

    def test_victory(self):
        """Parse victory condition."""
        source = """
        (victory
          :when (= (loc PLAYER) ENDROOM)
          :context ((ending good)))
        """
        world = parse_grue(source)

        assert world.victory is not None
        assert isinstance(world.victory.when, SList)
        assert len(world.victory.context) == 1

    def test_defeat(self):
        """Parse defeat condition."""
        source = """
        (defeat EATEN-BY-GRUE
          :when (and (not (room-has-flag? LIT))
                     (not (held? LAMP)))
          :context ((death-type grue)))
        """
        world = parse_grue(source)

        assert "EATEN-BY-GRUE" in world.defeat
        defeat = world.defeat["EATEN-BY-GRUE"]
        assert defeat.name == "EATEN-BY-GRUE"
        assert isinstance(defeat.when, SList)


class TestExampleFile:
    """Test parsing the example file."""

    def test_parse_outside_door_example(self):
        """Parse the outside-door.grue example file."""
        example_path = Path(__file__).parent.parent / "games" / "examples" / "outside-door.grue"
        if not example_path.exists():
            pytest.skip("Example file not found")

        world = load_grue(example_path)

        # Check world meta
        assert world.name == "Outside Door Example"

        # Check rooms (now using @lowercase naming)
        assert "@mass-ave" in world.rooms
        assert "@lobby" in world.rooms
        assert "@hallway" in world.rooms

        mass_ave = world.rooms["@mass-ave"]
        assert "OUTSIDE" in mass_ave.flags
        assert "LIT" in mass_ave.flags
        assert len(mass_ave.exits) == 3

        # Check objects
        assert "@player" in world.objects
        assert "@outside-door" in world.objects
        assert "@master-key" in world.objects

        door = world.objects["@outside-door"]
        assert door.location == "@mass-ave"
        assert "DOOR" in door.flags
        assert "LOCKED" in door.flags
        assert door.properties["lock-type"] == "electronic"

        # Check door behaviors
        behavior_verbs = [b.verb for b in door.behaviors]
        assert "open" in behavior_verbs
        assert "unlock" in behavior_verbs
        assert "close" in behavior_verbs
        assert "through" in behavior_verbs
        assert "examine" in behavior_verbs

        # Check the open behavior has multiple cases
        open_behavior = next(b for b in door.behaviors if b.verb == "open")
        assert len(open_behavior.cases) == 3

        # Check victory
        assert world.victory is not None



class TestGlobals:
    """Test globals parsing."""

    def test_globals_simple(self):
        """Parse globals with integer and boolean values."""
        source = """
        (globals
          :lair-cnt 0
          :hacker-help 0
          :hacker-trade false)
        """
        world = parse_grue(source)

        assert "lair-cnt" in world.globals
        assert world.globals["lair-cnt"] == 0
        assert world.globals["hacker-help"] == 0
        assert world.globals["hacker-trade"] is False

    def test_globals_various_types(self):
        """Parse globals with various value types."""
        source = """
        (globals
          :counter 42
          :active true
          :name "test-world"
          :negative -10)
        """
        world = parse_grue(source)

        assert world.globals["counter"] == 42
        assert world.globals["active"] is True
        assert world.globals["name"] == "test-world"
        assert world.globals["negative"] == -10

    def test_globals_with_world(self):
        """Parse globals alongside world definition."""
        source = """
        (world :name "Test")
        (globals :score 100 :lives 3)
        (room LOBBY :description "A lobby")
        """
        world = parse_grue(source)

        assert world.name == "Test"
        assert world.globals["score"] == 100
        assert world.globals["lives"] == 3
        assert "LOBBY" in world.rooms

    def test_globals_empty(self):
        """Parse empty globals form."""
        source = "(globals)"
        world = parse_grue(source)
        # Should not error, just have no custom globals
        assert len(world.globals) == 0


class TestErrors:
    """Test error handling."""

    def test_unknown_form(self):
        """Unknown top-level form raises error."""
        source = "(bogus-form :key value)"
        with pytest.raises(GrueParseError) as exc:
            parse_grue(source)
        assert "Unknown top-level form" in str(exc.value)

    def test_missing_room_name(self):
        """Room without name raises error."""
        source = "(room)"
        with pytest.raises(GrueParseError) as exc:
            parse_grue(source)
        assert "requires a name" in str(exc.value)

    def test_missing_exit_destination(self):
        """Exit without :to raises error."""
        source = """
        (room LOBBY
          :exits ((north)))
        """
        with pytest.raises(GrueParseError) as exc:
            parse_grue(source)
        assert "missing :to" in str(exc.value)

    def test_missing_victory_when(self):
        """Victory without :when raises error."""
        source = "(victory :context ((ending good)))"
        with pytest.raises(GrueParseError) as exc:
            parse_grue(source)
        assert "requires :when" in str(exc.value)
