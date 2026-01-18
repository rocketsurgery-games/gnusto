"""
Tests for pure Grue language features.

These tests exercise the language constructs (fn, defn, if, let, cond)
independent of the game runtime, treating Grue as a general-purpose
functional language.
"""

import pytest
from grue.sexpr import parse
from grue.expr import ExprEvaluator, EffectExecutor, GrueFn, EvalError
from grue.parser import parse_grue
from grue.runtime import GrueRuntime


# === Minimal state for pure language tests ===

class MinimalState:
    """Minimal state that provides just enough for expression evaluation."""

    def __init__(self):
        self._globals: dict = {}
        self._objects: dict = {}

    def get_global(self, name: str):
        if name in self._globals:
            return self._globals[name]
        raise KeyError(name)

    def set_global(self, name: str, value):
        self._globals[name] = value


# === Tests for (fn ...) anonymous functions ===

class TestAnonymousFunctions:
    """Test (fn (params) body) anonymous function creation and application."""

    def test_fn_creates_grue_fn(self):
        """(fn () body) should create a GrueFn value."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(fn () 42)"))
        assert isinstance(result, GrueFn)
        assert result.params == []

    def test_fn_with_params(self):
        """(fn (x y) body) should capture parameter names."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(fn (x y) (= x y))"))
        assert isinstance(result, GrueFn)
        assert result.params == ["x", "y"]

    def test_fn_with_question_mark_params(self):
        """Parameters with ? prefix should have it stripped."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(fn (?x ?y) (= ?x ?y))"))
        assert result.params == ["x", "y"]

    def test_fn_immediate_application(self):
        """((fn (x) x) 42) should apply the function immediately."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("((fn (x) x) 42)"))
        assert result == 42

    def test_fn_multi_arg_application(self):
        """((fn (a b) (= a b)) 1 1) should work with multiple args."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("((fn (a b) (= a b)) 1 1)"))
        assert result is True
        result = evaluator.eval(parse("((fn (a b) (= a b)) 1 2)"))
        assert result is False


# === Tests for (defn ...) named function definitions ===

class TestDefn:
    """Test (defn name (params) body) named function definitions."""

    def test_defn_registers_function(self):
        """(defn foo () ...) should register a callable function."""
        state = MinimalState()
        functions = {}
        evaluator = ExprEvaluator(state, functions)
        evaluator.eval(parse("(defn always-true () true)"))
        assert "always-true" in functions
        assert isinstance(functions["always-true"], GrueFn)

    def test_defn_returns_nil(self):
        """defn should return nil/None."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(defn foo () 42)"))
        assert result is None

    def test_call_defn_function(self):
        """A function defined with defn should be callable."""
        state = MinimalState()
        functions = {}
        evaluator = ExprEvaluator(state, functions)
        evaluator.eval(parse("(defn double (x) (+ x x))"))
        # Note: + isn't defined, so we'll use a simpler test
        evaluator.eval(parse("(defn identity (x) x)"))
        result = evaluator.eval(parse("(identity 42)"))
        assert result == 42

    def test_defn_with_question_mark_params(self):
        """defn should strip ? from param names."""
        state = MinimalState()
        functions = {}
        evaluator = ExprEvaluator(state, functions)
        evaluator.eval(parse("(defn greet (?name) ?name)"))
        result = evaluator.eval(parse('(greet "Alice")'))
        assert result == "Alice"

    def test_defn_via_effect_executor(self):
        """defn should also work via EffectExecutor."""
        state = MinimalState()
        state.get_global = lambda name: state._globals.get(name, name)
        functions = {}
        executor = EffectExecutor(state, functions)
        executor.execute(parse("(defn check () true)"))
        assert "check" in functions

        evaluator = ExprEvaluator(state, functions)
        result = evaluator.eval(parse("(check)"))
        assert result is True


# === Tests for (if ...) conditional expressions ===

class TestIf:
    """Test (if condition then else) conditional expressions."""

    def test_if_true_branch(self):
        """(if true then else) should evaluate then branch."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse('(if true "yes" "no")'))
        assert result == "yes"

    def test_if_false_branch(self):
        """(if false then else) should evaluate else branch."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse('(if false "yes" "no")'))
        assert result == "no"

    def test_if_without_else(self):
        """(if condition then) should return nil when false."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse('(if false "yes")'))
        assert result is None

    def test_if_nested(self):
        """if expressions can be nested."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse('(if false "a" (if true "b" "c"))'))
        assert result == "b"

    def test_if_with_comparison(self):
        """if should work with comparison expressions."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(if (> 5 3) 1 0)"))
        assert result == 1


# === Tests for (let ...) local bindings ===

class TestLet:
    """Test (let ((name value) ...) body) local bindings."""

    def test_let_single_binding(self):
        """(let ((x 1)) x) should bind x to 1."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(let ((x 42)) x)"))
        assert result == 42

    def test_let_multiple_bindings(self):
        """(let ((x 1) (y 2)) ...) should support multiple bindings."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(let ((x 10) (y 20)) (= x 10))"))
        assert result is True

    def test_let_bindings_in_body(self):
        """Let-bound values should be available in the body."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(let ((answer 42)) (= answer 42))"))
        assert result is True

    def test_let_with_question_mark(self):
        """Let should work with ?-prefixed binding names."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("(let ((?x 99)) ?x)"))
        assert result == 99


# === Tests for (cond ...) multi-branch conditionals ===

class TestCond:
    """Test (cond (test result) ...) multi-branch conditionals."""

    def test_cond_first_true(self):
        """cond should return result of first true test."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse('(cond (true "first") (true "second"))'))
        assert result == "first"

    def test_cond_skip_false(self):
        """cond should skip false tests."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse('(cond (false "first") (true "second"))'))
        assert result == "second"

    def test_cond_all_false(self):
        """cond should return nil if all tests are false."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse('(cond (false "a") (false "b"))'))
        assert result is None

    def test_cond_with_comparisons(self):
        """cond should work with comparison expressions."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("""
            (cond
                ((< 5 3) "less")
                ((= 5 5) "equal")
                (true "default"))
        """))
        assert result == "equal"


# === Tests for world-level function definitions ===

class TestWorldLevelDefn:
    """Test functions defined at the world level in .grue files."""

    def test_defn_in_world_file(self):
        """Functions defined at world level should be available at runtime."""
        world = parse_grue("""
            (world :name "test")

            (defn always-42 () 42)

            (room LOBBY :desc "A lobby")

            (object PLAYER :location LOBBY :properties (:person true))
        """)

        assert "always-42" in world.functions
        assert world.functions["always-42"].params == []

        runtime = GrueRuntime(world)
        evaluator = ExprEvaluator(runtime, runtime._functions)
        result = evaluator.eval(parse("(always-42)"))
        assert result == 42

    def test_defn_with_params_in_world(self):
        """World-level defn should support parameters."""
        world = parse_grue("""
            (world :name "test")

            (defn is-equal? (a b) (= a b))

            (room LOBBY :desc "A lobby")
            (object PLAYER :location LOBBY :properties (:person true))
        """)

        runtime = GrueRuntime(world)
        evaluator = ExprEvaluator(runtime, runtime._functions)
        assert evaluator.eval(parse("(is-equal? 1 1)")) is True
        assert evaluator.eval(parse("(is-equal? 1 2)")) is False

    def test_multiple_defns_in_world(self):
        """Multiple functions can be defined at world level."""
        world = parse_grue("""
            (world :name "test")

            (defn first-fn () 1)
            (defn second-fn () 2)
            (defn third-fn () 3)

            (room LOBBY :desc "A lobby")
            (object PLAYER :location LOBBY :properties (:person true))
        """)

        assert len(world.functions) == 3
        runtime = GrueRuntime(world)
        evaluator = ExprEvaluator(runtime, runtime._functions)
        assert evaluator.eval(parse("(first-fn)")) == 1
        assert evaluator.eval(parse("(second-fn)")) == 2
        assert evaluator.eval(parse("(third-fn)")) == 3

    def test_defn_can_call_other_defn(self):
        """World-level functions can call each other."""
        world = parse_grue("""
            (world :name "test")

            (defn inner () 42)
            (defn outer () (inner))

            (room LOBBY :desc "A lobby")
            (object PLAYER :location LOBBY :properties (:person true))
        """)

        runtime = GrueRuntime(world)
        evaluator = ExprEvaluator(runtime, runtime._functions)
        result = evaluator.eval(parse("(outer)"))
        assert result == 42


# === Tests for combining language features ===

class TestLanguageCombinations:
    """Test combinations of fn, defn, if, let, cond."""

    def test_defn_with_if(self):
        """defn body can use if."""
        state = MinimalState()
        functions = {}
        evaluator = ExprEvaluator(state, functions)
        evaluator.eval(parse("""
            (defn max (a b)
                (if (> a b) a b))
        """))
        assert evaluator.eval(parse("(max 10 5)")) == 10
        assert evaluator.eval(parse("(max 3 7)")) == 7

    def test_defn_with_cond(self):
        """defn body can use cond."""
        state = MinimalState()
        functions = {}
        evaluator = ExprEvaluator(state, functions)
        evaluator.eval(parse("""
            (defn classify (n)
                (cond
                    ((< n 0) "negative")
                    ((= n 0) "zero")
                    (true "positive")))
        """))
        assert evaluator.eval(parse("(classify -5)")) == "negative"
        assert evaluator.eval(parse("(classify 0)")) == "zero"
        assert evaluator.eval(parse("(classify 10)")) == "positive"

    def test_defn_with_let(self):
        """defn body can use let."""
        state = MinimalState()
        functions = {}
        evaluator = ExprEvaluator(state, functions)
        evaluator.eval(parse("""
            (defn add-ten (x)
                (let ((ten 10))
                    (let ((result x))
                        (= result x))))
        """))
        result = evaluator.eval(parse("(add-ten 5)"))
        assert result is True

    def test_fn_inside_defn(self):
        """defn body can return an anonymous function."""
        state = MinimalState()
        functions = {}
        evaluator = ExprEvaluator(state, functions)
        evaluator.eval(parse("(defn make-checker () (fn (x) (= x 42)))"))
        checker = evaluator.eval(parse("(make-checker)"))
        assert isinstance(checker, GrueFn)

    def test_let_with_fn(self):
        """let can bind anonymous functions."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        result = evaluator.eval(parse("""
            (let ((check (fn (x) (= x 42))))
                ((fn (f) (f 42)) check))
        """))
        assert result is True


# === Error handling tests ===

class TestLanguageErrors:
    """Test error handling for language constructs."""

    def test_defn_wrong_arity(self):
        """defn should error on wrong argument count."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        with pytest.raises(EvalError, match="expects 3 arguments"):
            evaluator.eval(parse("(defn foo)"))

    def test_defn_name_must_be_symbol(self):
        """defn name must be a symbol."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        with pytest.raises(EvalError, match="must be a symbol"):
            evaluator.eval(parse('(defn "foo" () 42)'))

    def test_defn_params_must_be_list(self):
        """defn params must be a list."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        with pytest.raises(EvalError, match="must be a list"):
            evaluator.eval(parse("(defn foo x 42)"))

    def test_if_too_few_args(self):
        """if should error with too few arguments."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        with pytest.raises(EvalError, match="if"):
            evaluator.eval(parse("(if)"))

    def test_fn_call_wrong_arity(self):
        """Calling a function with wrong arity should error."""
        state = MinimalState()
        functions = {}
        evaluator = ExprEvaluator(state, functions)
        evaluator.eval(parse("(defn needs-two (a b) true)"))
        with pytest.raises(EvalError, match="expects 2 arguments"):
            evaluator.eval(parse("(needs-two 1)"))


# === Arithmetic operators tests ===

class TestArithmetic:
    """Test arithmetic operators (+, -, *, /, mod)."""

    def test_add_two_numbers(self):
        """(+ 2 3) should return 5."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(+ 2 3)")) == 5

    def test_add_variadic(self):
        """(+ 1 2 3 4 5) should return 15."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(+ 1 2 3 4 5)")) == 15

    def test_add_zero_args(self):
        """(+) should return 0."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(+)")) == 0

    def test_subtract_two_numbers(self):
        """(- 10 3) should return 7."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(- 10 3)")) == 7

    def test_subtract_unary(self):
        """(- 5) should return -5."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(- 5)")) == -5

    def test_subtract_variadic(self):
        """(- 20 5 3 2) should return 10."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(- 20 5 3 2)")) == 10

    def test_multiply_two_numbers(self):
        """(* 4 5) should return 20."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(* 4 5)")) == 20

    def test_multiply_variadic(self):
        """(* 2 3 4) should return 24."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(* 2 3 4)")) == 24

    def test_multiply_zero_args(self):
        """(*) should return 1."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(*)")) == 1

    def test_divide_two_numbers(self):
        """(/ 20 4) should return 5."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(/ 20 4)")) == 5

    def test_divide_integer_truncation(self):
        """(/ 7 2) should return 3 (integer division)."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(/ 7 2)")) == 3

    def test_divide_by_zero(self):
        """(/ 10 0) should raise error."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        with pytest.raises(EvalError, match="Division by zero"):
            evaluator.eval(parse("(/ 10 0)"))

    def test_mod(self):
        """(mod 17 5) should return 2."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        assert evaluator.eval(parse("(mod 17 5)")) == 2

    def test_mod_by_zero(self):
        """(mod 10 0) should raise error."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        with pytest.raises(EvalError, match="Modulo by zero"):
            evaluator.eval(parse("(mod 10 0)"))

    def test_nested_arithmetic(self):
        """Arithmetic can be nested."""
        state = MinimalState()
        evaluator = ExprEvaluator(state)
        # (+ (* 3 4) (- 10 5)) = 12 + 5 = 17
        assert evaluator.eval(parse("(+ (* 3 4) (- 10 5))")) == 17

    def test_arithmetic_in_defn(self):
        """Arithmetic works in user-defined functions."""
        state = MinimalState()
        functions = {}
        evaluator = ExprEvaluator(state, functions)
        evaluator.eval(parse("(defn double (x) (* x 2))"))
        assert evaluator.eval(parse("(double 21)")) == 42
