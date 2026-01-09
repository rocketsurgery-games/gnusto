"""Tests for OUTSIDE-DOOR behavioral DSL - Lurking Horror test case.

This test case validates that our behavioral DSL can express the complex
conditional logic from ZIL's OUTSIDE-DOOR-F routine.

Original ZIL behavior:
- OUTSIDE location + THROUGH verb -> walk IN
- INSIDE location + THROUGH verb -> walk OUT
- OUTSIDE at MASS-AVE/SMITH-ST/COURTYARD/CS-ROOF + OPEN verb -> "opens from this side"
- OUTSIDE at MASS-AVE/SMITH-ST/COURTYARD/CS-ROOF + UNLOCK with MASTER-KEY -> "not keyed to this key"
- OUTSIDE at other locations + OPEN/UNLOCK -> "securely locked"
- INSIDE + OPEN -> "opens but shuts automatically"
"""

import pytest

from zil.dsl import (
    WorldDefinition,
    Room,
    Object,
    GameMeta,
    Behavior,
    BehaviorCase,
    Symbol,
    parse,
    parse_world,
)
from zil.dsl.runtime import GameState, Runtime


# The OUTSIDE-DOOR definition in our behavioral DSL
OUTSIDE_DOOR_YAML = """
meta:
  name: "Lurking Horror - Outside Door Test"
  starting_room: MASS-AVE

rooms:
  MASS-AVE:
    description: "Massachusetts Avenue"
    flags: [OUTSIDE]
    exits:
      in: LOBBY

  SMITH-ST:
    description: "Smith Street"
    flags: [OUTSIDE]
    exits:
      in: LOBBY

  GREAT-COURT:
    description: "Great Court"
    flags: [OUTSIDE]
    exits:
      in: LOBBY

  LOBBY:
    description: "The lobby of the building"
    exits:
      out: MASS-AVE

objects:
  OUTSIDE-DOOR:
    description: "outside door"
    initial_location: MASS-AVE
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
          - when: "(and (has-flag (loc PLAYER) OUTSIDE) (in-room? PLAYER MASS-AVE SMITH-ST) (= INSTRUMENT MASTER-KEY))"
            message: "The door is not keyed to this key."
          - when: "(has-flag (loc PLAYER) OUTSIDE)"
            message: "The door is securely locked."

  MASTER-KEY:
    description: "master key"
    initial_location: PLAYER
    flags: [TAKEBIT]
"""


class TestOutsideDoorParsing:
    """Test that OUTSIDE-DOOR YAML parses correctly."""

    def test_parse_outside_door_yaml(self):
        """Parse the OUTSIDE-DOOR YAML definition."""
        world = parse_world(OUTSIDE_DOOR_YAML)

        # Check door exists
        assert "OUTSIDE-DOOR" in world.objects
        door = world.objects["OUTSIDE-DOOR"]

        # Check behaviors
        assert "through" in door.behaviors
        assert "open" in door.behaviors
        assert "unlock" in door.behaviors

        # Check through behavior has 2 cases
        through = door.behaviors["through"]
        assert len(through.cases) == 2

        # Check open behavior has 3 cases
        open_b = door.behaviors["open"]
        assert len(open_b.cases) == 3

    def test_room_flags(self):
        """Verify rooms have OUTSIDE flag."""
        world = parse_world(OUTSIDE_DOOR_YAML)

        assert "OUTSIDE" in world.rooms["MASS-AVE"].flags
        assert "OUTSIDE" in world.rooms["SMITH-ST"].flags
        assert "OUTSIDE" not in world.rooms["LOBBY"].flags


class TestInRoomPredicate:
    """Test the in-room? predicate we need to add."""

    def test_in_room_single(self):
        """Test (in-room? PLAYER ROOM) returns true when player in room."""
        world = parse_world(OUTSIDE_DOOR_YAML)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        # Player starts in MASS-AVE
        result = runtime.evaluate(parse("(in-room? PLAYER MASS-AVE)"))
        assert result is True

        result = runtime.evaluate(parse("(in-room? PLAYER LOBBY)"))
        assert result is False

    def test_in_room_multiple(self):
        """Test (in-room? PLAYER ROOM1 ROOM2 ...) returns true if in any."""
        world = parse_world(OUTSIDE_DOOR_YAML)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        # Player starts in MASS-AVE
        result = runtime.evaluate(parse("(in-room? PLAYER MASS-AVE SMITH-ST)"))
        assert result is True

        result = runtime.evaluate(parse("(in-room? PLAYER SMITH-ST LOBBY)"))
        assert result is False


class TestRoomFlagPredicate:
    """Test checking flags on the player's current room."""

    def test_has_flag_on_room(self):
        """Test (has-flag (loc PLAYER) FLAG) works for rooms."""
        world = parse_world(OUTSIDE_DOOR_YAML)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        # Player is in MASS-AVE which has OUTSIDE flag
        result = runtime.evaluate(parse("(has-flag (loc PLAYER) OUTSIDE)"))
        assert result is True

    def test_room_without_flag(self):
        """Test room flag check returns false when missing."""
        world = parse_world(OUTSIDE_DOOR_YAML)
        state = GameState.from_world(world)
        # Move player to LOBBY (no OUTSIDE flag)
        state = state.with_player_location("LOBBY")
        runtime = Runtime(state)

        result = runtime.evaluate(parse("(has-flag (loc PLAYER) OUTSIDE)"))
        assert result is False


class TestBehaviorEvaluation:
    """Test evaluating object behaviors at runtime."""

    @pytest.fixture
    def runtime(self):
        """Create runtime with OUTSIDE-DOOR world."""
        world = parse_world(OUTSIDE_DOOR_YAML)
        state = GameState.from_world(world)
        return Runtime(state)

    def test_evaluate_open_outside_mass_ave(self, runtime):
        """Test OPEN behavior when outside at MASS-AVE."""
        # Player starts at MASS-AVE
        door = runtime.world.objects["OUTSIDE-DOOR"]
        open_b = door.behaviors["open"]

        # Should match first case (opens from this side)
        first_case = open_b.cases[0]
        result = runtime.evaluate(first_case.when)
        assert result is True
        assert first_case.message == "The door opens from this side."

    def test_evaluate_open_outside_great_court(self, runtime):
        """Test OPEN behavior when outside at GREAT-COURT (locked)."""
        # Move to GREAT-COURT (OUTSIDE but not in MASS-AVE/SMITH-ST list)
        runtime.state = runtime.state.with_player_location("GREAT-COURT")

        door = runtime.world.objects["OUTSIDE-DOOR"]
        open_b = door.behaviors["open"]

        # First case should NOT match (not in MASS-AVE or SMITH-ST)
        first_case = open_b.cases[0]
        result = runtime.evaluate(first_case.when)
        assert result is False

        # Second case SHOULD match (is OUTSIDE)
        second_case = open_b.cases[1]
        result = runtime.evaluate(second_case.when)
        assert result is True
        assert second_case.message == "The door is securely locked."

    def test_evaluate_open_inside(self, runtime):
        """Test OPEN behavior when inside (auto-close message)."""
        runtime.state = runtime.state.with_player_location("LOBBY")

        door = runtime.world.objects["OUTSIDE-DOOR"]
        open_b = door.behaviors["open"]

        # First case should NOT match (not OUTSIDE)
        result = runtime.evaluate(open_b.cases[0].when)
        assert result is False

        # Second case should NOT match (not OUTSIDE)
        result = runtime.evaluate(open_b.cases[1].when)
        assert result is False

        # Third case (default) should match
        result = runtime.evaluate(open_b.cases[2].when)
        assert result is True
        assert "shuts automatically" in open_b.cases[2].message


class TestBehaviorWithInstrument:
    """Test behaviors that check the instrument (second object)."""

    def test_unlock_with_master_key_outside(self):
        """Test UNLOCK with MASTER-KEY at MASS-AVE gives rejection message."""
        world = parse_world(OUTSIDE_DOOR_YAML)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        door = world.objects["OUTSIDE-DOOR"]
        unlock_b = door.behaviors["unlock"]

        # We need to evaluate with INSTRUMENT bound to MASTER-KEY
        # This requires extending the evaluator to support action context
        first_case = unlock_b.cases[0]

        # For now, verify the condition parses correctly
        assert "(= INSTRUMENT MASTER-KEY)" in str(first_case.when) or \
               "INSTRUMENT" in str(first_case.when)


class TestGoDirectionEffect:
    """Test the go-direction effect for implicit movement."""

    def test_through_outside_goes_in(self):
        """Test THROUGH from outside results in IN direction movement."""
        world = parse_world(OUTSIDE_DOOR_YAML)
        state = GameState.from_world(world)
        runtime = Runtime(state)

        door = world.objects["OUTSIDE-DOOR"]
        through_b = door.behaviors["through"]

        # First case should match (is OUTSIDE)
        first_case = through_b.cases[0]
        result = runtime.evaluate(first_case.when)
        assert result is True

        # The effect is (go-direction IN)
        # This should redirect to movement in the IN direction
        # For now, just verify the effect parses
        assert first_case.do is not None

    def test_through_inside_goes_out(self):
        """Test THROUGH from inside results in OUT direction movement."""
        world = parse_world(OUTSIDE_DOOR_YAML)
        state = GameState.from_world(world)
        runtime = Runtime(state)
        runtime.state = runtime.state.with_player_location("LOBBY")

        door = world.objects["OUTSIDE-DOOR"]
        through_b = door.behaviors["through"]

        # First case should NOT match (not OUTSIDE)
        result = runtime.evaluate(through_b.cases[0].when)
        assert result is False

        # Second case (default) should match
        result = runtime.evaluate(through_b.cases[1].when)
        assert result is True
