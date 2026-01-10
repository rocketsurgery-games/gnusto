"""Tests for GRUE runtime."""

import pytest
from pathlib import Path

from grue import (
    parse_grue,
    load_grue,
    GrueRuntime,
    ActionResult,
)


class TestBasicRuntime:
    """Test basic runtime functionality."""

    def test_init_state(self):
        """Runtime initializes state from world definition."""
        source = """
        (room LOBBY :description "A lobby" :flags (LIT))
        (object PLAYER :location LOBBY :flags (PERSON))
        (object KEY :location LOBBY :flags (TAKEABLE))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert runtime.get_player_location() == "LOBBY"
        assert "KEY" in runtime.get_visible_objects()
        assert len(runtime.get_inventory()) == 0

    def test_room_description(self):
        """Can get room descriptions."""
        source = """
        (room LOBBY :description "The main lobby")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert runtime.get_room_description() == "The main lobby"
        assert runtime.get_room_description("LOBBY") == "The main lobby"

    def test_exits(self):
        """Can get available exits."""
        source = """
        (room LOBBY
          :description "A lobby"
          :exits ((north :to HALLWAY) (east :to GARDEN)))
        (room HALLWAY :description "A hallway")
        (room GARDEN :description "A garden")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        exits = runtime.get_exits()
        assert exits["north"] == "HALLWAY"
        assert exits["east"] == "GARDEN"


class TestSimpleMovement:
    """Test basic movement."""

    def test_go_direction(self):
        """Can move through simple exits."""
        source = """
        (room LOBBY :description "A lobby" :exits ((north :to HALLWAY)))
        (room HALLWAY :description "A hallway")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert runtime.get_player_location() == "LOBBY"

        result = runtime.do("go", direction="north")
        assert result.outcome == "success"
        assert runtime.get_player_location() == "HALLWAY"

    def test_go_invalid_direction(self):
        """Cannot go in invalid direction."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("go", direction="north")
        assert result.outcome == "blocked"
        assert result.reason == "no-exit"


class TestBehaviorExecution:
    """Test behavior execution."""

    def test_simple_success_behavior(self):
        """Simple always-succeeds behavior."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object DOOR
          :location LOBBY
          :flags (DOOR)
          :behaviors
            ((open
               (case true
                 :outcome success
                 :effects ()))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("open", "DOOR")
        assert result.outcome == "success"

    def test_conditional_behavior(self):
        """Behavior with conditions."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object DOOR
          :location LOBBY
          :flags (DOOR LOCKED)
          :behaviors
            ((open
               (case (not (has-flag self LOCKED))
                 :outcome success
                 :effects ())
               (case true
                 :outcome blocked
                 :reason locked))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Door is locked, so should be blocked
        result = runtime.do("open", "DOOR")
        assert result.outcome == "blocked"
        assert result.reason == "locked"

    def test_behavior_with_effects(self):
        """Behavior that modifies state."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object DOOR
          :location LOBBY
          :flags (DOOR LOCKED)
          :behaviors
            ((unlock
               (case (has-flag self LOCKED)
                 :outcome success
                 :effects ((clear-flag! self LOCKED))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Door starts locked
        assert "LOCKED" in runtime.state.objects["DOOR"].flags

        result = runtime.do("unlock", "DOOR")
        assert result.outcome == "success"

        # Now unlocked
        assert "LOCKED" not in runtime.state.objects["DOOR"].flags

    def test_behavior_with_context(self):
        """Behavior returns context hints."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object DOOR
          :location LOBBY
          :behaviors
            ((open
               (case true
                 :outcome success
                 :effects ()
                 :context ((mechanism push-bar))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("open", "DOOR")
        assert result.outcome == "success"
        assert ("mechanism", "push-bar") in result.context

    def test_no_behavior_for_verb(self):
        """Object without behavior for verb."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object ROCK :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("open", "ROCK")
        assert result.outcome == "blocked"
        assert result.reason == "no-behavior"


class TestMovementViaDoors:
    """Test movement through doors."""

    def test_door_with_through_behavior(self):
        """Exit via door triggers through behavior."""
        source = """
        (room OUTSIDE
          :description "Outside"
          :exits ((in :to LOBBY :via DOOR)))
        (room LOBBY :description "Lobby")
        (object PLAYER :location OUTSIDE)
        (object DOOR
          :location OUTSIDE
          :behaviors
            ((through
               (case true
                 :outcome redirect
                 :action (go :direction in)))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Going "in" should trigger DOOR's through behavior
        result = runtime.do("go", direction="in")
        # The redirect means we need to handle it
        # For now, the runtime returns redirect
        assert result.outcome == "redirect"


class TestVictoryDefeat:
    """Test win/lose conditions."""

    def test_victory_condition(self):
        """Victory condition check."""
        source = """
        (room LOBBY :description "A lobby")
        (room ENDROOM :description "The end")
        (object PLAYER :location LOBBY)
        (victory :when (= (loc PLAYER) ENDROOM))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert not runtime.check_victory()

        # Move player to end room
        runtime.state.objects["PLAYER"].location = "ENDROOM"
        assert runtime.check_victory()

    def test_defeat_condition(self):
        """Defeat condition check."""
        source = """
        (room LOBBY :description "A lobby" :flags (LIT))
        (room DARKNESS :description "Darkness")
        (object PLAYER :location LOBBY)
        (defeat EATEN-BY-GRUE :when (= (loc PLAYER) DARKNESS))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert runtime.check_defeat() is None

        runtime.state.objects["PLAYER"].location = "DARKNESS"
        assert runtime.check_defeat() == "EATEN-BY-GRUE"


class TestOutsideDoorExample:
    """Test with the actual outside-door.grue example."""

    @pytest.fixture
    def runtime(self):
        example_path = Path(__file__).parent.parent / "examples" / "outside-door.grue"
        if not example_path.exists():
            pytest.skip("Example file not found")
        world = load_grue(example_path)
        return GrueRuntime(world)

    def test_initial_state(self, runtime):
        """Player starts at MASS-AVE."""
        assert runtime.get_player_location() == "MASS-AVE"
        assert "MASTER-KEY" in runtime.get_inventory()

    def test_open_door_from_outside(self, runtime):
        """Opening door from outside at push-bar location succeeds."""
        result = runtime.do("open", "OUTSIDE-DOOR")
        assert result.outcome == "success"
        assert ("mechanism", "push-bar") in result.context

    def test_unlock_door_with_key_from_outside(self, runtime):
        """Unlocking door from outside with physical key fails."""
        result = runtime.do("unlock", "OUTSIDE-DOOR", **{"with": "MASTER-KEY"})
        assert result.outcome == "blocked"
        assert result.reason == "wrong-key-type"

    def test_victory_in_hallway(self, runtime):
        """Victory when player reaches hallway."""
        assert not runtime.check_victory()

        runtime.state.objects["PLAYER"].location = "HALLWAY"
        assert runtime.check_victory()

    def test_close_door(self, runtime):
        """Closing door always succeeds (spring-loaded)."""
        result = runtime.do("close", "OUTSIDE-DOOR")
        assert result.outcome == "success"
        assert ("note", "spring-loaded") in result.context


class TestInventoryManagement:
    """Test object manipulation."""

    def test_visible_objects(self):
        """Objects in room are visible."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object KEY :location LOBBY :flags (TAKEABLE))
        (object COIN :location PLAYER :flags (TAKEABLE))
        (object HIDDEN :location ELSEWHERE)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        visible = runtime.get_visible_objects()
        assert "KEY" in visible
        assert "COIN" in visible  # In inventory is visible
        assert "HIDDEN" not in visible

    def test_inventory(self):
        """Objects with PLAYER location are inventory."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object KEY :location PLAYER :flags (TAKEABLE))
        (object LAMP :location LOBBY :flags (TAKEABLE))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        inv = runtime.get_inventory()
        assert "KEY" in inv
        assert "LAMP" not in inv


class TestReset:
    """Test state reset."""

    def test_reset_state(self):
        """Reset restores initial state."""
        source = """
        (room LOBBY :description "A lobby")
        (room GARDEN :description "A garden")
        (object PLAYER :location LOBBY)
        (object KEY :location LOBBY :flags (TAKEABLE))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Modify state
        runtime.state.objects["PLAYER"].location = "GARDEN"
        runtime.state.objects["KEY"].location = "PLAYER"
        runtime.state.globals["score"] = 100

        assert runtime.get_player_location() == "GARDEN"
        assert "KEY" in runtime.get_inventory()

        # Reset
        runtime.reset()

        assert runtime.get_player_location() == "LOBBY"
        assert "KEY" not in runtime.get_inventory()
        assert runtime.state.globals["score"] == 0
