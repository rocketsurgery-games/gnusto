"""Tests for World YAML parser."""

import pytest
from pathlib import Path
from zil.dsl import (
    WorldParser,
    WorldDefinition,
    Room,
    Object,
    Action,
    load_world,
    parse_world,
)
from zil.dsl.sexpr import Symbol


@pytest.fixture
def simple_world_yaml():
    return """
meta:
  name: "Test World"
  author: "Test Author"
  starting_room: ROOM-1

rooms:
  ROOM-1:
    description: "First Room"
    exits:
      north: ROOM-2
    flags:
      - ONBIT

  ROOM-2:
    description: "Second Room"
    exits:
      south: ROOM-1

objects:
  KEY:
    description: "brass key"
    initial_location: ROOM-1
    flags:
      - TAKEBIT
    synonyms:
      - KEY
      - BRASS-KEY
"""


@pytest.fixture
def terminal_room_path():
    return Path(__file__).parent.parent / "games" / "lurkinghorror" / "terminal_room.yaml"


class TestWorldParser:
    """Test basic YAML parsing."""

    def test_parse_empty(self):
        parser = WorldParser()
        world = parser.parse("")
        assert isinstance(world, WorldDefinition)
        assert len(world.rooms) == 0

    def test_parse_meta(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        assert world.meta.name == "Test World"
        assert world.meta.author == "Test Author"
        assert world.meta.starting_room == "ROOM-1"

    def test_parse_rooms(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        assert len(world.rooms) == 2
        assert "ROOM-1" in world.rooms
        assert "ROOM-2" in world.rooms

        room1 = world.rooms["ROOM-1"]
        assert room1.name == "ROOM-1"
        assert room1.description == "First Room"
        assert "north" in room1.exits
        assert room1.exits["north"].to == "ROOM-2"
        assert "ONBIT" in room1.flags

    def test_parse_objects(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        assert len(world.objects) == 1
        assert "KEY" in world.objects

        key = world.objects["KEY"]
        assert key.name == "KEY"
        assert key.description == "brass key"
        assert key.initial_location == "ROOM-1"
        assert "TAKEBIT" in key.flags
        assert "KEY" in key.synonyms


class TestConditionalExits:
    """Test exits with conditions."""

    def test_parse_conditional_exit(self):
        yaml = """
rooms:
  ROOM-1:
    description: "Room with guarded exit"
    exits:
      north:
        to: ROOM-2
        when: "(not (has-flag DOOR LOCKED))"
  ROOM-2:
    description: "Destination"
"""
        world = parse_world(yaml)
        exit = world.rooms["ROOM-1"].exits["north"]
        assert exit.to == "ROOM-2"
        assert exit.when is not None
        # The condition should be parsed as an S-expression (SList is a list subclass)
        from zil.dsl.sexpr import SList
        assert isinstance(exit.when, SList)


class TestActions:
    """Test action parsing."""

    def test_parse_action_with_conditions(self):
        yaml = """
actions:
  TAKE:
    syntax:
      - "take [object]"
    preconditions:
      - "(has-flag ?obj TAKEBIT)"
      - "(visible? ?obj)"
    effects:
      - "(move! ?obj PLAYER)"
    messages:
      success: "Taken."
      failure: "You can't take that."
"""
        world = parse_world(yaml)
        assert "TAKE" in world.actions
        take = world.actions["TAKE"]
        assert len(take.preconditions) == 2
        assert len(take.effects) == 1
        assert take.messages.success == "Taken."
        assert take.messages.failure == "You can't take that."


class TestTransitions:
    """Test transition parsing."""

    def test_parse_transition(self):
        yaml = """
transitions:
  door-blocks:
    trigger:
      action: GO
      direction: north
    when: "(has-flag DOOR LOCKED)"
    effects:
      - "(set-flag! DOOR TRIED)"
    message: "The door is locked."
"""
        world = parse_world(yaml)
        assert "door-blocks" in world.transitions
        trans = world.transitions["door-blocks"]
        assert trans.trigger["action"] == "GO"
        assert trans.trigger["direction"] == "north"
        assert trans.when is not None
        assert len(trans.effects) == 1
        assert trans.message == "The door is locked."


class TestInvariants:
    """Test invariant parsing."""

    def test_parse_simple_invariant(self):
        yaml = """
invariants:
  always-lit:
    check: "(has-flag ROOM ONBIT)"
"""
        world = parse_world(yaml)
        assert "always-lit" in world.invariants
        inv = world.invariants["always-lit"]
        assert inv.check is not None

    def test_parse_invariant_string_form(self):
        yaml = """
invariants:
  always-lit: "(has-flag ROOM ONBIT)"
"""
        world = parse_world(yaml)
        assert "always-lit" in world.invariants
        assert world.invariants["always-lit"].check is not None


class TestVictoryAndDefeat:
    """Test win/lose conditions."""

    def test_parse_victory(self):
        yaml = """
victory:
  when: "(has-flag PLAYER WON)"
  message: "Congratulations! You have won!"
"""
        world = parse_world(yaml)
        assert world.victory is not None
        assert world.victory.message == "Congratulations! You have won!"

    def test_parse_defeat(self):
        yaml = """
defeat:
  eaten-by-grue:
    when: "(and (not (prop ROOM lit)) (not (any (inventory PLAYER) (lambda (x) (has-flag x LIGHTBIT)))))"
    message: "You have been eaten by a grue."
"""
        world = parse_world(yaml)
        assert "eaten-by-grue" in world.defeat
        assert world.defeat["eaten-by-grue"].message == "You have been eaten by a grue."


class TestLurkingHorrorTerminalRoom:
    """Test parsing the actual Lurking Horror Terminal Room file."""

    def test_load_terminal_room(self, terminal_room_path):
        """Load and verify the Terminal Room world definition."""
        if not terminal_room_path.exists():
            pytest.skip("Terminal room file not found")

        world = load_world(str(terminal_room_path))

        # Check meta
        assert world.meta.name == "The Lurking Horror - Terminal Room"
        assert world.meta.starting_room == "TERMINAL-ROOM"

        # Check rooms
        assert "TERMINAL-ROOM" in world.rooms
        assert "CS-2ND" in world.rooms
        assert "KITCHEN" in world.rooms

        terminal = world.rooms["TERMINAL-ROOM"]
        assert terminal.description == "Terminal Room"
        assert "south" in terminal.exits
        assert terminal.exits["south"].to == "CS-2ND"
        assert terminal.exits["south"].when is not None  # Has condition

        # Check objects
        assert "HACKER" in world.objects
        assert "CHAIR" in world.objects
        assert "PC" in world.objects

        hacker = world.objects["HACKER"]
        assert hacker.initial_location == "TERMINAL-ROOM"
        assert "PERSON" in hacker.flags

        chair = world.objects["CHAIR"]
        assert "TAKEBIT" in chair.flags
        assert chair.properties.get("size") == 100

        # Check actions
        assert "TAKE" in world.actions
        assert "EXAMINE" in world.actions

        # Check transitions
        assert "hacker-blocks-exit" in world.transitions

        # Check invariants
        assert "player-has-light" in world.invariants

    def test_roundtrip_serialization(self, terminal_room_path):
        """Test that we can load, serialize, and reload the world."""
        if not terminal_room_path.exists():
            pytest.skip("Terminal room file not found")

        # Load original
        world1 = load_world(str(terminal_room_path))

        # Serialize to YAML
        yaml_str = world1.to_yaml()

        # Reload from serialized
        world2 = parse_world(yaml_str)

        # Verify key elements match
        assert world2.meta.name == world1.meta.name
        assert set(world2.rooms.keys()) == set(world1.rooms.keys())
        assert set(world2.objects.keys()) == set(world1.objects.keys())
        assert set(world2.actions.keys()) == set(world1.actions.keys())


class TestSerialization:
    """Test serialization to YAML."""

    def test_to_dict(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        d = world.to_dict()

        assert "meta" in d
        assert d["meta"]["name"] == "Test World"
        assert "rooms" in d
        assert "ROOM-1" in d["rooms"]

    def test_to_yaml(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        yaml_str = world.to_yaml()

        # Should be valid YAML that can be re-parsed
        world2 = parse_world(yaml_str)
        assert world2.meta.name == world.meta.name
