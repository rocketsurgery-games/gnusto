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
    """

    def test_can_call_elevator(self, game):
        """Can call the elevator using call buttons."""
        # Go to cs-2nd (has floor property)
        game.do("_movement", "go", "south")
        assert game.get_player_location() == "@cs-2nd"

        # Push the down button to call elevator
        result = game.do("@down-button", "push")
        assert result.outcome == "success"

        # Wait for elevator to arrive and open doors
        # Takes ~6 turns: queue(1) -> start moving(2) -> arrive(4) -> open doors(6)
        for _ in range(8):
            game.process_events()

        # Elevator door should be open
        door = game.state.objects.get("@elevator-door-2")
        assert door.properties.get("OPENBIT")

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

    def test_can_traverse_infinite_corridor(self, game):
        """Can traverse full infinite corridor to reach chemistry building.

        The floor waxer patrols the corridor. You must wait for it to pass
        before you can proceed through each section.
        """
        # Navigate to inf-1
        game.do("_movement", "go", "south")
        game.do("_movement", "go", "down")
        game.do("_movement", "go", "down")
        game.do("_movement", "go", "west")
        game.do("_movement", "go", "west")
        game.do("_movement", "go", "up")
        game.do("_movement", "go", "south")  # inf-1

        # Traverse to inf-5, waiting for waxer when blocked
        for _ in range(4):
            result = game.do("_movement", "go", "east")
            # Wait until we can move (waxer patrol timing varies)
            for _ in range(20):  # Max wait to avoid infinite loop
                if result.outcome == "success":
                    break
                if result.outcome == "blocked" and result.reason == "waxer-blocking":
                    game.process_events()
                    result = game.do("_movement", "go", "east")
                else:
                    break  # Different kind of block, stop retrying
            assert result.outcome == "success", f"Failed at {game.get_player_location()}"

        assert game.get_player_location() == "@inf-5"

        # Go to chemistry building (may need to wait for waxer to leave)
        result = game.do("_movement", "go", "south")
        for _ in range(20):
            if result.outcome == "success":
                break
            if result.outcome == "blocked" and result.reason == "waxer-blocking":
                game.process_events()
                result = game.do("_movement", "go", "south")
            else:
                break
        assert result.outcome == "success"
        assert game.get_player_location() == "@chemistry-bldg"


class TestPart4Chemistry:
    """Part 4: Chemistry Lab & The Ceremony.

    1. Knock on door to meet professor
    2. Show suicide note to gain access to lab
    3. Survive the ritual by escaping through trapdoor
    4. Get the flask
    """

    def _navigate_to_chemistry(self, game):
        """Navigate from terminal room to chemistry building."""
        game.do("_movement", "go", "south")  # cs-2nd
        game.do("_movement", "go", "down")   # comp-center
        game.do("_movement", "go", "down")   # cs-basement
        game.do("_movement", "go", "west")   # aero-basement
        game.do("_movement", "go", "west")   # aero-stairs
        game.do("_movement", "go", "up")     # aero-lobby
        game.do("_movement", "go", "south")  # inf-1

        # Traverse infinite corridor, waiting for waxer if needed
        for _ in range(4):
            result = game.do("_movement", "go", "east")
            for _ in range(20):
                if result.outcome == "success":
                    break
                if result.outcome == "blocked" and result.reason == "waxer-blocking":
                    game.process_events()
                    result = game.do("_movement", "go", "east")
                else:
                    break

        # South to chemistry building
        result = game.do("_movement", "go", "south")
        for _ in range(20):
            if result.outcome == "success":
                break
            if result.outcome == "blocked" and result.reason == "waxer-blocking":
                game.process_events()
                result = game.do("_movement", "go", "south")
            else:
                break

    def test_can_knock_on_alchemy_door(self, game):
        """Can knock on the alchemy department door."""
        self._navigate_to_chemistry(game)
        assert game.get_player_location() == "@chemistry-bldg"

        result = game.do("@alchemy-door", "knock")
        assert result.outcome == "success"

        # Wait for professor to answer (3 turns)
        for _ in range(4):
            game.process_events()

        # Should now be in alchemy-dept with professor
        assert game.get_player_location() == "@alchemy-dept"
        assert "@professor" in game.get_visible_objects()

    def test_professor_blocks_lab_without_note(self, game):
        """Professor blocks entry to lab without showing the note."""
        self._navigate_to_chemistry(game)

        # Knock and enter
        game.do("@alchemy-door", "knock")
        for _ in range(4):
            game.process_events()

        # Try to go south to lab - should be blocked
        result = game.do("_movement", "go", "south")
        assert result.outcome == "blocked"
        assert result.reason == "professor-blocks"

    def test_can_show_note_to_professor(self, game):
        """Can show the suicide note to the professor."""
        self._navigate_to_chemistry(game)

        # Give player the note (in real game, this comes from PC)
        game.move_object("@note", "@player")

        # Knock and enter
        game.do("@alchemy-door", "knock")
        for _ in range(4):
            game.process_events()

        # Show note to professor
        result = game.do("@professor", "show", "@note")
        assert result.outcome == "success"

        # Professor should now allow lab entry
        result = game.do("_movement", "go", "south")
        assert result.outcome == "success"
        assert game.get_player_location() == "@alchemy-lab"


class TestPart5Hand:
    """Part 5: The Hand.

    1. Go to the Brown Building dome
    2. Find the bathtub with the mummified hand
    3. Take the hand
    4. Revive it in the vat (chemistry lab)
    5. Put the hyrax ring on the hand
    """

    def _wait_for_waxer(self, game, direction):
        """Try to move in direction, waiting for waxer if needed."""
        result = game.do("_movement", "go", direction)
        for _ in range(20):  # Max wait
            if result.outcome == "success":
                return result
            if result.outcome == "blocked" and result.reason == "waxer-blocking":
                game.process_events()
                result = game.do("_movement", "go", direction)
            else:
                return result
        return result

    def _navigate_to_brown_dome(self, game):
        """Navigate from terminal room to Brown Building dome."""
        # Terminal room -> cs-2nd -> comp-center -> cs-basement -> aero-basement
        game.do("_movement", "go", "south")  # cs-2nd
        game.do("_movement", "go", "down")   # comp-center
        game.do("_movement", "go", "down")   # cs-basement
        game.do("_movement", "go", "west")   # aero-basement
        game.do("_movement", "go", "west")   # aero-stairs
        game.do("_movement", "go", "up")     # aero-lobby

        # Traverse infinite corridor to inf-5 (waxer may block)
        game.do("_movement", "go", "south")  # inf-1
        for _ in range(4):
            self._wait_for_waxer(game, "east")

        # inf-5 -> nutrition-bldg (also via waxer barrier)
        self._wait_for_waxer(game, "north")  # nutrition-bldg
        game.do("_movement", "go", "down")   # brown-tunnel
        game.do("_movement", "go", "se")     # brown-basement
        game.do("_movement", "go", "up")     # brown-building
        game.do("_movement", "go", "up")     # brown-top-floor

    def test_can_navigate_to_brown_building(self, game):
        """Can navigate from terminal room to Brown Building top floor."""
        self._navigate_to_brown_dome(game)
        assert game.get_player_location() == "@brown-top-floor"

    def test_roof_door_is_locked(self, game):
        """Roof door starts locked."""
        self._navigate_to_brown_dome(game)

        result = game.do("@roof-door", "open")
        assert result.outcome == "blocked"
        assert result.reason == "locked"

    def test_can_unlock_roof_door_with_master_key(self, game):
        """Can unlock roof door with master key."""
        self._navigate_to_brown_dome(game)

        # Give player master key
        game.move_object("@master-key", "@player")

        # Unlock door
        result = game.do("@roof-door", "unlock", "@master-key")
        assert result.outcome == "success"

        # Now can open
        result = game.do("@roof-door", "open")
        assert result.outcome == "success"

        # Can go to roof
        result = game.do("_movement", "go", "west")
        assert result.outcome == "success"
        assert game.get_player_location() == "@brown-roof"

    def test_can_reach_inside_dome(self, game):
        """Can reach inside the dome after unlocking roof door."""
        self._navigate_to_brown_dome(game)
        game.move_object("@master-key", "@player")

        game.do("@roof-door", "unlock", "@master-key")
        game.do("@roof-door", "open")
        game.do("_movement", "go", "west")   # brown-roof
        game.do("_movement", "go", "up")     # inside-dome

        assert game.get_player_location() == "@inside-dome"
        # Tub is NDESCBIT (scenery) so check it exists via do
        result = game.do("@tub", "examine")
        assert result.outcome == "success"

    def test_can_find_hand_in_tub(self, game):
        """Can search tub to find mummified hand."""
        self._navigate_to_brown_dome(game)
        game.move_object("@master-key", "@player")

        game.do("@roof-door", "unlock", "@master-key")
        game.do("@roof-door", "open")
        game.do("_movement", "go", "west")
        game.do("_movement", "go", "up")

        # Search the tub
        result = game.do("@tub", "search")
        assert result.outcome == "success"
        # Check message is in context
        context_dict = dict(result.context)
        assert "hand" in context_dict.get("message", "").lower()

        # Hand should now be in tub (visible via its location)
        hand = game.state.objects.get("@mummified-hand")
        assert hand.location == "@tub"

    def test_can_take_mummified_hand(self, game):
        """Can take the mummified hand from the tub."""
        self._navigate_to_brown_dome(game)
        game.move_object("@master-key", "@player")

        game.do("@roof-door", "unlock", "@master-key")
        game.do("@roof-door", "open")
        game.do("_movement", "go", "west")
        game.do("_movement", "go", "up")
        game.do("@tub", "search")

        result = game.do("@mummified-hand", "take")
        assert result.outcome == "success"
        assert "@mummified-hand" in game.get_inventory()

    def test_can_dip_hand_in_elixir(self, game):
        """Can dip mummified hand in the elixir vat to start animation."""
        # Set up: player has hand, is in alchemy-lab with prof dead
        game.move_object("@mummified-hand", "@player")
        game.move_object("@player", "@alchemy-lab")
        game.state.globals["prof-dead"] = True  # Prof is gone
        game.state.objects["@alchemy-lab"].properties["ONBIT"] = True  # Lights on

        # Dip hand in vat
        result = game.do("@vat", "put", "@mummified-hand")
        assert result.outcome == "success"

        # Animation event should be queued
        assert "animate-hand" in game.state.queues

    def test_hand_animates_after_dipping(self, game):
        """Hand becomes animated (PERSON flag) after dipping and waiting."""
        game.move_object("@mummified-hand", "@player")
        game.move_object("@player", "@alchemy-lab")
        game.state.globals["prof-dead"] = True
        game.state.objects["@alchemy-lab"].properties["ONBIT"] = True

        # Dip hand
        game.do("@vat", "put", "@mummified-hand")

        # Process animation events (takes 3 turns)
        for _ in range(4):
            game.process_events()

        # Hand should now be animated (PERSON flag)
        hand = game.state.objects.get("@mummified-hand")
        assert hand.properties.get("PERSON"), "Hand should be animated"

    def test_can_put_ring_on_animated_hand(self, game):
        """Can put the brass hyrax ring on the animated hand."""
        # Set up animated hand
        game.move_object("@mummified-hand", "@player")
        game.state.objects["@mummified-hand"].properties["PERSON"] = True

        # Give player the ring
        game.move_object("@ring", "@player")

        # Put ring on hand
        result = game.do("@ring", "put-on", "@mummified-hand")
        assert result.outcome == "success"

        # Ring should be on the hand
        ring = game.state.objects.get("@ring")
        assert ring.location == "@mummified-hand"

    def test_ring_cannot_go_on_mummified_hand(self, game):
        """Cannot put ring on non-animated (mummified) hand."""
        game.move_object("@mummified-hand", "@player")
        game.move_object("@ring", "@player")

        # Hand is NOT animated
        game.state.objects["@mummified-hand"].properties["PERSON"] = False

        # Try to put ring on hand
        result = game.do("@ring", "put-on", "@mummified-hand")
        assert result.outcome == "blocked"
        assert result.reason == "too-dry"


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
