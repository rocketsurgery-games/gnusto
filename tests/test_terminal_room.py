"""Integration tests for games/lurkinghorror/terminal-room.grue.

Tests the complete terminal-room world file including:
- Room :on-enter nightmare wake-up
- Room :before-action hacker-helps interference and compulsion override
- Hacker exit barrier :through behavior
- Event queue integration (hacker-helps, compulsion, food-hint)
"""

import pytest
from pathlib import Path

from src.grue import load_grue, GrueRuntime


@pytest.fixture
def terminal_room_runtime():
    """Load terminal-room.grue and create a runtime."""
    path = Path("games/lurkinghorror/terminal-room.grue")
    world = load_grue(path)
    return GrueRuntime(world)


class TestNightmareWakeUp:
    """Test :on-enter nightmare wake-up when entering from platform-room."""

    def test_entering_from_platform_room_triggers_wake_up(self, terminal_room_runtime):
        """Entering terminal-room from platform-room triggers nightmare wake-up."""
        rt = terminal_room_runtime

        # Move player to platform-room first
        rt.state.objects["@player"].location = "@platform-room"
        assert rt.get_player_location() == "@platform-room"

        # Enter terminal-room from platform-room
        result = rt.do("_movement", "go", "north")

        assert result.outcome == "success"
        assert rt.get_player_location() == "@terminal-room"
        # Check on-enter triggered nightmare wake-up
        assert ("nightmare-wake", True) in result.context
        assert ("message", "You are awakened by the thump of your head hitting the keyboard.") in result.context
        # Check hacker-helps was queued
        assert rt.is_queued("hacker-helps")

    def test_entering_from_cs_2nd_no_wake_up(self, terminal_room_runtime):
        """Entering terminal-room from cs-2nd does NOT trigger wake-up."""
        rt = terminal_room_runtime

        # Move player to cs-2nd first
        rt.state.objects["@player"].location = "@cs-2nd"

        # Enter terminal-room from cs-2nd
        result = rt.do("_movement", "go", "north")

        assert result.outcome == "success"
        assert rt.get_player_location() == "@terminal-room"
        # No nightmare wake-up context
        assert ("nightmare-wake", True) not in result.context
        # hacker-helps should NOT be queued (unless already was)
        assert not rt.is_queued("hacker-helps")


class TestHackerHelpsInterference:
    """Test room :before-action blocking when hacker is helping."""

    def test_hacker_blocks_click_on_menu_box(self, terminal_room_runtime):
        """When hacker-helps is queued, clicking menu-box is blocked."""
        rt = terminal_room_runtime

        # Queue hacker-helps event
        rt.queue_event("hacker-helps")
        assert rt.is_queued("hacker-helps")

        # Try to click menu-box
        result = rt.do("@menu-box", "click")

        assert result.outcome == "blocked"
        assert result.reason == "hacker-interference"
        assert ("blocker", "@hacker") in result.context

    def test_hacker_blocks_rub_on_more_box(self, terminal_room_runtime):
        """When hacker-helps is queued, rubbing more-box is blocked."""
        rt = terminal_room_runtime

        # Queue hacker-helps event
        rt.queue_event("hacker-helps")

        # Move more-box to PC so it's visible
        rt.state.objects["@more-box"].location = "@pc"

        # Try to rub more-box
        result = rt.do("@more-box", "rub")

        # Should be blocked by room :before-action (rub is in the blocked verb list)
        assert result.outcome == "blocked"
        assert result.reason == "hacker-interference"

    def test_examine_allowed_during_hacker_helps(self, terminal_room_runtime):
        """Examining objects is still allowed when hacker is helping."""
        rt = terminal_room_runtime

        # Queue hacker-helps event
        rt.queue_event("hacker-helps")

        # Examining PC should be allowed (not in blocked verb list)
        result = rt.do("@pc", "examine")

        # Should succeed (examine is not blocked)
        assert result.outcome == "success"


class TestCompulsionOverride:
    """Test room :before-action compulsion (possession) override."""

    def test_compulsion_blocks_unrelated_actions(self, terminal_room_runtime):
        """When compulsion is queued, most actions are blocked."""
        rt = terminal_room_runtime

        # Queue compulsion event
        rt.queue_event("compulsion")
        assert rt.is_queued("compulsion")

        # Try to examine the chair (unrelated to MORE box)
        result = rt.do("@chair", "examine")

        assert result.outcome == "blocked"
        assert result.reason == "possessed"
        assert ("compelled", True) in result.context
        assert ("forced-target", "@more-box") in result.context

    def test_compulsion_allows_click_on_more_box(self, terminal_room_runtime):
        """When possessed, clicking more-box is allowed."""
        rt = terminal_room_runtime

        # Queue compulsion event
        rt.queue_event("compulsion")

        # Move more-box to PC
        rt.state.objects["@more-box"].location = "@pc"
        # Set odd-paper as read (required for more-box click)
        rt.state.objects["@odd-paper"].properties["read-page"] = True

        # Click more-box should be allowed
        result = rt.do("@more-box", "click")

        assert result.outcome == "success"

    def test_compulsion_allows_read_odd_paper(self, terminal_room_runtime):
        """When possessed, reading odd-paper is allowed."""
        rt = terminal_room_runtime

        # Queue compulsion event
        rt.queue_event("compulsion")

        # Move odd-paper to PC
        rt.state.objects["@odd-paper"].location = "@pc"

        # Read odd-paper should be allowed
        result = rt.do("@odd-paper", "read")

        assert result.outcome == "success"


class TestHackerExitBarrier:
    """Test the hacker-exit-barrier :through behavior."""

    def test_exit_blocked_when_holding_pc(self, terminal_room_runtime):
        """Cannot leave terminal-room while holding the PC."""
        rt = terminal_room_runtime

        # Give player the PC
        rt.state.objects["@pc"].location = "@player"

        # Try to go south
        result = rt.do("_movement", "go", "south")

        assert result.outcome == "blocked"
        assert result.reason == "tech-property"
        assert ("blocker", "@hacker") in result.context

    def test_exit_blocked_when_holding_chair(self, terminal_room_runtime):
        """Cannot leave terminal-room while holding the chair."""
        rt = terminal_room_runtime

        # Give player the chair
        rt.state.objects["@chair"].location = "@player"

        # Try to go out
        result = rt.do("_movement", "go", "out")

        assert result.outcome == "blocked"
        assert result.reason == "tech-property"

    def test_exit_allowed_empty_handed(self, terminal_room_runtime):
        """Can leave terminal-room when not holding tech property."""
        rt = terminal_room_runtime

        # Make sure PC and chair are not held
        rt.state.objects["@pc"].location = "@terminal-room"
        rt.state.objects["@chair"].location = "@terminal-room"

        # Go south
        result = rt.do("_movement", "go", "south")

        assert result.outcome == "success"
        assert rt.get_player_location() == "@cs-2nd"


class TestHackerHelpsEvent:
    """Test the hacker-helps turn-based event progression."""

    def test_hacker_helps_stage_1(self, terminal_room_runtime):
        """First turn of hacker-helps shows stage 1 message."""
        rt = terminal_room_runtime

        # Queue hacker-helps and set initial state
        rt.queue_event("hacker-helps")
        rt.state.globals["hacker-help"] = 0

        # Process turn - returns list of results
        results = rt.process_events()

        assert len(results) == 1
        result = results[0]
        assert result.outcome == "success"
        assert ("stage", 1) in result.context
        assert rt.state.globals["hacker-help"] == 1

    def test_hacker_helps_progresses_through_stages(self, terminal_room_runtime):
        """hacker-helps advances through all 4 stages."""
        rt = terminal_room_runtime

        # Queue hacker-helps
        rt.queue_event("hacker-helps")
        rt.state.globals["hacker-help"] = 0

        # Process 4 turns
        stages = []
        for _ in range(4):
            results = rt.process_events()
            for result in results:
                for key, val in result.context:
                    if key == "stage":
                        stages.append(val)

        assert stages == [1, 2, 3, 4]
        # After stage 4, event should be dequeued
        assert not rt.is_queued("hacker-helps")


class TestCompulsionEvent:
    """Test the compulsion turn-based event progression."""

    def test_compulsion_page_1(self, terminal_room_runtime):
        """First turn of compulsion shows page 1."""
        rt = terminal_room_runtime

        # Queue compulsion and set initial state
        rt.queue_event("compulsion")
        rt.state.globals["comp-cnt"] = 0

        # Process turn - returns list of results
        results = rt.process_events()

        assert len(results) == 1
        result = results[0]
        assert result.outcome == "success"
        assert ("page", 1) in result.context
        assert rt.state.globals["comp-cnt"] == 1

    def test_compulsion_page_4_teleports_to_yuggoth(self, terminal_room_runtime):
        """Page 4 of compulsion teleports player to yuggoth."""
        rt = terminal_room_runtime

        # Queue compulsion at page 3 (ready for final page)
        rt.queue_event("compulsion")
        rt.state.globals["comp-cnt"] = 3

        # Process turn - returns list of results
        results = rt.process_events()

        assert len(results) == 1
        result = results[0]
        assert ("page", 4) in result.context
        # Player teleported to yuggoth
        assert rt.get_player_location() == "@yuggoth"
        # Event dequeued
        assert not rt.is_queued("compulsion")


class TestHackerBehaviors:
    """Test hacker object behaviors."""

    def test_ask_about_keys_reveals_master_key(self, terminal_room_runtime):
        """Asking hacker about keys reveals the master key."""
        rt = terminal_room_runtime

        # Master key should not have TOUCHBIT initially
        assert not rt.get_object_flag("@master-key", "TOUCHBIT")

        # Ask about keys
        result = rt.do("@hacker", "ask-about", "@keys")

        assert result.outcome == "success"
        # Master key now has TOUCHBIT (revealed)
        assert rt.get_object_flag("@master-key", "TOUCHBIT")

    def test_give_hot_food_with_trade_gets_key(self, terminal_room_runtime):
        """Giving hot chinese food after proposing trade yields master key."""
        rt = terminal_room_runtime

        # Set up the trade scenario
        rt.state.globals["hacker-trade"] = True
        rt.state.objects["@carton"].location = "@player"
        rt.state.objects["@chinese-food"].location = "@carton"
        rt.state.objects["@chinese-food"].properties["heat"] = 12  # Hot enough

        # Give the carton
        result = rt.do("@hacker", "give", "@carton")

        assert result.outcome == "success"
        # Player should have master key
        assert rt.state.objects["@master-key"].location == "@player"
        # Trade flag cleared
        assert not rt.state.globals["hacker-trade"]

    def test_give_cold_food_rejected(self, terminal_room_runtime):
        """Giving cold chinese food is rejected."""
        rt = terminal_room_runtime

        rt.state.objects["@carton"].location = "@player"
        rt.state.objects["@chinese-food"].location = "@carton"
        rt.state.objects["@chinese-food"].properties["heat"] = 0  # Cold

        result = rt.do("@hacker", "give", "@carton")

        assert result.outcome == "blocked"
        assert result.reason == "food-cold"


class TestPCBehaviors:
    """Test PC object behaviors."""

    def test_turn_on_pc(self, terminal_room_runtime):
        """Can turn on the PC when plugged in."""
        rt = terminal_room_runtime

        # PC starts plugged in
        rt.state.objects["@pc"].properties["unplugged"] = False
        rt.clear_object_flag("@pc", "POWER")

        result = rt.do("@pc", "turn-on")

        assert result.outcome == "success"
        assert rt.get_object_flag("@pc", "POWER")

    def test_turn_on_unplugged_pc_fails(self, terminal_room_runtime):
        """Cannot turn on PC when unplugged."""
        rt = terminal_room_runtime

        rt.state.objects["@pc"].properties["unplugged"] = True

        result = rt.do("@pc", "turn-on")

        assert result.outcome == "blocked"
        assert result.reason == "unplugged"

    def test_turn_off_blocked_during_hacker_helps(self, terminal_room_runtime):
        """Cannot turn off PC while hacker is helping."""
        rt = terminal_room_runtime

        # Turn on PC and queue hacker-helps
        rt.set_object_flag("@pc", "POWER")
        rt.queue_event("hacker-helps")

        result = rt.do("@pc", "turn-off")

        assert result.outcome == "blocked"
        assert result.reason == "hacker-interference"
