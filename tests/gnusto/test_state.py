"""Tests for gnusto game state serialization."""

import pytest
from gnusto.state import ObjectInfo, RoomInfo, ExitInfo, GameState


class TestObjectInfo:
    """Test ObjectInfo dataclass."""

    def test_basic_object(self):
        obj = ObjectInfo(
            id="@lantern",
            description="A brass lantern",
        )
        assert obj.id == "@lantern"
        assert obj.description == "A brass lantern"
        assert obj.ldesc == ""
        assert obj.behaviors == []
        assert obj.properties == {}
        assert obj.contents == []

    def test_object_with_behaviors(self):
        obj = ObjectInfo(
            id="@sword",
            description="A rusty sword",
            behaviors=["take", "drop", "attack <target>"],
        )
        assert obj.behaviors == ["take", "drop", "attack <target>"]

    def test_object_with_contents(self):
        coin = ObjectInfo(id="@coin", description="A gold coin")
        bag = ObjectInfo(
            id="@bag",
            description="A leather bag",
            contents=[coin],
        )
        assert len(bag.contents) == 1
        assert bag.contents[0].id == "@coin"

    def test_nested_contents(self):
        key = ObjectInfo(id="@key", description="A small key")
        box = ObjectInfo(id="@box", description="A wooden box", contents=[key])
        chest = ObjectInfo(id="@chest", description="A chest", contents=[box])

        assert chest.contents[0].id == "@box"
        assert chest.contents[0].contents[0].id == "@key"


class TestRoomInfo:
    """Test RoomInfo dataclass."""

    def test_room_info(self):
        room = RoomInfo(id="@kitchen", description="A small kitchen")
        assert room.id == "@kitchen"
        assert room.description == "A small kitchen"


class TestExitInfo:
    """Test ExitInfo dataclass."""

    def test_simple_exit(self):
        exit = ExitInfo(
            direction="north",
            destination_id="@hallway",
            destination_name="Hallway",
        )
        assert exit.direction == "north"
        assert exit.destination_id == "@hallway"
        assert exit.destination_name == "Hallway"
        assert exit.via is None

    def test_exit_with_via(self):
        exit = ExitInfo(
            direction="up",
            destination_id="@second-floor",
            destination_name="Second Floor",
            via="an old wooden staircase",
        )
        assert exit.via == "an old wooden staircase"


class TestGameState:
    """Test GameState dataclass and formatting."""

    def test_empty_state(self):
        state = GameState(
            room="@start",
            room_name="Starting Room",
            room_description="You are in a bare room.",
            visible_objects=[],
            inventory=[],
            exits=[],
        )
        assert state.room == "@start"
        assert state.room_name == "Starting Room"

    def test_to_context_string_basic(self):
        state = GameState(
            room="@kitchen",
            room_name="Kitchen",
            room_description="A cozy kitchen with a warm stove.",
            visible_objects=[],
            inventory=[],
            exits=[],
        )
        context = state.to_context_string()

        assert "## Current Location: @kitchen" in context
        assert "A cozy kitchen with a warm stove." in context
        assert "**Exits:** none" in context
        assert "**Visible objects:** none" in context
        assert "**Inventory:** empty" in context

    def test_to_context_string_with_exits(self):
        state = GameState(
            room="@kitchen",
            room_name="Kitchen",
            room_description="A kitchen.",
            visible_objects=[],
            inventory=[],
            exits=[
                ExitInfo("north", "@dining-room", "Dining Room"),
                ExitInfo("east", "@pantry", "Pantry"),
            ],
        )
        context = state.to_context_string()

        assert "north -> Dining Room" in context
        assert "east -> Pantry" in context

    def test_to_context_string_with_via(self):
        state = GameState(
            room="@lobby",
            room_name="Lobby",
            room_description="A hotel lobby.",
            visible_objects=[],
            inventory=[],
            exits=[
                ExitInfo("up", "@second-floor", "Second Floor", via="the elevator doors"),
            ],
        )
        context = state.to_context_string()

        assert "up -> Second Floor (via the elevator doors)" in context

    def test_to_context_string_with_objects(self):
        lantern = ObjectInfo(
            id="@lantern",
            description="A brass lantern",
            behaviors=["take", "light"],
        )
        state = GameState(
            room="@cellar",
            room_name="Cellar",
            room_description="A dark cellar.",
            visible_objects=[lantern],
            inventory=[],
            exits=[],
        )
        context = state.to_context_string()

        assert "**Visible objects:**" in context
        assert "@lantern: A brass lantern [actions: take, light]" in context

    def test_to_context_string_with_inventory(self):
        key = ObjectInfo(
            id="@key",
            description="A rusty key",
            behaviors=["drop"],
        )
        state = GameState(
            room="@hallway",
            room_name="Hallway",
            room_description="A long hallway.",
            visible_objects=[],
            inventory=[key],
            exits=[],
        )
        context = state.to_context_string()

        assert "**Inventory:**" in context
        assert "@key: A rusty key [actions: drop]" in context

    def test_to_context_string_nested_objects(self):
        coin = ObjectInfo(id="@coin", description="A gold coin", behaviors=["take"])
        bag = ObjectInfo(
            id="@bag",
            description="A leather bag",
            behaviors=["take", "open"],
            contents=[coin],
        )
        state = GameState(
            room="@room",
            room_name="Room",
            room_description="A room.",
            visible_objects=[bag],
            inventory=[],
            exits=[],
        )
        context = state.to_context_string()

        # Both bag and nested coin should appear
        assert "@bag:" in context
        assert "@coin:" in context

    def test_to_context_string_with_vehicle(self):
        state = GameState(
            room="@highway",
            room_name="Highway",
            room_description="A dusty highway.",
            visible_objects=[],
            inventory=[],
            exits=[],
            vehicle=("car", "in"),
        )
        context = state.to_context_string()

        assert "(You are in the car)" in context

    def test_nearby_rooms(self):
        state = GameState(
            room="@center",
            room_name="Center",
            room_description="The center.",
            visible_objects=[],
            inventory=[],
            exits=[],
            nearby_rooms=[
                RoomInfo("@north", "North Room"),
                RoomInfo("@south", "South Room"),
            ],
        )
        assert len(state.nearby_rooms) == 2
        assert state.nearby_rooms[0].id == "@north"


class TestFormatBehavior:
    """Test behavior formatting helper."""

    def test_format_no_params(self):
        from gnusto.state import _format_behavior

        assert _format_behavior("take", []) == "take"

    def test_format_single_param(self):
        from gnusto.state import _format_behavior

        assert _format_behavior("give", ["recipient"]) == "give <recipient>"

    def test_format_multiple_params(self):
        from gnusto.state import _format_behavior

        assert _format_behavior("put", ["item", "container"]) == "put <item> <container>"
