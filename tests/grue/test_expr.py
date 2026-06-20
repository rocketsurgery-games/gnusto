"""Tests for expression evaluator."""

import pytest

from grue.expr import (
    EffectExecutor,
    Environment,
    EvalError,
    ExprEvaluator,
    eval_predicate,
    execute_effect,
)
from grue.sexpr import Keyword, parse


class MockWorldState:
    """Mock world state for testing."""

    def __init__(self):
        # Bindings (for testing expression evaluation)
        self.bindings: dict[str, any] = {}

        # Object locations
        self.locations = {
            "FLASHLIGHT": "PLAYER",
            "KEY": "PLAYER",
            "DOOR": "TERMINAL-ROOM",
            "HACKER": "TERMINAL-ROOM",
            "CHAIR": "TERMINAL-ROOM",
            "PLAYER": "TERMINAL-ROOM",
        }

        # Object flags (legacy - kept for backward compatibility in some tests)
        self.flags = {
            "FLASHLIGHT": {"TAKEBIT", "LIGHTBIT", "ONBIT"},
            "KEY": {"TAKEBIT"},
            "DOOR": {"DOORBIT", "LOCKED"},
            "HACKER": {"PERSONBIT"},
            "CHAIR": {"TAKEBIT"},
        }

        # Object properties (unified with flags using lowercase names)
        # score/moves are player properties, not globals
        self.properties = {
            "FLASHLIGHT": {
                "battery_level": 100,
                "DESC": "A sturdy flashlight",
                "takeable": True,
                "light": True,
                "on": True,
            },
            "KEY": {"takeable": True},
            "DOOR": {"locked": True, "door": True},
            "HACKER": {"blocking": True, "personality": "antisocial", "person": True},
            "CHAIR": {"takeable": True},
            "PLAYER": {"score": 0, "moves": 0},
        }

        # Rooms set
        self.rooms = {"TERMINAL-ROOM", "HALLWAY", "MAINTENANCE-CLOSET"}

    def get_object_location(self, obj: str) -> str | None:
        return self.locations.get(obj)

    def get_object_property(self, obj: str, prop: str):
        return self.properties.get(obj, {}).get(prop)

    def has_object_property(self, obj: str, prop: str) -> bool:
        return prop in self.properties.get(obj, {})

    def get_global(self, name: str):
        # Check bindings first (for test variables like ?x)
        if name in self.bindings:
            return self.bindings[name]
        raise KeyError(f"Unknown symbol: {name}")

    def get_player_location(self) -> str:
        return self.locations["PLAYER"]

    def get_player_name(self) -> str:
        return "PLAYER"

    def get_inventory(self) -> list[str]:
        return [
            obj
            for obj, loc in self.locations.items()
            if loc == "PLAYER" and obj != "PLAYER"
        ]

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
    def set_object_property(self, obj: str, prop: str, value) -> None:
        if obj not in self.properties:
            self.properties[obj] = {}
        self.properties[obj][prop] = value

    def move_object(self, obj: str, dest: str) -> None:
        self.locations[obj] = dest


class TestBasicPredicates:
    """Test basic predicate evaluation."""

    def test_has_flag_true(self):
        state = MockWorldState()
        assert eval_predicate("(:takeable FLASHLIGHT)", state) is True

    def test_has_flag_false(self):
        state = MockWorldState()
        assert eval_predicate("(:takeable DOOR)", state) is False

    def test_equality(self):
        state = MockWorldState()
        assert eval_predicate("(= 1 1)", state) is True
        assert eval_predicate("(= 1 2)", state) is False

    def test_keyword_equality_is_lisp_like(self):
        # Keywords are self-denoting and equal by name...
        state = MockWorldState()
        assert eval_predicate("(= :open :open)", state) is True
        assert eval_predicate("(= :open :closed)", state) is False
        # ...but a keyword is NOT equal to a same-named string.
        assert eval_predicate('(= :open "open")', state) is False

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
        expr = "(and (:takeable FLASHLIGHT) (:light FLASHLIGHT))"
        assert eval_predicate(expr, state) is True

    def test_and_false(self):
        state = MockWorldState()
        expr = "(and (:takeable FLASHLIGHT) (:takeable DOOR))"
        assert eval_predicate(expr, state) is False

    def test_or_true(self):
        state = MockWorldState()
        expr = "(or (:takeable DOOR) (:takeable FLASHLIGHT))"
        assert eval_predicate(expr, state) is True

    def test_or_false(self):
        state = MockWorldState()
        expr = "(or (:takeable DOOR) (:takeable HACKER))"
        assert eval_predicate(expr, state) is False

    def test_not(self):
        state = MockWorldState()
        assert eval_predicate("(not (:takeable DOOR))", state) is True
        assert eval_predicate("(not (:takeable FLASHLIGHT))", state) is False

    def test_complex_boolean(self):
        state = MockWorldState()
        # TAKE precondition: has TAKEBIT, is visible, not already held
        expr = """
        (and
          (:takeable CHAIR)
          (visible? CHAIR)
          (not (held? CHAIR)))
        """
        assert eval_predicate(expr, state) is True


class TestObjectQueries:
    """Test object query predicates."""

    def test_player(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(player)")) == "PLAYER"
        # Can be used in expressions
        assert evaluator.eval(parse("(= (loc FLASHLIGHT) (player))")) is True

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
        inv = evaluator.eval(parse("(inventory)"))
        assert "FLASHLIGHT" in inv
        assert "KEY" in inv

    def test_contents(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        contents = evaluator.eval(parse("(contents TERMINAL-ROOM)"))
        assert "DOOR" in contents
        assert "HACKER" in contents

    def test_some_true(self):
        state = MockWorldState()
        # Some item in inventory has light property - returns truthy value
        expr = "(some (fn (?obj) (:light ?obj)) (inventory))"
        assert eval_predicate(expr, state) is True

    def test_some_false(self):
        state = MockWorldState()
        # No item in inventory has person property - returns nil
        expr = "(some (fn (?obj) (:person ?obj)) (inventory))"
        assert eval_predicate(expr, state) is False

    def test_every_true(self):
        state = MockWorldState()
        # All items in inventory have TAKEBIT
        expr = "(every? (fn (?obj) (:takeable ?obj)) (inventory))"
        assert eval_predicate(expr, state) is True

    def test_every_false(self):
        state = MockWorldState()
        # Not all items in inventory have light property (KEY doesn't)
        expr = "(every? (fn (?obj) (:light ?obj)) (inventory))"
        assert eval_predicate(expr, state) is False


class TestEffects:
    """Test effect execution."""

    def test_move(self):
        state = MockWorldState()
        execute_effect("(move CHAIR PLAYER)", state)
        assert state.locations["CHAIR"] == "PLAYER"

    def test_set_flag(self):
        state = MockWorldState()
        assert not state.properties.get("DOOR", {}).get("open")
        execute_effect("(set DOOR :open true)", state)
        assert state.properties["DOOR"]["open"] is True

    def test_clear_flag(self):
        state = MockWorldState()
        assert state.properties["DOOR"]["locked"] is True
        execute_effect("(set DOOR :locked false)", state)
        assert state.properties["DOOR"]["locked"] is False

    def test_inc(self):
        state = MockWorldState()
        execute_effect("(inc PLAYER :score)", state)
        assert state.properties["PLAYER"]["score"] == 1
        execute_effect("(inc PLAYER :score 5)", state)
        assert state.properties["PLAYER"]["score"] == 6

    def test_seq(self):
        state = MockWorldState()
        expr = """
        (seq
          (move CHAIR PLAYER)
          (inc PLAYER :score 5)
          (set CHAIR :touchbit true))
        """
        execute_effect(expr, state)
        assert state.locations["CHAIR"] == "PLAYER"
        assert state.properties["PLAYER"]["score"] == 5
        assert state.properties["CHAIR"]["touchbit"] is True

    def test_when_true(self):
        state = MockWorldState()
        state.properties["PLAYER"]["score"] = 0
        execute_effect("(when (= (:score PLAYER) 0) (inc PLAYER :score 10))", state)
        assert state.properties["PLAYER"]["score"] == 10

    def test_when_false(self):
        state = MockWorldState()
        state.properties["PLAYER"]["score"] = 50
        execute_effect("(when (= (:score PLAYER) 0) (inc PLAYER :score 10))", state)
        assert state.properties["PLAYER"]["score"] == 50  # unchanged


class TestRealWorldScenarios:
    """Test scenarios from Lurking Horror."""

    def test_take_precondition(self):
        """TAKE action precondition from design doc."""
        state = MockWorldState()

        # Chair is takeable, visible, and not held
        take_pre = """
        (and
          (:takeable CHAIR)
          (visible? CHAIR)
          (not (held? CHAIR)))
        """
        assert eval_predicate(take_pre, state) is True

        # Flashlight is already held
        take_flashlight = """
        (and
          (:takeable FLASHLIGHT)
          (visible? FLASHLIGHT)
          (not (held? FLASHLIGHT)))
        """
        assert eval_predicate(take_flashlight, state) is False

    def test_take_effect(self):
        """TAKE action effect."""
        state = MockWorldState()

        # Execute take
        execute_effect("(move CHAIR PLAYER)", state)

        # Verify post-conditions
        assert eval_predicate("(held? CHAIR)", state) is True
        assert eval_predicate("(= (loc CHAIR) PLAYER)", state) is True

    def test_open_door_with_key(self):
        """UNLOCK then OPEN door scenario."""
        state = MockWorldState()
        # Door starts locked with door property
        state.properties["DOOR"]["locked"] = True
        state.properties["DOOR"]["door"] = True

        # Precondition: door is locked, we have key
        unlock_pre = """
        (and
          (:door DOOR)
          (:locked DOOR)
          (held? KEY))
        """
        assert eval_predicate(unlock_pre, state) is True

        # Effect: clear locked flag
        execute_effect("(set DOOR :locked false)", state)

        # Now we can open
        open_pre = """
        (and
          (:door DOOR)
          (not (:locked DOOR)))
        """
        assert eval_predicate(open_pre, state) is True

        # Open the door
        execute_effect("(set DOOR :open true)", state)
        assert eval_predicate("(:open DOOR)", state) is True

    def test_light_check_with_flashlight(self):
        """Check if player has light source (from invariants)."""
        state = MockWorldState()
        state.properties["TERMINAL-ROOM"] = {"lit": False}

        # Room is dark, check for light source in inventory
        light_check = """
        (or
          (prop (loc PLAYER) lit)
          (some (fn (?obj)
                  (and (:light ?obj)
                       (:on ?obj)))
                (inventory)))
        """
        # Room is dark but flashlight is on
        assert eval_predicate(light_check, state) is True

        # Turn off flashlight
        state.properties["FLASHLIGHT"]["on"] = False
        assert eval_predicate(light_check, state) is False


class TestUserDefinedFunctions:
    """Test user-defined functions via defn."""

    def test_define_and_call_no_args(self):
        """Define a zero-argument function and call it."""
        state = MockWorldState()
        executor = EffectExecutor(state)

        # Define function
        executor.execute(parse("(defn at-terminal? () (= (loc PLAYER) TERMINAL-ROOM))"))

        # Call it via the evaluator (shares function registry)
        result = executor._predicates.eval(parse("(at-terminal?)"))
        assert result is True

    def test_define_and_call_with_args(self):
        """Define a function with arguments."""
        state = MockWorldState()
        executor = EffectExecutor(state)

        # Define function that checks if an object has a specific property
        executor.execute(parse("(defn is-takeable? (obj) (:takeable obj))"))

        # Call with different objects
        assert executor._predicates.eval(parse("(is-takeable? FLASHLIGHT)")) is True
        # HACKER has no takeable property - returns None which is falsy
        assert not executor._predicates.eval(parse("(is-takeable? HACKER)"))

    def test_define_with_multiple_args(self):
        """Define function with multiple arguments."""
        state = MockWorldState()
        executor = EffectExecutor(state)

        # Define function that checks if object is at location
        # Note: use 'place' not 'loc' to avoid shadowing builtin (loc obj)
        executor.execute(parse("(defn obj-at? (obj place) (= (loc obj) place))"))

        # Call with arguments
        assert executor._predicates.eval(parse("(obj-at? FLASHLIGHT PLAYER)")) is True
        assert executor._predicates.eval(parse("(obj-at? DOOR TERMINAL-ROOM)")) is True
        assert executor._predicates.eval(parse("(obj-at? FLASHLIGHT HALLWAY)")) is False

    def test_function_body_with_complex_expression(self):
        """Function body can be complex expressions."""
        state = MockWorldState()
        executor = EffectExecutor(state)

        # Define function with and/or/not
        executor.execute(
            parse("""
            (defn can-take? (obj)
              (and (:takeable obj)
                   (visible? obj)
                   (not (held? obj))))
        """)
        )

        # CHAIR can be taken (takeable, visible in room, not held)
        assert executor._predicates.eval(parse("(can-take? CHAIR)")) is True
        # FLASHLIGHT already held
        assert executor._predicates.eval(parse("(can-take? FLASHLIGHT)")) is False

    def test_functions_can_call_other_functions(self):
        """User-defined functions can call other user-defined functions."""
        state = MockWorldState()
        executor = EffectExecutor(state)

        # Define helper
        executor.execute(parse("(defn is-person? (obj) (:person obj))"))
        # Define function that uses helper
        executor.execute(
            parse("(defn is-person-here? (obj) (and (is-person? obj) (here? obj)))")
        )

        assert executor._predicates.eval(parse("(is-person-here? HACKER)")) is True
        # CHAIR returns None for :person (falsy), so (and nil ...) is False
        assert not executor._predicates.eval(parse("(is-person-here? CHAIR)"))

    def test_wrong_arity_error(self):
        """Calling function with wrong number of arguments raises error."""
        state = MockWorldState()
        executor = EffectExecutor(state)

        executor.execute(parse("(defn two-args (a b) (= a b))"))

        with pytest.raises(EvalError) as excinfo:
            executor._predicates.eval(parse("(two-args 1)"))
        assert "expects 2 arguments" in str(excinfo.value)

        with pytest.raises(EvalError) as excinfo:
            executor._predicates.eval(parse("(two-args 1 2 3)"))
        assert "expects 2 arguments" in str(excinfo.value)

    def test_defn_name_must_be_symbol(self):
        """defn name must be a symbol."""
        state = MockWorldState()
        executor = EffectExecutor(state)

        with pytest.raises(EvalError) as excinfo:
            executor.execute(parse("(defn 123 () true)"))
        assert "must be a symbol" in str(excinfo.value)

    def test_defn_params_must_be_list(self):
        """defn params must be a list."""
        state = MockWorldState()
        executor = EffectExecutor(state)

        with pytest.raises(EvalError) as excinfo:
            executor.execute(parse("(defn foo x true)"))
        assert "params must be a list" in str(excinfo.value)

    def test_defn_param_must_be_symbol(self):
        """defn parameters must be symbols."""
        state = MockWorldState()
        executor = EffectExecutor(state)

        with pytest.raises(EvalError) as excinfo:
            executor.execute(parse("(defn foo (123) true)"))
        assert "parameter must be a symbol" in str(excinfo.value)

    def test_define_function_directly(self):
        """Test define_function method on ExprEvaluator."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)

        # Define function directly
        evaluator.define_function("always-true", [], parse("true"))
        evaluator.define_function("is-lit", ["obj"], parse("(:light obj)"))

        assert evaluator.eval(parse("(always-true)")) is True
        assert evaluator.eval(parse("(is-lit FLASHLIGHT)")) is True
        # KEY has no light property - returns None which is falsy
        assert not evaluator.eval(parse("(is-lit KEY)"))

    def test_shared_function_registry(self):
        """Executor and evaluator share function registry."""
        state = MockWorldState()
        functions = {}
        executor = EffectExecutor(state, functions)
        evaluator = ExprEvaluator(state, functions)

        # Define via executor
        executor.execute(parse("(defn test-fn () true)"))

        # Callable via evaluator
        assert evaluator.eval(parse("(test-fn)")) is True


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

    def test_invalid_effect_name(self):
        state = MockWorldState()
        with pytest.raises(EvalError):
            execute_effect("(frobnicate @door)", state)


class TestHigherOrderFunctions:
    """Test map, filter, reduce, keep, remove."""

    def test_map_double(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(map (fn (?x) (* ?x 2)) '(1 2 3))"))
        assert result == [2, 4, 6]

    def test_map_first(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(map (fn (?x) (first ?x)) '((a b) (c d)))"))
        assert result == ["a", "c"]

    def test_map_empty(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(map (fn (?x) ?x) '())"))
        assert result == []

    def test_filter_positive(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(filter (fn (?x) (> ?x 0)) '(-1 0 1 2))"))
        assert result == [1, 2]

    def test_filter_empty(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(filter (fn (?x) (> ?x 100)) '(1 2 3))"))
        assert result == []

    def test_remove_positive(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(remove (fn (?x) (> ?x 0)) '(-1 0 1 2))"))
        assert result == [-1, 0]

    def test_keep_positive(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(
            parse("(keep (fn (?x) (if (> ?x 0) ?x nil)) '(-1 0 1 2))")
        )
        assert result == [1, 2]

    def test_reduce_sum(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(
            parse("(reduce (fn (?acc ?x) (+ ?acc ?x)) 0 '(1 2 3 4))")
        )
        assert result == 10

    def test_reduce_reverse(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(
            parse("(reduce (fn (?acc ?x) (cons ?x ?acc)) '() '(1 2 3))")
        )
        assert result == [3, 2, 1]

    def test_reduce_empty(self):
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(reduce (fn (?acc ?x) (+ ?acc ?x)) 100 '())"))
        assert result == 100

    def test_map_filter_compose(self):
        """Test composing map and filter."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        # Double values then filter for > 3
        result = evaluator.eval(
            parse("(filter (fn (?x) (> ?x 3)) (map (fn (?x) (* ?x 2)) '(1 2 3)))")
        )
        assert result == [4, 6]


class TestForDoseq:
    """Test for and doseq comprehension forms."""

    def test_for_basic(self):
        """Basic for comprehension."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(for (?x '(1 2 3)) (* ?x 2))"))
        assert result == [2, 4, 6]

    def test_for_empty(self):
        """for over empty sequence returns empty list."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(for (?x '()) ?x)"))
        assert result == []

    def test_for_nested_bindings(self):
        """for with multiple binding pairs creates cartesian product."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(for (?x '(1 2) ?y '(a b)) (list ?x ?y))"))
        assert result == [[1, "a"], [1, "b"], [2, "a"], [2, "b"]]

    def test_for_binding_uses_earlier_binding(self):
        """Later bindings can reference earlier bindings."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        # For each x, filter y to be less than x
        result = evaluator.eval(
            parse(
                "(for (?x '(2 3) ?y (filter (fn (?n) (< ?n ?x)) '(1 2))) (list ?x ?y))"
            )
        )
        # x=2: y in [1] (only 1 < 2) -> (2,1)
        # x=3: y in [1,2] (1,2 < 3) -> (3,1), (3,2)
        assert result == [[2, 1], [3, 1], [3, 2]]

    def test_for_with_strings(self):
        """for works with string elements."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse('(for (?s \'("a" "b")) (str ?s ?s))'))
        assert result == ["aa", "bb"]

    def test_doseq_returns_nil(self):
        """doseq returns nil."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(doseq (?x '(1 2 3)) ?x)"))
        assert result is None

    def test_doseq_pure_body(self):
        """doseq with pure body (no side effects) still works."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        # doseq returns nil, body is executed for side effects (or none)
        result = evaluator.eval(parse("(doseq (?x '(1 2 3)) (+ ?x 1))"))
        assert result is None

    def test_doseq_nested(self):
        """doseq with nested bindings (pure body)."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        # Nested bindings still work, just can't have side effects
        result = evaluator.eval(parse("(doseq (?x '(1 2) ?y '(a b)) (list ?x ?y))"))
        assert result is None

    def test_for_error_odd_bindings(self):
        """for with odd number of binding elements raises error."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        with pytest.raises(EvalError) as excinfo:
            evaluator.eval(parse("(for (?x '(1 2) ?y) ?x)"))
        assert "even number" in str(excinfo.value)

    def test_for_error_no_bindings(self):
        """for with empty bindings raises error."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        with pytest.raises(EvalError) as excinfo:
            evaluator.eval(parse("(for () 1)"))
        assert "at least one" in str(excinfo.value)

    def test_for_error_non_sequence(self):
        """for with non-sequence raises error."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        with pytest.raises(EvalError) as excinfo:
            evaluator.eval(parse("(for (?x 42) ?x)"))
        assert "sequence must be a list" in str(excinfo.value)


class TestRange:
    """Test range function."""

    def test_range_single_arg(self):
        """(range n) generates 0..n-1."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(range 5)")) == [0, 1, 2, 3, 4]
        assert evaluator.eval(parse("(range 0)")) == []
        assert evaluator.eval(parse("(range 1)")) == [0]

    def test_range_two_args(self):
        """(range start end) generates start..end-1."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(range 2 5)")) == [2, 3, 4]
        assert evaluator.eval(parse("(range 0 4)")) == [0, 1, 2, 3]
        assert evaluator.eval(parse("(range 5 5)")) == []

    def test_range_three_args(self):
        """(range start end step) generates sequence with step."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(range 0 10 2)")) == [0, 2, 4, 6, 8]
        assert evaluator.eval(parse("(range 5 0 -1)")) == [5, 4, 3, 2, 1]
        assert evaluator.eval(parse("(range 0 9 3)")) == [0, 3, 6]

    def test_range_with_for(self):
        """range integrates with for comprehension."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        # Double each value in 0..3
        result = evaluator.eval(parse("(for (?x (range 4)) (* ?x 2))"))
        assert result == [0, 2, 4, 6]

    def test_range_error_no_args(self):
        """range with no arguments raises error."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        with pytest.raises(EvalError) as excinfo:
            evaluator.eval(parse("(range)"))
        assert "expects 1-3 arguments" in str(excinfo.value)

    def test_range_error_non_int(self):
        """range with non-integer raises error."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)
        with pytest.raises(EvalError) as excinfo:
            evaluator.eval(parse('(range "5")'))
        assert "must be int" in str(excinfo.value)


# === EffectInterpreter Tests ===

from grue.expr import EffectInterpreter, EffectOutcome
from grue.sexpr import Keyword


class MockStateWithQueues(MockWorldState):
    """Extended mock state with queue support for EffectInterpreter tests."""

    def __init__(self):
        super().__init__()
        self.queues: dict[str, int | None] = {}

    def queue_event(self, event: str, countdown: int | None = None) -> None:
        self.queues[event] = countdown

    def dequeue_event(self, event: str) -> None:
        self.queues.pop(event, None)

    def is_queued(self, event: str) -> bool:
        return event in self.queues


class TestEffectInterpreterBasic:
    """Test basic EffectInterpreter functionality."""

    def test_success_simple(self):
        """Simple success terminator."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        result = interp.interpret([["success"]])
        assert result.outcome == "success"
        assert result.effects_applied == []

    def test_success_with_message(self):
        """Success with message context."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        result = interp.interpret([["success", Keyword("message"), "You got it!"]])
        assert result.outcome == "success"
        assert result.context["message"] == "You got it!"

    def test_success_carries_render_beat_tag(self):
        """(success :render :tag) lands the beat tag in context for the UI."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        result = interp.interpret(
            [["success", Keyword("render"), Keyword("stage5"), Keyword("message"), "m"]]
        )
        assert result.outcome == "success"
        # Beat tag preserved as a Keyword (resolves to <event>-stage5 downstream).
        assert result.context["render"] == Keyword("stage5")

    def test_blocked_with_reason(self):
        """Blocked with reason."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        result = interp.interpret([["blocked", Keyword("reason"), "locked"]])
        assert result.outcome == "blocked"
        assert result.reason == "locked"

    def test_blocked_with_message(self):
        """Blocked with reason and message."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        result = interp.interpret(
            [
                [
                    "blocked",
                    Keyword("reason"),
                    "no-key",
                    Keyword("message"),
                    "You need a key.",
                ]
            ]
        )
        assert result.outcome == "blocked"
        assert result.reason == "no-key"
        assert result.context["message"] == "You need a key."

    def test_default_terminator(self):
        """Default terminator."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        result = interp.interpret([["default"]])
        assert result.outcome == "default"

    def test_redirect_with_action(self):
        """Redirect with action."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        result = interp.interpret([["redirect", ["do", "@door", ":open"]]])
        assert result.outcome == "redirect"
        assert result.redirect_action == ["do", "@door", ":open"]


class TestEffectInterpreterMutations:
    """Test EffectInterpreter mutation effects."""

    def test_move_effect(self):
        """Move effect changes object location."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        result = interp.interpret([["move", "KEY", "HALLWAY"], ["success"]])
        assert result.outcome == "success"
        assert state.locations["KEY"] == "HALLWAY"
        assert "move KEY to HALLWAY" in result.effects_applied

    def test_set_property_effect(self):
        """Set effect changes object property."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        result = interp.interpret(
            [["set", "@player", Keyword("score"), 100], ["success"]]
        )
        assert result.outcome == "success"
        assert state.properties["@player"]["score"] == 100
        assert "set @player score = 100" in result.effects_applied

    def test_inc_effect(self):
        """Inc effect increments object property."""
        state = MockStateWithQueues()
        state.properties["@player"] = {"score": 10}
        interp = EffectInterpreter(state)
        result = interp.interpret([["inc", "@player", Keyword("score")], ["success"]])
        assert result.outcome == "success"
        assert state.properties["@player"]["score"] == 11

    def test_inc_effect_with_amount(self):
        """Inc effect with custom amount."""
        state = MockStateWithQueues()
        state.properties["@player"] = {"score": 10}
        interp = EffectInterpreter(state)
        result = interp.interpret(
            [["inc", "@player", Keyword("score"), 5], ["success"]]
        )
        assert result.outcome == "success"
        assert state.properties["@player"]["score"] == 15

    def test_dec_effect(self):
        """Dec effect decrements object property."""
        state = MockStateWithQueues()
        state.properties["@player"] = {"score": 10}
        interp = EffectInterpreter(state)
        result = interp.interpret([["dec", "@player", Keyword("score")], ["success"]])
        assert result.outcome == "success"
        assert state.properties["@player"]["score"] == 9

    def test_queue_effect(self):
        """Queue effect adds event to queue."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        result = interp.interpret([["queue", "@alarm"], ["success"]])
        assert result.outcome == "success"
        assert "@alarm" in state.queues
        assert state.queues["@alarm"] is None  # Indefinite

    def test_queue_effect_with_countdown(self):
        """Queue effect with countdown."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        result = interp.interpret([["queue", "@alarm", 5], ["success"]])
        assert result.outcome == "success"
        assert state.queues["@alarm"] == 5

    def test_dequeue_effect(self):
        """Dequeue effect removes event from queue."""
        state = MockStateWithQueues()
        state.queues["@alarm"] = 3
        interp = EffectInterpreter(state)
        result = interp.interpret([["dequeue", "@alarm"], ["success"]])
        assert result.outcome == "success"
        assert "@alarm" not in state.queues

    def test_set_prop_effect(self):
        """Set-prop effect changes object property."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        result = interp.interpret(
            [["set-prop", "FLASHLIGHT", "battery_level", 50], ["success"]]
        )
        assert result.outcome == "success"
        assert state.properties["FLASHLIGHT"]["battery_level"] == 50

    def test_multiple_effects(self):
        """Multiple effects applied in order."""
        state = MockStateWithQueues()
        state.properties["PLAYER"] = {"score": 0}
        interp = EffectInterpreter(state)
        result = interp.interpret(
            [
                ["move", "KEY", "PLAYER"],
                ["set", "KEY", Keyword("taken"), True],
                ["inc", "PLAYER", Keyword("score"), 10],
                ["success", Keyword("message"), "You take the key."],
            ]
        )
        assert result.outcome == "success"
        assert state.locations["KEY"] == "PLAYER"
        assert state.properties["KEY"]["taken"] is True
        assert state.properties["PLAYER"]["score"] == 10
        assert len(result.effects_applied) == 3


class TestEffectInterpreterValidation:
    """Test EffectInterpreter validation."""

    def test_no_terminator_error(self):
        """Effect list without terminator raises error."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        with pytest.raises(EvalError) as excinfo:
            interp.interpret([["move", "KEY", "HALLWAY"]])
        assert "terminator" in str(excinfo.value).lower()

    def test_multiple_terminators_error(self):
        """Effect list with multiple terminators raises error."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        with pytest.raises(EvalError) as excinfo:
            interp.interpret([["success"], ["blocked", Keyword("reason"), "test"]])
        assert "Multiple terminators" in str(excinfo.value)

    def test_empty_effect_error(self):
        """Empty effect raises error."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        with pytest.raises(EvalError) as excinfo:
            interp.interpret([[], ["success"]])
        assert "non-empty list" in str(excinfo.value)

    def test_invalid_effect_type_error(self):
        """Non-list effect raises error."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        with pytest.raises(EvalError) as excinfo:
            interp.interpret(["not-a-list", ["success"]])
        assert "non-empty list" in str(excinfo.value)

    def test_unknown_effect_error(self):
        """Unknown effect raises error."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        with pytest.raises(EvalError) as excinfo:
            interp.interpret([["unknown-effect", "arg"], ["success"]])
        assert "Unknown effect" in str(excinfo.value)


class TestEffectInterpreterSetup:
    """Test EffectInterpreter.interpret_setup for test :setup."""

    def test_setup_mutations_only(self):
        """Setup processes mutations without terminator."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        effects_applied = interp.interpret_setup(
            [["move", "KEY", "PLAYER"], ["set", "DOOR", Keyword("open"), True]]
        )
        assert state.locations["KEY"] == "PLAYER"
        assert state.properties["DOOR"]["open"] is True
        assert len(effects_applied) == 2

    def test_setup_rejects_terminators(self):
        """Setup rejects terminator effects."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        with pytest.raises(EvalError) as excinfo:
            interp.interpret_setup([["move", "KEY", "PLAYER"], ["success"]])
        assert "not allowed in :setup" in str(excinfo.value)

    def test_setup_empty_list(self):
        """Setup with empty list works."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        effects_applied = interp.interpret_setup([])
        assert effects_applied == []


class TestExposeEffect:
    """Test the (expose ...) effect."""

    def test_expose_sets_known(self):
        """(expose @entity) sets :known true on the entity."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        result = interp.interpret([["expose", "@students"], ["success"]])
        assert result.outcome == "success"
        assert state.properties["@students"]["known"] is True
        assert "expose @students" in result.effects_applied

    def test_expose_in_setup(self):
        """(expose) works in test :setup context."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        effects_applied = interp.interpret_setup(
            [
                ["expose", "@students"],
            ]
        )
        assert state.properties["@students"]["known"] is True
        assert len(effects_applied) == 1

    def test_expose_wrong_arg_count(self):
        """(expose) with wrong number of args raises error."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state)
        with pytest.raises(EvalError) as excinfo:
            interp.interpret([["expose", "@a", "@b"], ["success"]])
        assert "'expose' expects 1 argument" in str(excinfo.value)

    def test_expose_with_variable(self):
        """(expose ?topic) resolves variable binding."""
        state = MockStateWithQueues()
        interp = EffectInterpreter(state, bindings={"topic": "@lovecraft"})
        result = interp.interpret([["expose", "?topic"], ["success"]])
        assert state.properties["@lovecraft"]["known"] is True


class TestQuasiquote:
    """Tests for quasiquote, unquote, and unquote-splicing."""

    @pytest.fixture
    def evaluator(self):
        state = MockWorldState()
        state.bindings["x"] = 42
        state.bindings["nums"] = [1, 2, 3]
        state.bindings["condition"] = True
        return ExprEvaluator(state)

    def test_quasiquote_without_unquotes(self, evaluator):
        """Quasiquote without unquotes behaves like quote."""
        result = evaluator.eval(parse("`(a b c)"))
        assert result == ["a", "b", "c"]

    def test_quasiquote_unquote_variable(self, evaluator):
        """Unquote evaluates and inserts a variable."""
        result = evaluator.eval(parse("`(a ,x c)"))
        assert result == ["a", 42, "c"]

    def test_quasiquote_unquote_expression(self, evaluator):
        """Unquote evaluates and inserts an expression."""
        result = evaluator.eval(parse("`(a ,(+ 1 2) c)"))
        assert result == ["a", 3, "c"]

    def test_quasiquote_unquote_splicing(self, evaluator):
        """Unquote-splicing splices list elements."""
        result = evaluator.eval(parse("`(a ,@nums c)"))
        assert result == ["a", 1, 2, 3, "c"]

    def test_quasiquote_unquote_splicing_empty(self, evaluator):
        """Unquote-splicing with empty list contributes nothing."""
        evaluator.state.bindings["empty"] = []
        result = evaluator.eval(parse("`(a ,@empty c)"))
        assert result == ["a", "c"]

    def test_quasiquote_nested_lists(self, evaluator):
        """Quasiquote works with nested lists."""
        result = evaluator.eval(parse("`((set foo ,(+ 10 20)) (success))"))
        assert result == [["set", "foo", 30], ["success"]]

    def test_quasiquote_conditional_effects(self, evaluator):
        """Quasiquote with conditional effect inclusion."""
        evaluator.state.bindings["condition"] = True
        result = evaluator.eval(
            parse("`((effect1) ,@(if condition '((effect2)) '()) (success))")
        )
        assert result == [["effect1"], ["effect2"], ["success"]]

        evaluator.state.bindings["condition"] = False
        result = evaluator.eval(
            parse("`((effect1) ,@(if condition '((effect2)) '()) (success))")
        )
        assert result == [["effect1"], ["success"]]

    def test_quasiquote_multiple_unquotes(self, evaluator):
        """Multiple unquotes in same list."""
        evaluator.state.bindings["a"] = 1
        evaluator.state.bindings["b"] = 2
        result = evaluator.eval(parse("`(,a ,b ,(+ a b))"))
        assert result == [1, 2, 3]

    def test_unquote_splicing_requires_list(self, evaluator):
        """Unquote-splicing raises error if value is not a list."""
        with pytest.raises(EvalError) as excinfo:
            evaluator.eval(parse("`(a ,@x c)"))  # x=42, not a list
        assert "requires a list" in str(excinfo.value)

    def test_quasiquote_deeply_nested(self, evaluator):
        """Quasiquote with deeply nested structure."""
        result = evaluator.eval(parse("`((outer (inner ,x)))"))
        assert result == [["outer", ["inner", 42]]]


class TestParamTypeAnnotations:
    """Test type annotations on fn parameters."""

    def test_parse_param_list_no_types(self):
        from grue.sexpr import SList, Symbol, parse_param_list

        params, types = parse_param_list(SList([Symbol("?x"), Symbol("?y")]))
        assert params == ["x", "y"]
        assert types == {}

    def test_parse_param_list_with_type(self):
        from grue.sexpr import Keyword, SList, Symbol, parse_param_list

        params, types = parse_param_list(SList([Symbol("?seconds"), Keyword("number")]))
        assert params == ["seconds"]
        assert types == {"seconds": "number"}

    def test_parse_param_list_mixed_types(self):
        from grue.sexpr import Keyword, SList, Symbol, parse_param_list

        params, types = parse_param_list(
            SList([Symbol("?target"), Symbol("?value"), Keyword("string")])
        )
        assert params == ["target", "value"]
        assert types == {"value": "string"}

    def test_parse_param_list_all_types(self):
        from grue.sexpr import Keyword, SList, Symbol, parse_param_list

        params, types = parse_param_list(
            SList(
                [
                    Symbol("?a"),
                    Keyword("entity"),
                    Symbol("?b"),
                    Keyword("string"),
                    Symbol("?c"),
                    Keyword("number"),
                    Symbol("?d"),
                    Keyword("symbol"),
                ]
            )
        )
        assert params == ["a", "b", "c", "d"]
        assert types == {"a": "entity", "b": "string", "c": "number", "d": "symbol"}

    def test_parse_param_list_unknown_type(self):
        from grue.sexpr import Keyword, SList, Symbol, parse_param_list

        with pytest.raises(ValueError, match="Unknown parameter type"):
            parse_param_list(SList([Symbol("?x"), Keyword("bogus")]))

    def test_parse_param_list_require_question_mark(self):
        from grue.sexpr import SList, Symbol, parse_param_list

        with pytest.raises(ValueError, match="Expected \\?param"):
            parse_param_list(
                SList([Symbol("x")]),
                require_question_mark=True,
            )

    def test_fn_with_type_annotation(self):
        """fn form parses type annotations on parameters."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)

        fn = evaluator.eval(parse("(fn (?x :number) (+ ?x 1))"))
        assert fn.params == ["x"]
        assert fn.param_types == {"x": "number"}

    def test_fn_without_type_annotation(self):
        """fn form works without type annotations (backward compatible)."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)

        fn = evaluator.eval(parse("(fn (?x ?y) (+ ?x ?y))"))
        assert fn.params == ["x", "y"]
        assert fn.param_types == {}

    def test_fn_with_type_still_callable(self):
        """Functions with type annotations are still callable."""
        state = MockWorldState()
        evaluator = ExprEvaluator(state)

        fn = evaluator.eval(parse("(fn (?x :number) (+ ?x 1))"))
        result = evaluator.call_fn(fn, [5])
        assert result == 6
