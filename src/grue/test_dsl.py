"""
Grue-native test DSL.

Tests are S-expressions that exercise the full Grue stack:

    (test "door opens from mass-ave"
      :action (do :verb open :object OUTSIDE-DOOR)
      :expect ((outcome? success)
               (context? mechanism push-bar)))

    (test "door blocked from great-court"
      :setup ((move! PLAYER GREAT-COURT))
      :action (do :verb open :object OUTSIDE-DOOR)
      :expect ((outcome? blocked)
               (reason? locked-from-outside)))

Test forms:
    (test NAME :setup EFFECTS :action ACTION :expect PREDICATES)

    (test-sequence NAME
      :setup EFFECTS              ; optional, runs once at start
      (step :action A :expect P)  ; first step
      (step :action A :expect P)  ; second step, state persists
      ...)

Special predicates for :expect:
    (outcome? OUTCOME)        - Check action outcome (success, blocked, error, redirect)
    (reason? REASON)          - Check blocked/error reason
    (context? KEY VALUE)      - Check context contains key=value
    (changed? OBJ PROP FROM TO) - Check property changed
    (flag-set? OBJ FLAG)      - Check flag was set by action
    (flag-cleared? OBJ FLAG)  - Check flag was cleared by action

Setup effects use standard effect forms:
    (move! OBJ DEST)
    (set-flag! OBJ FLAG)
    (clear-flag! OBJ FLAG)
    (set-prop! OBJ PROP VALUE)
    (defn NAME (PARAMS) BODY)  ; define helper functions

Usage:
    from grue.test_dsl import run_tests
    results = run_tests("path/to/world.grue", "path/to/tests.grue")
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .sexpr import SExpr, Symbol, Keyword, SList, parse, parse_all, to_string
from .parser import load_grue, GrueWorld
from .runtime import GrueRuntime, ActionResult, GrueStateAdapter
from .expr import ExprEvaluator, EffectExecutor, EvalError


@dataclass
class TestResult:
    """Result of running a single test."""
    name: str
    passed: bool
    failures: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class TestSuiteResult:
    """Result of running a test suite."""
    world_path: str
    test_path: str
    results: list[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed and not r.error)

    @property
    def errored(self) -> int:
        return sum(1 for r in self.results if r.error)

    @property
    def total(self) -> int:
        return len(self.results)


class TestRunner:
    """
    Runs Grue-native tests against a world.

    Each test gets a fresh copy of the world state.
    """

    def __init__(self, world: GrueWorld):
        self.world = world
        # Shared function definitions across tests
        self._functions: dict[str, tuple[list[str], SExpr]] = {}

    def run_test(self, test_form: SList) -> TestResult:
        """
        Run a single (test ...) form.

        Format: (test NAME :setup EFFECTS :action ACTION :expect PREDICATES)
        """
        # Parse test form
        if len(test_form) < 2:
            return TestResult(
                name="<invalid>",
                passed=False,
                error="Test form too short"
            )

        name = test_form[1]
        if isinstance(name, str):
            test_name = name
        elif isinstance(name, Symbol):
            test_name = name.name
        else:
            test_name = to_string(name)

        # Parse keyword arguments
        setup_effects: list[SExpr] = []
        action: SExpr | None = None
        expect_predicates: list[SExpr] = []

        i = 2
        while i < len(test_form):
            item = test_form[i]
            if isinstance(item, Keyword):
                if i + 1 >= len(test_form):
                    return TestResult(
                        name=test_name,
                        passed=False,
                        error=f"Missing value for :{item.name}"
                    )
                value = test_form[i + 1]

                if item.name == "setup":
                    if isinstance(value, SList):
                        setup_effects = list(value.items)
                elif item.name == "action":
                    action = value
                elif item.name == "expect":
                    if isinstance(value, SList):
                        expect_predicates = list(value.items)
                i += 2
            else:
                i += 1

        if action is None:
            return TestResult(
                name=test_name,
                passed=False,
                error="Test missing :action"
            )

        # Create fresh runtime for this test
        runtime = GrueRuntime(self.world)
        # Use adapter for mutable state operations
        state_adapter = GrueStateAdapter(runtime.state)
        # Share function definitions
        executor = EffectExecutor(state_adapter, self._functions)

        try:
            # Run setup effects
            for effect in setup_effects:
                executor.execute(effect)

            # Execute action
            result = self._execute_action(runtime, action)

            # Check expectations
            failures = self._check_expectations(runtime, result, expect_predicates)

            return TestResult(
                name=test_name,
                passed=len(failures) == 0,
                failures=failures
            )

        except Exception as e:
            return TestResult(
                name=test_name,
                passed=False,
                error=str(e)
            )

    def run_test_sequence(self, seq_form: SList) -> TestResult:
        """
        Run a (test-sequence ...) form.

        Format:
            (test-sequence NAME
              :setup EFFECTS
              (step :action ACTION :expect PREDICATES)
              (step :action ACTION :expect PREDICATES)
              ...)

        State persists across steps within the sequence.
        """
        if len(seq_form) < 2:
            return TestResult(
                name="<invalid>",
                passed=False,
                error="Test-sequence form too short"
            )

        name = seq_form[1]
        if isinstance(name, str):
            test_name = name
        elif isinstance(name, Symbol):
            test_name = name.name
        else:
            test_name = to_string(name)

        # Parse initial :setup and collect steps
        setup_effects: list[SExpr] = []
        steps: list[SList] = []

        i = 2
        while i < len(seq_form):
            item = seq_form[i]

            if isinstance(item, Keyword):
                if i + 1 >= len(seq_form):
                    return TestResult(
                        name=test_name,
                        passed=False,
                        error=f"Missing value for :{item.name}"
                    )
                value = seq_form[i + 1]

                if item.name == "setup":
                    if isinstance(value, SList):
                        setup_effects = list(value.items)
                i += 2

            elif isinstance(item, SList) and len(item) > 0:
                head = item[0]
                if isinstance(head, Symbol) and head.name == "step":
                    steps.append(item)
                i += 1
            else:
                i += 1

        if not steps:
            return TestResult(
                name=test_name,
                passed=False,
                error="Test-sequence has no steps"
            )

        # Create ONE runtime for the whole sequence - state persists!
        runtime = GrueRuntime(self.world)
        state_adapter = GrueStateAdapter(runtime.state)
        executor = EffectExecutor(state_adapter, self._functions)

        all_failures: list[str] = []

        try:
            # Run setup effects once
            for effect in setup_effects:
                executor.execute(effect)

            # Run each step in sequence
            for step_idx, step in enumerate(steps, 1):
                step_action = None
                step_expects: list[SExpr] = []

                # Parse step form: (step :action A :expect P)
                j = 1
                while j < len(step):
                    item = step[j]
                    if isinstance(item, Keyword):
                        if j + 1 >= len(step):
                            all_failures.append(f"Step {step_idx}: Missing value for :{item.name}")
                            break
                        value = step[j + 1]

                        if item.name == "action":
                            step_action = value
                        elif item.name == "expect":
                            if isinstance(value, SList):
                                step_expects = list(value.items)
                        j += 2
                    else:
                        j += 1

                if step_action is None:
                    all_failures.append(f"Step {step_idx}: Missing :action")
                    continue

                # Execute this step's action
                result = self._execute_action(runtime, step_action)

                # Check this step's expectations
                step_failures = self._check_expectations(runtime, result, step_expects)

                for failure in step_failures:
                    all_failures.append(f"Step {step_idx}: {failure}")

            return TestResult(
                name=test_name,
                passed=len(all_failures) == 0,
                failures=all_failures
            )

        except Exception as e:
            return TestResult(
                name=test_name,
                passed=False,
                error=str(e)
            )

    def _execute_action(self, runtime: GrueRuntime, action: SExpr) -> ActionResult:
        """Execute an action form and return the result."""
        if not isinstance(action, SList) or len(action) == 0:
            raise EvalError(f"Invalid action: {action}")

        head = action[0]
        if not isinstance(head, Symbol):
            raise EvalError(f"Action must start with symbol: {action}")

        name = head.name

        if name == "do":
            # Parse (do :verb V :object O :with W ...)
            kwargs = self._parse_kwargs(action)
            verb = kwargs.get("verb")
            obj = kwargs.get("object")
            with_obj = kwargs.get("with")

            if verb is None:
                raise EvalError("(do ...) requires :verb")

            extra = {}
            if with_obj:
                extra["with"] = with_obj

            return runtime.do(verb, obj, **extra)

        elif name == "go":
            # Parse (go :direction D)
            kwargs = self._parse_kwargs(action)
            direction = kwargs.get("direction")
            if direction is None:
                raise EvalError("(go ...) requires :direction")
            return runtime.do("go", direction=direction)

        else:
            raise EvalError(f"Unknown action type: {name}")

    def _parse_kwargs(self, form: SList) -> dict[str, Any]:
        """Parse keyword arguments from a form."""
        kwargs = {}
        i = 1
        while i < len(form):
            item = form[i]
            if isinstance(item, Keyword):
                if i + 1 >= len(form):
                    raise EvalError(f"Missing value for :{item.name}")
                value = form[i + 1]
                # Resolve symbols to strings
                if isinstance(value, Symbol):
                    value = value.name
                kwargs[item.name] = value
                i += 2
            else:
                i += 1
        return kwargs

    def _check_expectations(
        self,
        runtime: GrueRuntime,
        result: ActionResult,
        predicates: list[SExpr]
    ) -> list[str]:
        """Check expectation predicates, return list of failures."""
        failures = []

        for pred in predicates:
            if not isinstance(pred, SList) or len(pred) == 0:
                failures.append(f"Invalid predicate: {pred}")
                continue

            head = pred[0]
            if not isinstance(head, Symbol):
                failures.append(f"Predicate must start with symbol: {pred}")
                continue

            name = head.name

            if name == "outcome?":
                if len(pred) != 2:
                    failures.append("(outcome? EXPECTED) requires 1 argument")
                    continue
                expected = pred[1]
                if isinstance(expected, Symbol):
                    expected = expected.name
                if result.outcome != expected:
                    failures.append(
                        f"Expected outcome '{expected}', got '{result.outcome}'"
                    )

            elif name == "reason?":
                if len(pred) != 2:
                    failures.append("(reason? EXPECTED) requires 1 argument")
                    continue
                expected = pred[1]
                if isinstance(expected, Symbol):
                    expected = expected.name
                if result.reason != expected:
                    failures.append(
                        f"Expected reason '{expected}', got '{result.reason}'"
                    )

            elif name == "context?":
                if len(pred) != 3:
                    failures.append("(context? KEY VALUE) requires 2 arguments")
                    continue
                key = pred[1]
                expected = pred[2]
                if isinstance(key, Symbol):
                    key = key.name
                if isinstance(expected, Symbol):
                    expected = expected.name

                context_dict = dict(result.context)
                if key not in context_dict:
                    failures.append(f"Context missing key '{key}'")
                elif context_dict[key] != expected:
                    failures.append(
                        f"Context['{key}'] expected '{expected}', got '{context_dict[key]}'"
                    )

            elif name == "player-at?":
                if len(pred) != 2:
                    failures.append("(player-at? ROOM) requires 1 argument")
                    continue
                expected = pred[1]
                if isinstance(expected, Symbol):
                    expected = expected.name
                actual = runtime.get_player_location()
                if actual != expected:
                    failures.append(
                        f"Expected player at '{expected}', got '{actual}'"
                    )

            elif name == "has-flag?":
                if len(pred) != 3:
                    failures.append("(has-flag? OBJ FLAG) requires 2 arguments")
                    continue
                obj = pred[1]
                flag = pred[2]
                if isinstance(obj, Symbol):
                    obj = obj.name
                if isinstance(flag, Symbol):
                    flag = flag.name
                if obj not in runtime.state.objects:
                    failures.append(f"Unknown object: {obj}")
                elif flag not in runtime.state.objects[obj].flags:
                    failures.append(f"Object '{obj}' missing flag '{flag}'")

            elif name == "no-flag?":
                if len(pred) != 3:
                    failures.append("(no-flag? OBJ FLAG) requires 2 arguments")
                    continue
                obj = pred[1]
                flag = pred[2]
                if isinstance(obj, Symbol):
                    obj = obj.name
                if isinstance(flag, Symbol):
                    flag = flag.name
                if obj not in runtime.state.objects:
                    failures.append(f"Unknown object: {obj}")
                elif flag in runtime.state.objects[obj].flags:
                    failures.append(f"Object '{obj}' has unexpected flag '{flag}'")

            elif name == "loc?":
                if len(pred) != 3:
                    failures.append("(loc? OBJ EXPECTED) requires 2 arguments")
                    continue
                obj = pred[1]
                expected = pred[2]
                if isinstance(obj, Symbol):
                    obj = obj.name
                if isinstance(expected, Symbol):
                    expected = expected.name
                if obj not in runtime.state.objects:
                    failures.append(f"Unknown object: {obj}")
                else:
                    actual = runtime.state.objects[obj].location
                    if actual != expected:
                        failures.append(
                            f"Object '{obj}' at '{actual}', expected '{expected}'"
                        )

            else:
                # Try evaluating as a general predicate
                try:
                    state_adapter = GrueStateAdapter(runtime.state)
                    evaluator = ExprEvaluator(state_adapter, self._functions)
                    if not evaluator.eval(pred):
                        failures.append(f"Predicate failed: {to_string(pred)}")
                except Exception as e:
                    failures.append(f"Error evaluating {to_string(pred)}: {e}")

        return failures

    def run_suite(self, test_source: str) -> list[TestResult]:
        """Run all tests from source string."""
        results = []
        forms = parse_all(test_source)

        for form in forms:
            if not isinstance(form, SList) or len(form) == 0:
                continue

            head = form[0]
            if not isinstance(head, Symbol):
                continue

            if head.name == "test":
                results.append(self.run_test(form))
            elif head.name == "test-sequence":
                results.append(self.run_test_sequence(form))
            elif head.name == "defn":
                # Global function definition for tests
                try:
                    executor = EffectExecutor(
                        _DummyState(),
                        self._functions
                    )
                    executor.execute(form)
                except Exception as e:
                    results.append(TestResult(
                        name=f"defn {to_string(form[1]) if len(form) > 1 else '?'}",
                        passed=False,
                        error=str(e)
                    ))

        return results


class _DummyState:
    """Minimal state for parsing defn forms."""
    def get_global(self, name: str) -> Any:
        raise KeyError(name)


def run_tests(
    world_path: str | Path,
    test_path: str | Path | None = None
) -> TestSuiteResult:
    """
    Run tests against a world.

    If test_path is None, looks for <world>.test.grue or tests/<world>.grue.
    """
    world_path = Path(world_path)
    world = load_grue(world_path)

    # Find test file
    if test_path is None:
        # Try <name>.test.grue
        test_path = world_path.with_suffix(".test.grue")
        if not test_path.exists():
            # Try tests/<name>.grue
            test_path = world_path.parent / "tests" / (world_path.stem + ".grue")
        if not test_path.exists():
            raise FileNotFoundError(
                f"No test file found for {world_path}. "
                f"Tried: {world_path.with_suffix('.test.grue')}, "
                f"{world_path.parent / 'tests' / (world_path.stem + '.grue')}"
            )
    else:
        test_path = Path(test_path)

    test_source = test_path.read_text()

    runner = TestRunner(world)
    results = runner.run_suite(test_source)

    return TestSuiteResult(
        world_path=str(world_path),
        test_path=str(test_path),
        results=results
    )


def run_tests_from_string(
    world: GrueWorld,
    test_source: str
) -> list[TestResult]:
    """Run tests from a string against a loaded world."""
    runner = TestRunner(world)
    return runner.run_suite(test_source)
