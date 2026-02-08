"""Tests for partial evaluator (reducer)."""

import pytest
from grue.reduce import Reducer, reduce_expr, ReductionStats
from grue.sexpr import parse, to_string, SList, Symbol
from grue.forms import GrueWorld, GrueFunction


def make_world(functions=None, constants=None):
    """Create a minimal GrueWorld for testing."""
    world = GrueWorld()
    if functions:
        for name, (params, body_str) in functions.items():
            body = parse(body_str)
            world.functions[name] = GrueFunction(name=name, params=params, body=body)
    if constants:
        world.constants = constants
    return world


class TestBasicReduction:
    """Tests for basic expression reduction."""

    def test_reduce_literal_int(self):
        """Literals pass through unchanged."""
        world = make_world()
        expr = parse("42")
        result, _ = reduce_expr(world, expr)
        assert result == 42

    def test_reduce_literal_string(self):
        """String literals pass through."""
        world = make_world()
        expr = parse('"hello"')
        result, _ = reduce_expr(world, expr)
        assert result == "hello"

    def test_reduce_literal_bool(self):
        """Boolean literals pass through."""
        world = make_world()
        assert reduce_expr(world, parse("true"))[0] == True
        assert reduce_expr(world, parse("false"))[0] == False

    def test_reduce_symbol(self):
        """Unknown symbols pass through."""
        world = make_world()
        result, _ = reduce_expr(world, parse("@player"))
        assert isinstance(result, Symbol)
        assert result.name == "@player"

    def test_reduce_empty_list(self):
        """Empty list passes through."""
        world = make_world()
        result, _ = reduce_expr(world, parse("()"))
        assert isinstance(result, SList)
        assert len(result.items) == 0


class TestConstantPropagation:
    """Tests for constant propagation from (def name value)."""

    def test_propagate_numeric_constant(self):
        """Constants are substituted."""
        world = make_world(constants={"MAX_ITEMS": 10})
        result, stats = reduce_expr(world, parse("MAX_ITEMS"))
        assert result == 10
        assert stats.constants_propagated == 1

    def test_propagate_string_constant(self):
        """String constants are substituted."""
        world = make_world(constants={"GAME_NAME": "Lurking Horror"})
        result, _ = reduce_expr(world, parse("GAME_NAME"))
        assert result == "Lurking Horror"

    def test_propagate_list_constant(self):
        """List constants are converted to SList."""
        world = make_world(constants={"ROOMS": ["@room1", "@room2"]})
        result, _ = reduce_expr(world, parse("ROOMS"))
        assert isinstance(result, SList)
        assert len(result.items) == 2

    def test_constant_in_expression(self):
        """Constants in expressions are propagated."""
        world = make_world(constants={"LIMIT": 5})
        result, _ = reduce_expr(world, parse("(> x LIMIT)"))
        result_str = to_string(result)
        assert "5" in result_str
        assert "LIMIT" not in result_str


class TestConditionalSimplification:
    """Tests for simplifying if/cond/and/or expressions."""

    def test_if_true_condition(self):
        """(if true then else) -> then"""
        world = make_world()
        result, stats = reduce_expr(world, parse("(if true @a @b)"))
        assert isinstance(result, Symbol)
        assert result.name == "@a"
        assert stats.conditionals_simplified == 1

    def test_if_false_condition(self):
        """(if false then else) -> else"""
        world = make_world()
        result, stats = reduce_expr(world, parse("(if false @a @b)"))
        assert isinstance(result, Symbol)
        assert result.name == "@b"
        assert stats.conditionals_simplified == 1

    def test_if_false_no_else(self):
        """(if false then) -> nil"""
        world = make_world()
        result, _ = reduce_expr(world, parse("(if false @a)"))
        assert isinstance(result, Symbol)
        assert result.name == "nil"

    def test_if_unknown_condition(self):
        """Unknown condition keeps if structure."""
        world = make_world()
        result, _ = reduce_expr(world, parse("(if (held? @key) @a @b)"))
        result_str = to_string(result)
        assert result_str.startswith("(if")

    def test_cond_first_true(self):
        """(cond (true a) (x b)) -> a"""
        world = make_world()
        result, _ = reduce_expr(world, parse("(cond (true @first) (other @second))"))
        assert isinstance(result, Symbol)
        assert result.name == "@first"

    def test_cond_skip_false(self):
        """False clauses are removed from cond."""
        world = make_world()
        result, stats = reduce_expr(world, parse("(cond (false @skip) (true @keep))"))
        assert isinstance(result, Symbol)
        assert result.name == "@keep"
        assert stats.conditionals_simplified >= 2  # One for false skip, one for true match

    def test_cond_all_false(self):
        """(cond (false a) (false b)) -> nil"""
        world = make_world()
        result, _ = reduce_expr(world, parse("(cond (false @a) (false @b))"))
        assert isinstance(result, Symbol)
        assert result.name == "nil"

    def test_cond_preserves_unknown(self):
        """Unknown conditions are preserved."""
        world = make_world()
        result, _ = reduce_expr(world, parse("(cond ((= x 1) @a) ((= x 2) @b))"))
        result_str = to_string(result)
        assert "cond" in result_str

    def test_and_short_circuit_false(self):
        """(and false x) -> false"""
        world = make_world()
        result, _ = reduce_expr(world, parse("(and false (expensive-call))"))
        assert result == False

    def test_and_skip_true(self):
        """(and true true x) -> x"""
        world = make_world()
        result, _ = reduce_expr(world, parse("(and true true @remaining)"))
        assert isinstance(result, Symbol)
        assert result.name == "@remaining"

    def test_and_all_true(self):
        """(and true true) -> true"""
        world = make_world()
        result, _ = reduce_expr(world, parse("(and true true)"))
        assert result == True

    def test_and_empty(self):
        """(and) -> true"""
        world = make_world()
        result, _ = reduce_expr(world, parse("(and)"))
        assert result == True

    def test_or_short_circuit_true(self):
        """(or true x) -> true"""
        world = make_world()
        result, _ = reduce_expr(world, parse("(or true (expensive-call))"))
        assert result == True

    def test_or_skip_false(self):
        """(or false false x) -> x"""
        world = make_world()
        result, _ = reduce_expr(world, parse("(or false false @remaining)"))
        assert isinstance(result, Symbol)
        assert result.name == "@remaining"

    def test_or_all_false(self):
        """(or false false) -> false"""
        world = make_world()
        result, _ = reduce_expr(world, parse("(or false false)"))
        assert result == False

    def test_or_empty(self):
        """(or) -> false"""
        world = make_world()
        result, _ = reduce_expr(world, parse("(or)"))
        assert result == False

    def test_not_true(self):
        """(not true) -> false"""
        world = make_world()
        result, _ = reduce_expr(world, parse("(not true)"))
        assert result == False

    def test_not_false(self):
        """(not false) -> true"""
        world = make_world()
        result, _ = reduce_expr(world, parse("(not false)"))
        assert result == True

    def test_not_unknown(self):
        """(not x) preserved when x unknown."""
        world = make_world()
        result, _ = reduce_expr(world, parse("(not (held? @key))"))
        result_str = to_string(result)
        assert result_str.startswith("(not")


class TestFunctionInlining:
    """Tests for inlining user-defined functions."""

    def test_inline_simple_function(self):
        """Simple function call is inlined."""
        world = make_world(functions={
            "double": (["x"], "(+ ?x ?x)")
        })
        result, stats = reduce_expr(world, parse("(double 5)"))
        result_str = to_string(result)
        # After inlining, should have (+ 5 5)
        assert "5" in result_str
        assert "double" not in result_str
        assert stats.functions_inlined == 1

    def test_inline_with_object_ref(self):
        """Function with object reference."""
        world = make_world(functions={
            "at-room": (["room"], "(= (loc @player) ?room)")
        })
        result, _ = reduce_expr(world, parse("(at-room @lobby)"))
        result_str = to_string(result)
        assert "@lobby" in result_str
        assert "at-room" not in result_str

    def test_inline_nested_function(self):
        """Nested function calls are both inlined."""
        world = make_world(functions={
            "inc": (["x"], "(+ ?x 1)"),
            "double-inc": (["x"], "(inc (inc ?x))")
        })
        result, stats = reduce_expr(world, parse("(double-inc 3)"))
        result_str = to_string(result)
        # Both inc calls should be inlined
        assert "inc" not in result_str
        assert stats.functions_inlined == 3  # double-inc + 2 inc calls

    def test_inline_function_with_cond(self):
        """Function with cond body."""
        world = make_world(functions={
            "waxer-next-loc": (["loc", "going-west"], """
                (cond
                    (?going-west
                        (cond
                            ((= ?loc @inf-5) @inf-4)
                            ((= ?loc @inf-4) @inf-3)
                            (true @inf-1)))
                    (true
                        (cond
                            ((= ?loc @inf-1) @inf-2)
                            ((= ?loc @inf-2) @inf-3)
                            (true @inf-5))))
            """)
        })
        # Call with going-west = true
        result, stats = reduce_expr(world, parse("(waxer-next-loc @inf-5 true)"))
        # Since going-west is true, first branch is taken, and (= @inf-5 @inf-5) is true
        assert isinstance(result, Symbol)
        assert result.name == "@inf-4"
        assert stats.functions_inlined == 1

    def test_inline_respects_parameter_names(self):
        """Parameter binding works correctly."""
        world = make_world(functions={
            # Use (loc ...) which can't be statically evaluated
            "swap-check": (["a", "b"], "(and (= (loc ?a) @room) (= (loc ?b) @other))")
        })
        result, _ = reduce_expr(world, parse("(swap-check @first @second)"))
        result_str = to_string(result)
        # After substitution, should have (loc @first) and (loc @second)
        assert "@first" in result_str
        assert "@second" in result_str


class TestRecursionHandling:
    """Tests for handling recursive functions."""

    def test_direct_recursion_limited(self):
        """Direct recursion hits depth limit."""
        world = make_world(functions={
            "countdown": (["n"], "(if (= ?n 0) done (countdown (- ?n 1)))")
        })
        result, stats = reduce_expr(world, parse("(countdown 100)"), max_depth=5)
        # Should hit recursion limit
        assert stats.recursion_limits_hit > 0
        # Result should still contain countdown call (not infinitely inlined)
        result_str = to_string(result)
        assert "countdown" in result_str

    def test_mutual_recursion_limited(self):
        """Mutual recursion also limited."""
        world = make_world(functions={
            "even": (["n"], "(if (= ?n 0) true (odd (- ?n 1)))"),
            "odd": (["n"], "(if (= ?n 0) false (even (- ?n 1)))")
        })
        result, stats = reduce_expr(world, parse("(even 20)"), max_depth=3)
        # Should hit some limit
        result_str = to_string(result)
        # The result should contain unevaluated calls
        assert "even" in result_str or "odd" in result_str

    def test_non_recursive_deep_nesting(self):
        """Deep nesting of different functions works."""
        world = make_world(functions={
            "f1": (["x"], "(f2 ?x)"),
            "f2": (["x"], "(f3 ?x)"),
            "f3": (["x"], "(f4 ?x)"),
            "f4": (["x"], "(+ ?x 1)")
        })
        result, stats = reduce_expr(world, parse("(f1 10)"), max_depth=10)
        result_str = to_string(result)
        # Should fully inline all functions
        assert "10" in result_str
        assert stats.functions_inlined == 4


class TestLetExpressions:
    """Tests for let expression handling."""

    def test_let_basic(self):
        """Basic let binding works."""
        world = make_world()
        result, _ = reduce_expr(world, parse("(let ((x 5)) (+ x 1))"))
        result_str = to_string(result)
        assert "5" in result_str

    def test_let_with_question_mark(self):
        """Let with ?-prefixed names works."""
        world = make_world()
        result, _ = reduce_expr(world, parse("(let ((?x @room)) ?x)"))
        result_str = to_string(result)
        assert "@room" in result_str

    def test_let_shadows_constant(self):
        """Let binding shadows outer constants."""
        world = make_world(constants={"x": 100})
        result, _ = reduce_expr(world, parse("(let ((x 5)) x)"))
        # The let binding should shadow the constant
        result_str = to_string(result)
        # Inner binding should take effect
        assert "5" in result_str


class TestQuotedExpressions:
    """Tests for quote and quasiquote handling."""

    def test_quote_not_reduced(self):
        """Quoted expressions are not reduced."""
        world = make_world(constants={"x": 100})
        result, _ = reduce_expr(world, parse("'(x y z)"))
        result_str = to_string(result)
        # x should NOT be replaced with 100
        assert "100" not in result_str
        assert "x" in result_str

    def test_quasiquote_reduces_unquote(self):
        """Unquoted parts in quasiquote are reduced."""
        world = make_world(constants={"val": 42})
        result, _ = reduce_expr(world, parse("`(list ,val)"))
        result_str = to_string(result)
        # val should be replaced with 42 inside the unquote
        assert "42" in result_str


class TestFnExpressions:
    """Tests for lambda expression handling."""

    def test_fn_body_reduced(self):
        """Lambda body is reduced."""
        world = make_world(constants={"MAX": 10})
        result, _ = reduce_expr(world, parse("(fn (?x) (< ?x MAX))"))
        result_str = to_string(result)
        # MAX should be replaced in the body
        assert "10" in result_str
        assert "MAX" not in result_str

    def test_fn_param_not_replaced(self):
        """Lambda parameters are not replaced by outer bindings."""
        world = make_world(constants={"x": 100})
        result, _ = reduce_expr(world, parse("(fn (?x) (+ ?x 1))"))
        result_str = to_string(result)
        # ?x should NOT be replaced with 100
        assert "100" not in result_str
        assert "?x" in result_str


class TestRealWorldExamples:
    """Tests based on real patterns from Lurking Horror."""

    def test_waxer_next_loc_going_west(self):
        """Waxer location function with going-west=true."""
        world = make_world(functions={
            "waxer-next-loc": (["loc", "going-west"], """
                (cond
                    (?going-west
                        (cond
                            ((= ?loc @inf-5) @inf-4)
                            ((= ?loc @inf-4) @inf-3)
                            ((= ?loc @inf-3) @inf-2)
                            ((= ?loc @inf-2) @inf-1)
                            (true @inf-1)))
                    (true
                        (cond
                            ((= ?loc @inf-1) @inf-2)
                            ((= ?loc @inf-2) @inf-3)
                            ((= ?loc @inf-3) @inf-4)
                            ((= ?loc @inf-4) @inf-5)
                            (true @inf-5))))
            """)
        })

        # Test with known going-west = true and known location
        result, _ = reduce_expr(world, parse("(waxer-next-loc @inf-3 true)"))
        assert isinstance(result, Symbol)
        assert result.name == "@inf-2"

        # Test with known going-west = false and known location
        result, _ = reduce_expr(world, parse("(waxer-next-loc @inf-3 false)"))
        assert isinstance(result, Symbol)
        assert result.name == "@inf-4"

    def test_waxer_next_loc_unknown_location(self):
        """Waxer function with unknown location but known direction."""
        world = make_world(functions={
            "waxer-next-loc": (["loc", "going-west"], """
                (cond
                    (?going-west
                        (cond
                            ((= ?loc @inf-5) @inf-4)
                            ((= ?loc @inf-4) @inf-3)
                            (true @inf-1)))
                    (true
                        (cond
                            ((= ?loc @inf-1) @inf-2)
                            (true @inf-5))))
            """)
        })

        # With unknown ?loc but going-west=true, cond structure preserved
        result, _ = reduce_expr(world, parse("(waxer-next-loc ?current-loc true)"))
        result_str = to_string(result)
        # Should have simplified outer cond (since going-west=true)
        # but kept inner cond since ?current-loc is unknown
        assert "cond" in result_str
        assert "@inf-4" in result_str  # One of the branches
        # Should NOT have the going-west branch structure anymore
        assert "going-west" not in result_str

    def test_elevator_floor_lookup(self):
        """Pattern from elevator floor lookup."""
        world = make_world(
            constants={
                "floor-rooms": ["@cs-basement", "@comp-center", "@cs-2nd", "@cs-3rd"]
            },
            functions={
                # Get :floor property from @elevator object
                "elevator-at-floor?": (["floor"], "(= (:floor @elevator) ?floor)")
            }
        )
        result, _ = reduce_expr(world, parse("(elevator-at-floor? 2)"))
        result_str = to_string(result)
        # After inlining, should have the floor number substituted
        assert "2" in result_str
        assert "elevator-at-floor?" not in result_str


class TestEdgeCases:
    """Edge cases and potential error conditions."""

    def test_missing_function_preserved(self):
        """Call to undefined function is preserved."""
        world = make_world()
        result, _ = reduce_expr(world, parse("(unknown-fn @arg)"))
        result_str = to_string(result)
        assert "unknown-fn" in result_str

    def test_malformed_if_preserved(self):
        """Malformed if is preserved."""
        world = make_world()
        result, _ = reduce_expr(world, parse("(if)"))  # No args
        result_str = to_string(result)
        assert "if" in result_str

    def test_deeply_nested_structure(self):
        """Deep nesting doesn't cause issues."""
        world = make_world()
        deep = "(if true " * 20 + "@result" + ")" * 20
        result, stats = reduce_expr(world, parse(deep))
        # Should reduce to just @result
        assert isinstance(result, Symbol)
        assert result.name == "@result"
        assert stats.conditionals_simplified == 20

    def test_nil_handling(self):
        """nil is handled correctly."""
        world = make_world()
        result, _ = reduce_expr(world, parse("nil"))
        assert isinstance(result, Symbol)
        assert result.name == "nil"

    def test_function_missing_args(self):
        """Function call with fewer args than params."""
        world = make_world(functions={
            "needs-two": (["a", "b"], "(+ ?a ?b)")
        })
        result, _ = reduce_expr(world, parse("(needs-two 5)"))
        result_str = to_string(result)
        # Should have 5 and nil
        assert "5" in result_str
        assert "nil" in result_str


class TestStatistics:
    """Tests for reduction statistics tracking."""

    def test_stats_functions_inlined(self):
        """Functions inlined count is accurate."""
        world = make_world(functions={
            "f": ([], "@result")
        })
        _, stats = reduce_expr(world, parse("(and (f) (f) (f))"))
        assert stats.functions_inlined == 3

    def test_stats_constants_propagated(self):
        """Constants propagated count is accurate."""
        world = make_world(constants={"A": 1, "B": 2, "C": 3})
        _, stats = reduce_expr(world, parse("(+ A B C)"))
        assert stats.constants_propagated == 3

    def test_stats_conditionals_simplified(self):
        """Conditionals simplified count is accurate."""
        world = make_world()
        _, stats = reduce_expr(world, parse("(and true (or false true) (not false))"))
        # and: 1 true eliminated, or: 1 false eliminated + result, not: 1
        assert stats.conditionals_simplified >= 3
