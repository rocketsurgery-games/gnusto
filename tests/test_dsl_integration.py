"""
Integration tests for DSL with actual Lurking Horror data.

These tests verify that our DSL expressions work correctly
against real game state loaded from the ZIL parser.
"""

import pytest
from zil import load_game
from zil.dsl import parse, ExprEvaluator, EffectExecutor, eval_predicate


class GameWorldStateAdapter:
    """
    Adapter that wraps the existing World model to provide
    the WorldState interface expected by the DSL evaluator.
    """

    def __init__(self, world):
        self.world = world

    def get_object_flag(self, obj: str, flag: str) -> bool:
        obj_state = self.world.get_object_state(obj)
        if obj_state is None:
            return False
        return flag in obj_state.flags

    def get_object_location(self, obj: str) -> str | None:
        # PLAYER special case - player is always "in" the current room
        if obj == "PLAYER":
            return self.world.state.current_room
        obj_state = self.world.get_object_state(obj)
        if obj_state is None:
            return None
        return obj_state.location

    def get_object_property(self, obj: str, prop: str):
        obj_state = self.world.get_object_state(obj)
        if obj_state is None:
            return None
        return obj_state.properties.get(prop)

    def get_object_flags(self, obj: str) -> set[str]:
        obj_state = self.world.get_object_state(obj)
        if obj_state is None:
            return set()
        return obj_state.flags

    def get_global(self, name: str):
        # Check built-in state attributes first
        name_lower = name.lower()
        if name_lower == "score":
            return self.world.state.score
        if name_lower == "moves":
            return self.world.state.moves
        # Then check globals dict
        if name in self.world.state.globals:
            return self.world.state.globals[name]
        raise KeyError(f"Unknown global: {name}")

    def get_player_location(self) -> str:
        return self.world.state.current_room

    def get_inventory(self) -> list[str]:
        return list(self.world.state.inventory)

    def is_visible(self, obj: str) -> bool:
        # Object is visible if in current room, in inventory, or globally accessible
        obj_state = self.world.get_object_state(obj)
        if obj_state is None:
            return False
        loc = obj_state.location
        if loc is None:
            return False
        if loc == "PLAYER":
            return True
        if loc == self.world.state.current_room:
            return True
        # Check if in a visible container
        return False

    def is_room(self, loc: str) -> bool:
        return loc in self.world.data.rooms

    def get_contents(self, container: str) -> list[str]:
        # Get all objects whose location is this container
        result = []
        for obj_name, obj_state in self.world.state.objects.items():
            if obj_state.location == container:
                result.append(obj_name)
        return result

    # Mutable operations
    def set_object_flag(self, obj: str, flag: str) -> None:
        obj_state = self.world.get_object_state(obj)
        if obj_state:
            obj_state.flags.add(flag)

    def clear_object_flag(self, obj: str, flag: str) -> None:
        obj_state = self.world.get_object_state(obj)
        if obj_state:
            obj_state.flags.discard(flag)

    def set_object_property(self, obj: str, prop: str, value) -> None:
        obj_state = self.world.get_object_state(obj)
        if obj_state:
            obj_state.properties[prop] = value

    def set_global(self, name: str, value) -> None:
        name_lower = name.lower()
        if name_lower == "score":
            self.world.state.score = value
        elif name_lower == "moves":
            self.world.state.moves = value
        else:
            self.world.state.globals[name] = value

    def move_object(self, obj: str, dest: str) -> None:
        obj_state = self.world.get_object_state(obj)
        if obj_state:
            obj_state.location = dest


@pytest.fixture
def lurking_horror():
    """Load Lurking Horror game data."""
    data, world = load_game("infocom/lurkinghorror")
    return data, world


@pytest.fixture
def game_state(lurking_horror):
    """Create an adapter for the world state."""
    data, world = lurking_horror
    return GameWorldStateAdapter(world)


class TestLurkingHorrorBasics:
    """Basic tests with actual game data."""

    def test_starting_room(self, game_state):
        """Player starts in TERMINAL-ROOM."""
        assert game_state.get_player_location() == "TERMINAL-ROOM"

    def test_room_check(self, game_state):
        """TERMINAL-ROOM is a valid room."""
        assert game_state.is_room("TERMINAL-ROOM")

    def test_hacker_in_room(self, game_state):
        """Hacker should be in Terminal Room."""
        loc = game_state.get_object_location("HACKER")
        assert loc == "TERMINAL-ROOM"

    def test_hacker_is_person(self, game_state):
        """Hacker has PERSON flag."""
        assert game_state.get_object_flag("HACKER", "PERSON")


class TestDSLWithRealGame:
    """Test DSL expressions against real game state."""

    def test_basic_predicate(self, game_state):
        """Test basic has-flag predicate."""
        # The PC (computer) is in the terminal room and should have some flags
        result = eval_predicate("(visible? HACKER)", game_state)
        assert result is True

    def test_location_predicate(self, game_state):
        """Test location equality."""
        result = eval_predicate("(= (loc HACKER) TERMINAL-ROOM)", game_state)
        assert result is True

    def test_here_predicate(self, game_state):
        """Test that hacker is here (in player's room)."""
        result = eval_predicate("(here? HACKER)", game_state)
        assert result is True

    def test_inventory_empty_at_start(self, game_state):
        """Player starts with empty inventory."""
        inv = game_state.get_inventory()
        assert len(inv) == 0

    def test_room_contents(self, game_state):
        """Test getting room contents."""
        contents = game_state.get_contents("TERMINAL-ROOM")
        assert "HACKER" in contents

    def test_complex_predicate(self, game_state):
        """Test a complex nested predicate."""
        # Check if player is in a room and hacker is visible
        result = eval_predicate(
            "(and (room? (loc PLAYER)) (visible? HACKER))",
            game_state
        )
        assert result is True


class TestActionsWithRealGame:
    """Test action-like sequences with real game."""

    def test_examine_precondition(self, game_state):
        """EXAMINE requires object to be visible."""
        # Hacker is in the room, so should be visible
        expr = "(visible? HACKER)"
        assert eval_predicate(expr, game_state) is True

    def test_potential_take(self, game_state):
        """Check if we could potentially take something."""
        # Check if there's anything in the room with TAKEBIT
        # Note: We need to find an object that has TAKEBIT
        evaluator = ExprEvaluator(game_state)
        contents = evaluator.eval(parse("(contents TERMINAL-ROOM)"))

        # Check each object for TAKEBIT
        takeable = []
        for obj in contents:
            if game_state.get_object_flag(obj, "TAKEBIT"):
                takeable.append(obj)

        # In the Terminal Room at start, what's takeable?
        # This depends on the actual game data
        print(f"Takeable objects: {takeable}")


class TestEffectsWithRealGame:
    """Test effects on real game state."""

    def test_score_increment(self, lurking_horror):
        """Test incrementing the score."""
        data, world = lurking_horror
        game_state = GameWorldStateAdapter(world)

        initial_score = world.state.score
        executor = EffectExecutor(game_state)
        executor.execute(parse("(set! score 10)"))
        assert world.state.score == 10

    def test_move_object(self, lurking_horror):
        """Test moving an object."""
        data, world = lurking_horror
        game_state = GameWorldStateAdapter(world)

        # Find a takeable object in the room
        contents = game_state.get_contents("TERMINAL-ROOM")
        takeable = None
        for obj in contents:
            if game_state.get_object_flag(obj, "TAKEBIT"):
                takeable = obj
                break

        if takeable:
            # Move it to player's inventory
            executor = EffectExecutor(game_state)
            executor.execute(parse(f"(move! {takeable} PLAYER)"))

            # Verify it's now in inventory
            assert game_state.get_object_location(takeable) == "PLAYER"
            assert eval_predicate(f"(held? {takeable})", game_state)
