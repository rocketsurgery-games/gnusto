"""Tests for DSL runtime executor."""

import pytest
from pathlib import Path
from zil.dsl import (
    GameState,
    ObjectState,
    Runtime,
    ActionResult,
    MoveResult,
    load_world,
    parse_world,
)


@pytest.fixture
def simple_world_yaml():
    return """
meta:
  name: "Test World"
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

  BOX:
    description: "wooden box"
    initial_location: ROOM-1
    flags:
      - CONTBIT
      - OPENBIT
"""


@pytest.fixture
def action_world_yaml():
    return """
meta:
  name: "Action Test World"
  starting_room: ROOM-1

rooms:
  ROOM-1:
    description: "Test Room"

objects:
  KEY:
    description: "brass key"
    initial_location: ROOM-1
    flags:
      - TAKEBIT

  LAMP:
    description: "brass lamp"
    initial_location: ROOM-1
    flags:
      - TAKEBIT
      - LIGHTBIT

  STATUE:
    description: "stone statue"
    initial_location: ROOM-1
    # No TAKEBIT - can't take it

actions:
  TAKE:
    syntax:
      - "take [object]"
    preconditions:
      - "(has-flag ?obj TAKEBIT)"
      - "(not (held? ?obj))"
    effects:
      - "(move! ?obj PLAYER)"
    messages:
      success: "Taken."
      failure: "You can't take that."

  DROP:
    syntax:
      - "drop [object]"
    preconditions:
      - "(held? ?obj)"
    effects:
      - "(move! ?obj (loc PLAYER))"
    messages:
      success: "Dropped."
      failure: "You're not holding that."

  LIGHT:
    syntax:
      - "light [object]"
    preconditions:
      - "(has-flag ?obj LIGHTBIT)"
      - "(held? ?obj)"
    effects:
      - "(set-flag! ?obj ONBIT)"
    messages:
      success: "The lamp is now lit."
      failure: "You can't light that."
"""


@pytest.fixture
def terminal_room_path():
    return Path(__file__).parent.parent / "games" / "lurkinghorror" / "terminal_room.yaml"


class TestGameState:
    """Test immutable game state."""

    def test_create_from_world(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        state = GameState.from_world(world)

        assert state.player_location == "ROOM-1"
        assert state.get_object("KEY") is not None
        assert state.get_object("BOX") is not None

    def test_object_state(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        state = GameState.from_world(world)

        key = state.get_object("KEY")
        assert key is not None
        assert key.location == "ROOM-1"
        assert "TAKEBIT" in key.flags

    def test_immutable_object_update(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        state = GameState.from_world(world)

        key = state.get_object("KEY")
        new_key = key.with_location("PLAYER")

        # Original unchanged
        assert key.location == "ROOM-1"
        # New state has update
        assert new_key.location == "PLAYER"

    def test_immutable_state_update(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        state = GameState.from_world(world)

        key = state.get_object("KEY")
        new_key = key.with_location("PLAYER")
        new_state = state.with_object(new_key)

        # Original state unchanged
        assert state.get_object("KEY").location == "ROOM-1"
        # New state has update
        assert new_state.get_object("KEY").location == "PLAYER"

    def test_with_player_location(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        state = GameState.from_world(world)

        new_state = state.with_player_location("ROOM-2")

        assert state.player_location == "ROOM-1"
        assert new_state.player_location == "ROOM-2"

    def test_with_global(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        state = GameState.from_world(world)

        new_state = state.with_global("score", 10)

        assert state.get_global("score") is None
        assert new_state.get_global("score") == 10


class TestObjectState:
    """Test ObjectState immutable updates."""

    def test_with_flag(self):
        obj = ObjectState(
            name="TEST",
            location="ROOM",
            flags=frozenset(["A"]),
            properties=(),
        )

        new_obj = obj.with_flag("B")

        assert "A" in obj.flags
        assert "B" not in obj.flags
        assert "A" in new_obj.flags
        assert "B" in new_obj.flags

    def test_without_flag(self):
        obj = ObjectState(
            name="TEST",
            location="ROOM",
            flags=frozenset(["A", "B"]),
            properties=(),
        )

        new_obj = obj.without_flag("B")

        assert "B" in obj.flags
        assert "B" not in new_obj.flags
        assert "A" in new_obj.flags

    def test_with_property(self):
        obj = ObjectState(
            name="TEST",
            location="ROOM",
            flags=frozenset(),
            properties=(("size", 10),),
        )

        new_obj = obj.with_property("weight", 5)

        assert obj.get_property("weight") is None
        assert new_obj.get_property("weight") == 5
        assert new_obj.get_property("size") == 10


class TestRuntime:
    """Test runtime action execution."""

    def test_create_runtime(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        assert runtime.state.player_location == "ROOM-1"

    def test_describe_room(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        desc = runtime.describe_room()
        assert "First Room" in desc

    def test_describe_exits(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        exits = runtime.describe_exits()
        assert "north" in exits

    def test_get_visible_objects(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        visible = runtime.get_visible_objects()
        assert "KEY" in visible
        assert "BOX" in visible


class TestMovement:
    """Test movement between rooms."""

    def test_move_success(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        result = runtime.move("north")

        assert result.success
        assert result.new_state is not None
        assert result.new_state.player_location == "ROOM-2"

    def test_move_no_exit(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        result = runtime.move("west")

        assert not result.success
        assert "can't go west" in result.message

    def test_move_immutable(self, simple_world_yaml):
        world = parse_world(simple_world_yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        result = runtime.move("north")

        # Original runtime state unchanged
        assert runtime.state.player_location == "ROOM-1"
        # Result has new state
        assert result.new_state.player_location == "ROOM-2"


class TestActions:
    """Test action execution."""

    def test_take_success(self, action_world_yaml):
        world = parse_world(action_world_yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        result = runtime.execute_action("TAKE", "KEY")

        assert result.success
        assert result.message == "Taken."
        assert result.new_state is not None

        # Check object moved
        key = result.new_state.get_object("KEY")
        assert key.location == "PLAYER"

    def test_take_failure_no_takebit(self, action_world_yaml):
        world = parse_world(action_world_yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        result = runtime.execute_action("TAKE", "STATUE")

        assert not result.success
        assert result.message == "You can't take that."
        assert result.failed_precondition is not None

    def test_take_already_held(self, action_world_yaml):
        world = parse_world(action_world_yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        # First take
        result1 = runtime.execute_action("TAKE", "KEY")
        assert result1.success

        # Try to take again from new state
        runtime.state = result1.new_state
        result2 = runtime.execute_action("TAKE", "KEY")

        assert not result2.success

    def test_drop_success(self, action_world_yaml):
        world = parse_world(action_world_yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        # First take the key
        take_result = runtime.execute_action("TAKE", "KEY")
        assert take_result.success
        runtime.state = take_result.new_state

        # Now drop it
        drop_result = runtime.execute_action("DROP", "KEY")

        assert drop_result.success
        assert drop_result.message == "Dropped."

        # Key should be back in room
        key = drop_result.new_state.get_object("KEY")
        assert key.location == "ROOM-1"

    def test_drop_failure_not_held(self, action_world_yaml):
        world = parse_world(action_world_yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        result = runtime.execute_action("DROP", "KEY")

        assert not result.success
        assert result.message == "You're not holding that."

    def test_light_lamp(self, action_world_yaml):
        world = parse_world(action_world_yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        # Take lamp first
        take_result = runtime.execute_action("TAKE", "LAMP")
        assert take_result.success
        runtime.state = take_result.new_state

        # Light it
        light_result = runtime.execute_action("LIGHT", "LAMP")

        assert light_result.success
        lamp = light_result.new_state.get_object("LAMP")
        assert "ONBIT" in lamp.flags

    def test_unknown_action(self, action_world_yaml):
        world = parse_world(action_world_yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        result = runtime.execute_action("FLY", "KEY")

        assert not result.success
        assert "Unknown action" in result.message


class TestTransitions:
    """Test transition blocking."""

    def test_blocked_transition(self):
        yaml = """
meta:
  name: "Blocking Test"
  starting_room: ROOM-1

rooms:
  ROOM-1:
    description: "Room with guard"
    exits:
      north: ROOM-2
  ROOM-2:
    description: "Guarded room"

objects:
  TREASURE:
    description: "golden treasure"
    initial_location: ROOM-1
    flags:
      - TAKEBIT

actions:
  TAKE:
    preconditions:
      - "(has-flag ?obj TAKEBIT)"
    effects:
      - "(move! ?obj PLAYER)"
    messages:
      success: "Taken."
      failure: "Can't take."

transitions:
  guard-blocks:
    trigger:
      action: GO
      direction: north
    when: "(held? TREASURE)"
    message: "The guard stops you!"
"""
        world = parse_world(yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        # Can move without treasure
        result1 = runtime.move("north")
        assert result1.success

        # Take treasure
        runtime.state = state  # Reset
        take_result = runtime.execute_action("TAKE", "TREASURE")
        assert take_result.success
        runtime.state = take_result.new_state

        # Can't move with treasure
        result2 = runtime.move("north")
        assert not result2.success
        assert "guard stops you" in result2.message
        assert result2.blocked_by == "guard-blocks"


class TestConditionalExits:
    """Test exits with conditions."""

    def test_conditional_exit_blocked(self):
        yaml = """
meta:
  name: "Conditional Exit Test"
  starting_room: ROOM-1

rooms:
  ROOM-1:
    description: "Room with locked door"
    exits:
      north:
        to: ROOM-2
        when: "(has-flag DOOR UNLOCKED)"
  ROOM-2:
    description: "Beyond the door"

objects:
  DOOR:
    description: "wooden door"
    initial_location: ROOM-1
    flags:
      - LOCKED
"""
        world = parse_world(yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        result = runtime.move("north")

        assert not result.success
        assert "can't go north" in result.message


class TestInvariants:
    """Test invariant enforcement."""

    def test_invariant_violation(self):
        yaml = """
meta:
  name: "Invariant Test"
  starting_room: ROOM-1

rooms:
  ROOM-1:
    description: "Lit room"
    flags:
      - ONBIT
  ROOM-2:
    description: "Dark room"
    # No ONBIT - dark

objects:
  LAMP:
    description: "lamp"
    initial_location: ROOM-1
    flags:
      - TAKEBIT
      - LIGHTBIT

invariants:
  must-have-light:
    check: |
      (or
        (has-flag (loc PLAYER) ONBIT)
        (any (inventory PLAYER) (lambda (x) (and (has-flag x LIGHTBIT) (has-flag x ONBIT)))))
    on_violation: "It is pitch dark!"
"""
        world = parse_world(yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        # Moving to dark room without lit lamp should fail invariant
        # First, the room exists
        assert "ROOM-2" in world.rooms

        # Add exit to dark room
        world.rooms["ROOM-1"].exits["north"] = world.rooms["ROOM-1"].exits.get(
            "north"
        ) or type(world.rooms["ROOM-1"].exits.get("south", None))

        # For this test, let's check the invariant directly
        # by modifying state to be in dark room
        dark_state = state.with_player_location("ROOM-2")
        runtime.state = dark_state

        # Check invariant should fail
        result = runtime._check_invariants(dark_state)
        assert result is not None
        assert result[0] == "must-have-light"
        assert "pitch dark" in result[1]


class TestLurkingHorrorTerminalRoom:
    """Test with real Lurking Horror Terminal Room."""

    def test_load_and_create_state(self, terminal_room_path):
        if not terminal_room_path.exists():
            pytest.skip("Terminal room file not found")

        world = load_world(str(terminal_room_path))
        state = GameState.from_world(world)

        assert state.player_location == "TERMINAL-ROOM"
        assert state.get_object("HACKER") is not None
        assert state.get_object("CHAIR") is not None
        assert state.get_object("PC") is not None

    def test_describe_terminal_room(self, terminal_room_path):
        if not terminal_room_path.exists():
            pytest.skip("Terminal room file not found")

        world = load_world(str(terminal_room_path))
        state = GameState.from_world(world)
        runtime = Runtime(state)

        desc = runtime.describe_room()
        assert "computer terminals" in desc.lower()

    def test_movement_in_terminal_room(self, terminal_room_path):
        if not terminal_room_path.exists():
            pytest.skip("Terminal room file not found")

        world = load_world(str(terminal_room_path))
        state = GameState.from_world(world)
        runtime = Runtime(state)

        # Can move south to CS-2ND
        result = runtime.move("south")
        assert result.success
        assert result.new_state.player_location == "CS-2ND"

    def test_take_chair_blocks_exit(self, terminal_room_path):
        if not terminal_room_path.exists():
            pytest.skip("Terminal room file not found")

        world = load_world(str(terminal_room_path))
        state = GameState.from_world(world)
        runtime = Runtime(state)

        # Take the chair
        take_result = runtime.execute_action("TAKE", "CHAIR")
        assert take_result.success
        runtime.state = take_result.new_state

        # Now try to leave - hacker should block
        move_result = runtime.move("south")
        assert not move_result.success
        assert "hacker" in move_result.message.lower()

    def test_examine_objects(self, terminal_room_path):
        if not terminal_room_path.exists():
            pytest.skip("Terminal room file not found")

        world = load_world(str(terminal_room_path))
        state = GameState.from_world(world)
        runtime = Runtime(state)

        visible = runtime.get_visible_objects()
        assert "HACKER" in visible
        assert "CHAIR" in visible
        assert "PC" in visible


class TestVictoryDefeat:
    """Test win/lose condition checking."""

    def test_victory_condition(self):
        yaml = """
meta:
  name: "Victory Test"
  starting_room: ROOM-1

rooms:
  ROOM-1:
    description: "Test room"

objects:
  TROPHY:
    description: "golden trophy"
    initial_location: ROOM-1
    flags:
      - TAKEBIT

actions:
  TAKE:
    preconditions:
      - "(has-flag ?obj TAKEBIT)"
    effects:
      - "(move! ?obj PLAYER)"
    messages:
      success: "Taken."

victory:
  when: "(held? TROPHY)"
  message: "You win!"
"""
        world = parse_world(yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        # Not victory yet
        won, msg = runtime.check_victory()
        assert not won

        # Take trophy
        result = runtime.execute_action("TAKE", "TROPHY")
        assert result.success
        runtime.state = result.new_state

        # Now should be victory
        won, msg = runtime.check_victory()
        assert won
        assert msg == "You win!"

    def test_defeat_condition(self):
        yaml = """
meta:
  name: "Defeat Test"
  starting_room: ROOM-1

rooms:
  ROOM-1:
    description: "Room with trap"

objects:
  LEVER:
    description: "suspicious lever"
    initial_location: ROOM-1
    flags:
      - PULLED

defeat:
  trap-sprung:
    when: "(has-flag LEVER PULLED)"
    message: "A trap springs! Game over."
"""
        world = parse_world(yaml)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        # Should be defeated (lever starts pulled)
        name, msg = runtime.check_defeat()
        assert name == "trap-sprung"
        assert "trap springs" in msg.lower()
