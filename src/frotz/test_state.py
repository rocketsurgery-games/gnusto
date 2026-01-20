"""Tests for game state extraction (LLM context building)."""

import pytest
from src.grue import load_grue
from src.grue.runtime import GrueRuntime
from src.frotz.state import get_game_state


@pytest.fixture
def runtime():
    """Create a runtime with the Lurking Horror game."""
    world = load_grue("games/lurkinghorror/")
    return GrueRuntime(world)


class TestRoomVisibleObjects:
    """Test that room :visible lists correctly surface objects in LLM context."""

    def test_visible_global_objects_appear_in_context(self, runtime):
        """Objects in room's :visible list should appear even if at @global."""
        runtime.move_object("@player", "@cs-2nd")
        state = get_game_state(runtime)

        visible_ids = {obj.id for obj in state.visible_objects}
        assert "@up-button" in visible_ids
        assert "@down-button" in visible_ids

    def test_visible_nodesc_objects_appear_in_context(self, runtime):
        """Objects with :nodesc should appear if in room's :visible list."""
        # The buttons have both :nodesc and :location @global
        runtime.move_object("@player", "@comp-center")
        state = get_game_state(runtime)

        visible_ids = {obj.id for obj in state.visible_objects}
        # Both buttons should be visible on first floor
        assert "@up-button" in visible_ids
        assert "@down-button" in visible_ids

    def test_visible_varies_by_room(self, runtime):
        """Different rooms should show different :visible objects."""
        # Basement only has up button
        runtime.move_object("@player", "@cs-basement")
        state = get_game_state(runtime)
        visible_ids = {obj.id for obj in state.visible_objects}
        assert "@up-button" in visible_ids
        assert "@down-button" not in visible_ids

        # Top floor only has down button
        runtime.move_object("@player", "@cs-3rd")
        state = get_game_state(runtime)
        visible_ids = {obj.id for obj in state.visible_objects}
        assert "@down-button" in visible_ids
        assert "@up-button" not in visible_ids

    def test_regular_room_objects_still_appear(self, runtime):
        """Objects located in the room should still appear normally."""
        runtime.move_object("@player", "@cs-2nd")
        state = get_game_state(runtime)

        visible_ids = {obj.id for obj in state.visible_objects}
        # The elevator door is located in @cs-2nd, should still appear
        assert "@elevator-door-2" in visible_ids
