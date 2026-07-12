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
        # Darkness/start-events defaults
        assert world.dark_message == "It is pitch black."
        assert world.start_events == []

    def test_world_dark_message_and_start_events(self):
        """Parse world :dark-message and :start-events."""
        source = """
        (world :player @player
          :dark-message "It is pitch black. You are likely to be eaten by a grue."
          :start-events (grue-lurks background-clock))
        """
        world = parse_grue(source)
        assert world.dark_message == "It is pitch black. You are likely to be eaten by a grue."
        assert world.start_events == ["grue-lurks", "background-clock"]

    def test_simple_room(self):
        """Parse a simple room."""
        source = """
        (room LOBBY
          :description "The main lobby"
          :properties (:inside true :lit true))
        """
        world = parse_grue(source)

        assert "LOBBY" in world.rooms
        room = world.rooms["LOBBY"]
        assert room.name == "LOBBY"
        assert room.description == "The main lobby"
        assert room.properties.get("inside") is True
        assert room.properties.get("lit") is True

    def test_room_with_exits(self):
        """Parse a room with exits."""
        source = """
        (room LOBBY
          :description "The main lobby"
          :properties (:inside true :lit true)
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

    def test_blocked_message_exit(self):
        """Parse a message-only :blocked exit (ZIL string/SORRY exit)."""
        source = """
        (room LOBBY
          :exits ((north :to HALLWAY)
                  (west :blocked "You would need a machete to go further west.")))
        """
        world = parse_grue(source)

        west_exit = next(e for e in world.rooms["LOBBY"].exits if e.direction == "west")
        assert west_exit.to is None
        assert west_exit.via is None
        assert west_exit.blocked == "You would need a machete to go further west."

    def test_exit_to_and_blocked_conflict(self):
        """:to and :blocked are mutually exclusive."""
        source = """
        (room LOBBY
          :exits ((west :to HALLWAY :blocked "nope")))
        """
        with pytest.raises(Exception) as exc:
            parse_grue(source)
        assert "both :to and :blocked" in str(exc.value)

    def test_simple_object(self):
        """Parse a simple object."""
        source = """
        (object KEY
          :description "A brass key"
          :location PLAYER
          :properties (:takeable true))
        """
        world = parse_grue(source)

        assert "KEY" in world.objects
        obj = world.objects["KEY"]
        assert obj.name == "KEY"
        assert obj.description == "A brass key"
        assert obj.location == "PLAYER"
        assert obj.properties.get("takeable") is True

    def test_object_with_properties(self):
        """Parse an object with properties."""
        source = """
        (object DOOR
          :description "A wooden door"
          :location LOBBY
          :properties (:door true :locked true)
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
          :properties (:door true)
          :behaviors (
            :open (fn ()
              (cond
                (true (success))))))
        """
        world = parse_grue(source)

        obj = world.objects["DOOR"]
        assert len(obj.behaviors) == 1

        behavior = obj.behaviors[0]
        assert behavior.verb == "open"
        assert behavior.params == []
        # Body is stored as an SExpr (the cond expression)
        assert behavior.body is not None
        assert isinstance(behavior.body, SList)
        assert behavior.body[0].name == "cond"

    def test_behavior_with_condition(self):
        """Parse a behavior with a complex condition."""
        source = """
        (object DOOR
          :description "A door"
          :location LOBBY
          :properties (:door true :locked true)
          :behaviors (
            :open (fn ()
              (cond
                ((not (:locked ?self)) (success))
                (true (blocked :reason locked))))))
        """
        world = parse_grue(source)

        behavior = world.objects["DOOR"].behaviors[0]
        # Body is the cond expression with 2 clauses
        assert behavior.body is not None
        assert isinstance(behavior.body, SList)
        assert behavior.body[0].name == "cond"
        # cond has 2 clauses + the "cond" symbol = 3 items
        assert len(behavior.body) == 3

    def test_behavior_with_effects(self):
        """Parse a behavior that has effects."""
        source = """
        (object DOOR
          :description "A door"
          :location LOBBY
          :properties (:door true :locked true)
          :behaviors (
            :unlock (fn (?key)
              (cond
                ((= ?key KEY) '((set ?self :locked false) (success)))))))
        """
        world = parse_grue(source)

        behavior = world.objects["DOOR"].behaviors[0]
        assert behavior.params == ["key"]
        # Body is stored as raw SExpr
        assert behavior.body is not None
        assert isinstance(behavior.body, SList)

    def test_behavior_with_context(self):
        """Parse a behavior with context hints."""
        source = """
        (object DOOR
          :description "A door"
          :location LOBBY
          :behaviors (
            :open (fn ()
              (cond
                (true (success :context ((mechanism push-bar)
                                         (note auto-closing))))))))
        """
        world = parse_grue(source)

        behavior = world.objects["DOOR"].behaviors[0]
        # Body stored as raw SExpr - not pre-parsed
        assert behavior.body is not None
        assert isinstance(behavior.body, SList)

    def test_behavior_with_default(self):
        """Parse a behavior with default action."""
        source = """
        (object DOOR
          :description "A door"
          :location LOBBY
          :behaviors (
            :through (fn ()
              (cond
                (true (default :action (go :direction in)))))))
        """
        world = parse_grue(source)

        behavior = world.objects["DOOR"].behaviors[0]
        # Body is stored as raw SExpr (the cond expression)
        assert behavior.body is not None
        assert isinstance(behavior.body, SList)
        assert behavior.body[0].name == "cond"


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
          :when (and (not (room-has-flag? "lit"))
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

        # Check the open behavior has a body
        open_behavior = next(b for b in door.behaviors if b.verb == "open")
        assert open_behavior.body is not None
        assert isinstance(open_behavior.body, SList)

        # Check victory
        assert world.victory is not None


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
