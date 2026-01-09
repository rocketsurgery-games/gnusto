"""Tests for DSL expression evaluator."""

import pytest
from grue.expr import (
    ExprEvaluator,
    EffectExecutor,
    EvalError,
    eval_predicate,
    execute_effect,
)
from grue.sexpr import parse


class MockWorldState:
    """Mock world state for testing."""

    def __init__(self):
        # Object locations
        self.locations = {
            "FLASHLIGHT": "PLAYER",
            "KEY": "PLAYER",
            "DOOR": "TERMINAL-ROOM",
            "HACKER": "TERMINAL-ROOM",
            "CHAIR": "TERMINAL-ROOM",
            "PLAYER": "TERMINAL-ROOM",
        }

        # Object flags
        self.flags = {
            "FLASHLIGHT": {"TAKEBIT", "LIGHTBIT", "ONBIT"},
            "KEY": {"TAKEBIT"},
            "DOOR": {"DOORBIT", "LOCKED"},
            "HACKER": {"PERSONBIT"},
            "CHAIR": {"TAKEBIT"},
        }

        # Object properties
        self.properties = {
            "FLASHLIGHT": {"battery_level": 100, "DESC": "A sturdy flashlight"},
            "DOOR": {"locked": True},
            "HACKER": {"blocking": True, "personality": "antisocial"},
        }

        # Global variables
        self.globals = {
            "SCORE": 0,
            "MOVES": 0,
            "GAME_PHASE": "beginning",
        }

        # Rooms set
        self.rooms = {"TERMINAL-ROOM", "HALLWAY", "MAINTENANCE-CLOSET"}

    def get_object_flag(self, obj: str, flag: str) -> bool:
        return flag in self.flags.get(obj, set())

    def get_object_location(self, obj: str) -> str | None:
        return self.locations.get(obj)

    def get_object_property(self, obj: str, prop: str):
        return self.properties.get(obj, {}).get(prop)

    def get_object_flags(self, obj: str) -> set[str]:
        return self.flags.get(obj, set())

    def get_global(self, name: str):
        if name not in self.globals:
            raise KeyError(f"Unknown global: {name}")
        return self.globals[name]

    def get_player_location(self) -> str:
        return self.locations["PLAYER"]

    def get_inventory(self) -> list[str]:
        return [obj for obj, loc in self.locations.items() if loc == "PLAYER" and obj != "PLAYER"]

    def is_visible(self, obj: str) -> bool:
        # Object is visible if in player's location or in inventory
        obj_loc = self.locations.get(obj)
        if obj_loc is None:
            return False
        if obj_loc == "PLAYER":
            return True
        return obj_loc == self.get_player_location()

    def is_room(self, loc: str) -> bool:
        return loc in self.rooms

    def get_contents(self, container: str) -> list[str]:
        return [obj for obj, loc in self.locations.items() if loc == container]

    # Mutable operations
    def set_object_flag(self, obj: str, flag: str) -> None:
        if obj not in self.flags:
            self.flags[obj] = set()
        self.flags[obj].add(flag)

    def clear_object_flag(self, obj: str, flag: str) -> None:
        if obj in self.flags:
            self.flags[obj].discard(flag)

    def set_object_property(self, obj: str, prop: str, value) -> None:
        if obj not in self.properties:
            self.properties[obj] = {}
        self.properties[obj][prop] = value

    def set_global(self, name: str, value) -> None:
        self.globals[name] = value

    def move_object(self, obj: str, dest: str) -> None:
        self.locations[obj] = dest


class TestBasicPredicates:
    """Test basic predicate evaluation."""

    def test_has_flag_true(self):
        state = MockWorldState()
        assert eval_predicate("(has-flag FLASHLIGHT TAKEBIT)", state) is True

    def test_has_flag_false(self):
        state = MockWorldState()
        assert eval_predicate("(has-flag DOOR TAKEBIT)", state) is False

    def test_equality(self):
        state = MockWorldState()
        assert eval_predicate("(= 1 1)", state) is True
        assert eval_predicate("(= 1 2)", state) is False

    def test_comparisons(self):
        state = MockWorldState()
        assert eval_predicate("(> 5 3)", state) is True
        assert eval_predicate("(< 5 3)", state) is False
        assert eval_predicate("(>= 5 5)", state) is True
        assert eval_predicate("(<= 5 5)", state) is True


class TestBooleanOperators:
    """Test boolean logic."""

    def test_and_true(self):
        state = MockWorldState()
        expr = "(and (has-flag FLASHLIGHT TAKEBIT) (has-flag FLASHLIGHT LIGHTBIT))"
        assert eval_predicate(expr, state) is True

    def test_and_false(self):
        state = MockWorldState()
        expr = "(and (has-flag FLASHLIGHT TAKEBIT) (has-flag DOOR TAKEBIT))"
        assert eval_predicate(expr, state) is False

    def test_or_true(self):
        state = MockWorldState()
        expr = "(or (has-flag DOOR TAKEBIT) (has-flag FLASHLIGHT TAKEBIT))"
        assert eval_predicate(expr, state) is True

    def test_or_false(self):
        state = MockWorldState()
        expr = "(or (has-flag DOOR TAKEBIT) (has-flag HACKER TAKEBIT))"
        assert eval_predicate(expr, state) is False

    def test_not(self):
        state = MockWorldState()
        assert eval_predicate("(not (has-flag DOOR TAKEBIT))", state) is True
        assert eval_predicate("(not (has-flag FLASHLIGHT TAKEBIT))", state) is False

    def test_complex_boolean(self):
        state = MockWorldState()
        # TAKE precondition: has TAKEBIT, is visible, not already held
        expr = """
        (and
          (has-flag CHAIR TAKEBIT)
          (visible? CHAIR)
          (not (held? CHAIR)))
        """
        assert eval_predicate(expr, state) is True


class TestObjectQueries:
    """Test object query predicates."""

    def test_loc(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(loc FLASHLIGHT)")) == "PLAYER"
        assert evaluator.eval(parse("(loc DOOR)")) == "TERMINAL-ROOM"

    def test_prop(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(prop FLASHLIGHT battery_level)")) == 100
        assert evaluator.eval(parse("(prop DOOR locked)")) is True

    def test_flags(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        flags = evaluator.eval(parse("(flags FLASHLIGHT)"))
        assert "TAKEBIT" in flags
        assert "LIGHTBIT" in flags

    def test_loc_equality(self):
        state = MockWorldState()
        assert eval_predicate("(= (loc FLASHLIGHT) PLAYER)", state) is True


class TestConveniencePredicates:
    """Test convenience predicates."""

    def test_visible_in_room(self):
        state = MockWorldState()
        assert eval_predicate("(visible? CHAIR)", state) is True

    def test_visible_in_inventory(self):
        state = MockWorldState()
        assert eval_predicate("(visible? FLASHLIGHT)", state) is True

    def test_not_visible(self):
        state = MockWorldState()
        state.locations["HIDDEN_ITEM"] = "MAINTENANCE-CLOSET"
        assert eval_predicate("(visible? HIDDEN_ITEM)", state) is False

    def test_held(self):
        state = MockWorldState()
        assert eval_predicate("(held? FLASHLIGHT)", state) is True
        assert eval_predicate("(held? CHAIR)", state) is False

    def test_here(self):
        state = MockWorldState()
        assert eval_predicate("(here? CHAIR)", state) is True
        state.locations["FAR_ITEM"] = "HALLWAY"
        assert eval_predicate("(here? FAR_ITEM)", state) is False

    def test_in(self):
        state = MockWorldState()
        assert eval_predicate("(in? CHAIR TERMINAL-ROOM)", state) is True
        assert eval_predicate("(in? CHAIR HALLWAY)", state) is False

    def test_room(self):
        state = MockWorldState()
        assert eval_predicate("(room? TERMINAL-ROOM)", state) is True
        assert eval_predicate("(room? FLASHLIGHT)", state) is False


class TestQuantifiers:
    """Test collection operations."""

    def test_inventory(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        inv = evaluator.eval(parse("(inventory PLAYER)"))
        assert "FLASHLIGHT" in inv
        assert "KEY" in inv

    def test_contents(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        contents = evaluator.eval(parse("(contents TERMINAL-ROOM)"))
        assert "DOOR" in contents
        assert "HACKER" in contents

    def test_any_true(self):
        state = MockWorldState()
        # Any item in inventory has LIGHTBIT
        expr = "(any (inventory PLAYER) (lambda (obj) (has-flag obj LIGHTBIT)))"
        assert eval_predicate(expr, state) is True

    def test_any_false(self):
        state = MockWorldState()
        # Any item in inventory has PERSONBIT
        expr = "(any (inventory PLAYER) (lambda (obj) (has-flag obj PERSONBIT)))"
        assert eval_predicate(expr, state) is False

    def test_all_true(self):
        state = MockWorldState()
        # All items in inventory have TAKEBIT
        expr = "(all (inventory PLAYER) (lambda (obj) (has-flag obj TAKEBIT)))"
        assert eval_predicate(expr, state) is True

    def test_all_false(self):
        state = MockWorldState()
        # All items in inventory have LIGHTBIT (KEY doesn't)
        expr = "(all (inventory PLAYER) (lambda (obj) (has-flag obj LIGHTBIT)))"
        assert eval_predicate(expr, state) is False


class TestEffects:
    """Test effect execution."""

    def test_move(self):
        state = MockWorldState()
        execute_effect("(move! CHAIR PLAYER)", state)
        assert state.locations["CHAIR"] == "PLAYER"

    def test_set_flag(self):
        state = MockWorldState()
        assert "OPENBIT" not in state.flags.get("DOOR", set())
        execute_effect("(set-flag! DOOR OPENBIT)", state)
        assert "OPENBIT" in state.flags["DOOR"]

    def test_clear_flag(self):
        state = MockWorldState()
        assert "LOCKED" in state.flags["DOOR"]
        execute_effect("(clear-flag! DOOR LOCKED)", state)
        assert "LOCKED" not in state.flags["DOOR"]

    def test_set_prop(self):
        state = MockWorldState()
        execute_effect("(set-prop! DOOR locked false)", state)
        assert state.properties["DOOR"]["locked"] is False

    def test_set_global(self):
        state = MockWorldState()
        execute_effect("(set! SCORE 10)", state)
        assert state.globals["SCORE"] == 10

    def test_inc(self):
        state = MockWorldState()
        execute_effect("(inc! SCORE)", state)
        assert state.globals["SCORE"] == 1
        execute_effect("(inc! SCORE 5)", state)
        assert state.globals["SCORE"] == 6

    def test_seq(self):
        state = MockWorldState()
        expr = """
        (seq
          (move! CHAIR PLAYER)
          (inc! SCORE 5)
          (set-flag! CHAIR TOUCHBIT))
        """
        execute_effect(expr, state)
        assert state.locations["CHAIR"] == "PLAYER"
        assert state.globals["SCORE"] == 5
        assert "TOUCHBIT" in state.flags["CHAIR"]

    def test_when_true(self):
        state = MockWorldState()
        execute_effect("(when (= SCORE 0) (inc! SCORE 10))", state)
        assert state.globals["SCORE"] == 10

    def test_when_false(self):
        state = MockWorldState()
        state.globals["SCORE"] = 50
        execute_effect("(when (= SCORE 0) (inc! SCORE 10))", state)
        assert state.globals["SCORE"] == 50  # unchanged


class TestRealWorldScenarios:
    """Test scenarios from Lurking Horror."""

    def test_take_precondition(self):
        """TAKE action precondition from design doc."""
        state = MockWorldState()

        # Chair is takeable, visible, and not held
        take_pre = """
        (and
          (has-flag CHAIR TAKEBIT)
          (visible? CHAIR)
          (not (held? CHAIR)))
        """
        assert eval_predicate(take_pre, state) is True

        # Flashlight is already held
        take_flashlight = """
        (and
          (has-flag FLASHLIGHT TAKEBIT)
          (visible? FLASHLIGHT)
          (not (held? FLASHLIGHT)))
        """
        assert eval_predicate(take_flashlight, state) is False

    def test_take_effect(self):
        """TAKE action effect."""
        state = MockWorldState()

        # Execute take
        execute_effect("(move! CHAIR PLAYER)", state)

        # Verify post-conditions
        assert eval_predicate("(held? CHAIR)", state) is True
        assert eval_predicate("(= (loc CHAIR) PLAYER)", state) is True

    def test_open_door_with_key(self):
        """UNLOCK then OPEN door scenario."""
        state = MockWorldState()
        state.flags["DOOR"].add("LOCKBIT")

        # Precondition: door is locked, we have key
        unlock_pre = """
        (and
          (has-flag DOOR LOCKBIT)
          (has-flag DOOR LOCKED)
          (held? KEY))
        """
        assert eval_predicate(unlock_pre, state) is True

        # Effect: clear locked flag
        execute_effect("(clear-flag! DOOR LOCKED)", state)

        # Now we can open
        open_pre = """
        (and
          (has-flag DOOR DOORBIT)
          (not (has-flag DOOR LOCKED)))
        """
        assert eval_predicate(open_pre, state) is True

        # Open the door
        execute_effect("(set-flag! DOOR OPENBIT)", state)
        assert eval_predicate("(has-flag DOOR OPENBIT)", state) is True

    def test_light_check_with_flashlight(self):
        """Check if player has light source (from invariants)."""
        state = MockWorldState()
        state.properties["TERMINAL-ROOM"] = {"lit": False}

        # Room is dark, check for light source in inventory
        light_check = """
        (or
          (prop (loc PLAYER) lit)
          (any (inventory PLAYER)
               (lambda (obj)
                 (and (has-flag obj LIGHTBIT)
                      (has-flag obj ONBIT)))))
        """
        # Room is dark but flashlight is on
        assert eval_predicate(light_check, state) is True

        # Turn off flashlight
        state.flags["FLASHLIGHT"].remove("ONBIT")
        assert eval_predicate(light_check, state) is False


class TestErrorHandling:
    """Test error conditions."""

    def test_unknown_function(self):
        state = MockWorldState()
        with pytest.raises(EvalError) as excinfo:
            eval_predicate("(unknown-func x y)", state)
        assert "Unknown function" in str(excinfo.value)

    def test_wrong_arity(self):
        state = MockWorldState()
        with pytest.raises(EvalError) as excinfo:
            eval_predicate("(not)", state)
        assert "expects 1 argument" in str(excinfo.value)

    def test_invalid_effect_target(self):
        state = MockWorldState()
        with pytest.raises(EvalError):
            execute_effect("(set! 123 456)", state)
