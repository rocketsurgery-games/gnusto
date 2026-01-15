"""Walkthrough validation tests for The Lurking Horror.

This test steps through the game walkthrough to validate the implementation.
Based on Doug Bolden's walkthrough from wyrmis.com.

Each test section corresponds to a part of the walkthrough.
Bugs discovered here should be filed as type=bug with LH tag.
"""

import pytest
from pathlib import Path

from grue import load_grue, GrueRuntime


@pytest.fixture
def game():
    """Load The Lurking Horror and return a fresh runtime."""
    # Load the DIRECTORY to include all .grue files
    path = Path(__file__).parent.parent / "games" / "lurkinghorror"
    world = load_grue(path)
    return GrueRuntime(world)


class TestPart1TerminalRoom:
    """Part 1: Terminal Room & Dream Sequence.

    1. Wake up in terminal room with the hacker
    2. Login to PC, read your assignment
    3. Fall asleep and experience the nightmare
    4. In the dream: get the smooth stone from the altar
    5. Wake up - the hacker will now help you
    """

    def test_initial_state(self, game):
        """Player starts in terminal room."""
        assert game.get_player_location() == "@terminal-room"

    def test_hacker_present(self, game):
        """Hacker is visible in terminal room."""
        visible = game.get_visible_objects()
        assert "@hacker" in visible

    def test_pc_present(self, game):
        """PC is visible in terminal room."""
        visible = game.get_visible_objects()
        assert "@pc" in visible

    def test_room_has_description(self, game):
        """Terminal room should have a description."""
        desc = game.get_room_description()
        # This is currently failing - room description is empty
        assert desc, "Room description should not be empty"

    def test_examine_hacker(self, game):
        """Can examine the hacker."""
        result = game.do("@hacker", "examine")
        assert result.outcome == "success"
        # Should get descriptive text
        assert result.context, "Examine should return context"

    def test_login_to_pc(self, game):
        """Can login to the PC."""
        result = game.do("@pc", "turn-on")
        assert result.outcome in ("success", "blocked"), f"Unexpected outcome: {result.outcome}"
        # Note: Actual login sequence may need specific commands


class TestPart2MasterKey:
    """Part 2: Getting the Master Key.

    1. Go to the kitchen (south then west from terminal room)
    2. Open refrigerator, get carton
    3. Open microwave, put carton in, set timer, start
    4. Wait for food to cook
    5. Take the hot container back to the hacker
    6. Ask about keys, propose trade, give food - get master key
    """

    def test_can_navigate_to_kitchen(self, game):
        """Can navigate from terminal room to kitchen."""
        result = game.do("_movement", "go", "south")
        assert result.outcome == "success"
        assert game.get_player_location() == "@cs-2nd"

        result = game.do("_movement", "go", "west")
        assert result.outcome == "success"
        assert game.get_player_location() == "@kitchen"

    def test_can_get_food_from_fridge(self, game):
        """Can open fridge and get the carton of food."""
        game.do("_movement", "go", "south")
        game.do("_movement", "go", "west")

        result = game.do("@refrigerator", "open")
        assert result.outcome == "success"

        # Carton should now be visible
        assert "@carton" in game.get_visible_objects()

        result = game.do("@carton", "take")
        assert result.outcome == "success"
        assert "@carton" in game.get_inventory()

    def test_can_heat_food_in_microwave(self, game):
        """Can heat food in microwave."""
        # Navigate and get food
        game.do("_movement", "go", "south")
        game.do("_movement", "go", "west")
        game.do("@refrigerator", "open")
        game.do("@carton", "take")

        # Heat sequence: open, put, set-timer, close, start
        game.do("@microwave", "open")
        result = game.do("@carton", "put", "@microwave")
        assert result.outcome == "success"

        result = game.do("@microwave", "set-timer", 300)
        assert result.outcome == "success"

        game.do("@microwave", "close")

        result = game.do("@microwave", "start")
        assert result.outcome == "success"

        # Process events to cook food
        for _ in range(10):
            game.process_events()

        # Food should be hot
        food = game.state.objects.get("@chinese-food")
        assert food.properties.get("heat", 0) >= 12, "Food should be hot enough"

    def test_complete_master_key_trade(self, game):
        """Complete sequence: heat food, trade with hacker for master key."""
        # Navigate and get food
        game.do("_movement", "go", "south")
        game.do("_movement", "go", "west")
        game.do("@refrigerator", "open")
        game.do("@carton", "take")

        # Heat food
        game.do("@microwave", "open")
        game.do("@carton", "put", "@microwave")
        game.do("@microwave", "set-timer", 300)
        game.do("@microwave", "close")
        game.do("@microwave", "start")

        for _ in range(10):
            game.process_events()

        # Get hot food
        game.do("@microwave", "open")
        game.do("@carton", "take")

        # Return to hacker
        game.do("_movement", "go", "east")
        game.do("_movement", "go", "north")

        # Ask about keys (reveals master key)
        result = game.do("@hacker", "ask-about", "@keyring")
        assert result.outcome == "success"

        # Propose trade
        result = game.do("@hacker", "trade", "@carton", "@master-key")
        assert result.outcome == "success"

        # Give food
        result = game.do("@hacker", "give", "@carton")
        assert result.outcome == "success"

        # Should have master key now
        assert "@master-key" in game.get_inventory()


class TestPart3Basement:
    """Part 3: Basement Exploration.

    1. Take the elevator down to the basement
    2. Get the crowbar from Brown basement
    3. Get the gloves from the alchemy lab
    4. Get the knife
    5. Use the forklift to access the "Tomb of the Unknown Tool"

    NOTE: Access to brown building/alchemy requires passing through the
    infinite corridor, which is currently blocked by bugs:
    - frotzlm-rk2: Elevator buttons not visible
    - frotzlm-68x: Floor waxer never starts patrolling
    """

    def test_can_reach_aero_basement(self, game):
        """Can navigate to aero basement via stairs."""
        game.do("_movement", "go", "south")  # cs-2nd
        game.do("_movement", "go", "down")   # comp-center
        game.do("_movement", "go", "down")   # cs-basement
        game.do("_movement", "go", "west")   # aero-basement

        assert game.get_player_location() == "@aero-basement"
        assert "@forklift" in game.get_visible_objects()

    def test_can_reach_infinite_corridor(self, game):
        """Can reach infinite corridor via aero lobby."""
        game.do("_movement", "go", "south")
        game.do("_movement", "go", "down")
        game.do("_movement", "go", "down")
        game.do("_movement", "go", "west")   # aero-basement
        game.do("_movement", "go", "west")   # aero-stairs
        game.do("_movement", "go", "up")     # aero-lobby
        game.do("_movement", "go", "south")  # inf-1

        assert game.get_player_location() == "@inf-1"

    @pytest.mark.xfail(reason="BUG frotzlm-68x: waxer blocks corridor, never patrols")
    def test_can_traverse_infinite_corridor(self, game):
        """Can traverse full infinite corridor to reach chemistry building."""
        # Navigate to inf-1
        game.do("_movement", "go", "south")
        game.do("_movement", "go", "down")
        game.do("_movement", "go", "down")
        game.do("_movement", "go", "west")
        game.do("_movement", "go", "west")
        game.do("_movement", "go", "up")
        game.do("_movement", "go", "south")  # inf-1

        # Traverse to inf-5
        for _ in range(4):
            result = game.do("_movement", "go", "east")
            assert result.outcome == "success", f"Failed at {game.get_player_location()}"

        assert game.get_player_location() == "@inf-5"

        # Go to chemistry building
        result = game.do("_movement", "go", "south")
        assert result.outcome == "success"
        assert game.get_player_location() == "@chemistry-bldg"


class TestPart4Chemistry:
    """Part 4: Chemistry Lab & The Ceremony.

    Blocked by infinite corridor traversal issues.
    """
    pass  # TODO: Implement after frotzlm-68x fixed


class TestPart5Hand:
    """Part 5: The Hand.

    Blocked by infinite corridor traversal issues.
    """
    pass  # TODO


class TestPart6SteamTunnels:
    """Part 6: Steam Tunnels.

    Blocked by infinite corridor traversal issues.
    """
    pass  # TODO


class TestPart7Maze:
    """Part 7: The Maze (Lair)."""
    pass  # TODO


class TestPart8FinalBattle:
    """Part 8: Final Battle."""
    pass  # TODO
