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
from .runtime import GrueRuntime, ActionResult
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
        # Share function definitions - runtime implements MutableWorldState
        executor = EffectExecutor(runtime, self._functions)

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
        executor = EffectExecutor(runtime, self._functions)

        all_failures: list[str] = []

        try:
            # Run setup effects once
            for effect in setup_effects:
                executor.execute(effect)

            # Run each step in sequence
            for step_idx, step in enumerate(steps, 1):
                step_action = None
                step_expects: list[SExpr] = []
                step_setup: list[SExpr] = []

                # Parse step form: (step :setup S :action A :expect P)
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
                        elif item.name == "setup":
                            if isinstance(value, SList):
                                step_setup = list(value.items)
                        j += 2
                    else:
                        j += 1

                if step_action is None:
                    all_failures.append(f"Step {step_idx}: Missing :action")
                    continue

                # Run per-step setup effects
                for effect in step_setup:
                    executor.execute(effect)

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
            # Parse (do TARGET :verb arg1 arg2 ...)
            # Format: (do @hacker :give @food) -> runtime.do("HACKER", "give", "FOOD")
            items = list(action.items)[1:]  # Skip 'do'

            if len(items) < 2:
                raise EvalError("(do TARGET :verb ...) requires target and verb")

            # First item is target
            target = items[0]
            if isinstance(target, Symbol):
                target = target.name
            else:
                raise EvalError(f"Target must be a symbol: {target}")

            # Second item is verb (keyword)
            verb_item = items[1]
            if isinstance(verb_item, Keyword):
                verb = verb_item.name
            else:
                raise EvalError(f"Verb must be a keyword: {verb_item}")

            # Remaining items are positional args
            args = []
            for item in items[2:]:
                if isinstance(item, Symbol):
                    args.append(item.name)
                else:
                    args.append(item)

            return runtime.do(target, verb, *args)

        elif name == "go":
            # Parse (go :direction D)
            kwargs = self._parse_kwargs(action)
            direction = kwargs.get("direction")
            if direction is None:
                raise EvalError("(go ...) requires :direction")
            return runtime.do("_movement", "go", direction)

        elif name == "process-events":
            # Process all queued events for this turn
            # Returns the first event result (if any) for testing
            results = runtime.process_events()
            if results:
                return results[0]
            # Return a no-op success if no events fired
            return ActionResult(outcome="success", context=[("events-processed", 0)])

        elif name == "wait":
            # Shorthand for doing nothing + processing events
            results = runtime.process_events()
            if results:
                return results[0]
            return ActionResult(outcome="success", context=[("waited", True)])

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
                # Handle boolean literals
                if isinstance(expected, Symbol):
                    if expected.name.lower() == "true":
                        expected = True
                    elif expected.name.lower() == "false":
                        expected = False
                    else:
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
                # Handle nil as Python None
                if expected == "nil":
                    expected = None
                if obj not in runtime.state.objects:
                    failures.append(f"Unknown object: {obj}")
                else:
                    actual = runtime.state.objects[obj].location
                    if actual != expected:
                        failures.append(
                            f"Object '{obj}' at '{actual}', expected '{expected}'"
                        )

            elif name == "global?":
                if len(pred) != 3:
                    failures.append("(global? NAME EXPECTED) requires 2 arguments")
                    continue
                gname = pred[1]
                expected = pred[2]
                if isinstance(gname, Symbol):
                    gname = gname.name
                if isinstance(expected, Symbol):
                    expected = expected.name
                actual = runtime.state.globals.get(gname)
                if actual != expected:
                    failures.append(
                        f"Global '{gname}' is '{actual}', expected '{expected}'"
                    )

            elif name == "prop?":
                if len(pred) != 4:
                    failures.append("(prop? OBJ PROP EXPECTED) requires 3 arguments")
                    continue
                obj = pred[1]
                prop = pred[2]
                expected = pred[3]
                if isinstance(obj, Symbol):
                    obj = obj.name
                if isinstance(prop, Symbol):
                    prop = prop.name
                if isinstance(expected, Symbol):
                    expected = expected.name
                if obj not in runtime.state.objects:
                    failures.append(f"Unknown object: {obj}")
                else:
                    actual = runtime.state.objects[obj].properties.get(prop)
                    if actual != expected:
                        failures.append(
                            f"Property '{obj}.{prop}' is '{actual}', expected '{expected}'"
                        )

            elif name == "queued?":
                if len(pred) != 2:
                    failures.append("(queued? EVENT) requires 1 argument")
                    continue
                event = pred[1]
                if isinstance(event, Symbol):
                    event = event.name
                if not runtime.is_queued(event):
                    failures.append(f"Event '{event}' is not queued")

            elif name == "not-queued?":
                if len(pred) != 2:
                    failures.append("(not-queued? EVENT) requires 1 argument")
                    continue
                event = pred[1]
                if isinstance(event, Symbol):
                    event = event.name
                if runtime.is_queued(event):
                    failures.append(f"Event '{event}' should not be queued")

            elif name == "not-flag?":
                # Alias for no-flag? - check object does NOT have a flag
                if len(pred) != 3:
                    failures.append("(not-flag? OBJ FLAG) requires 2 arguments")
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

            elif name == "death?":
                # Check if result context contains (death true)
                if len(pred) != 2:
                    failures.append("(death? EXPECTED) requires 1 argument")
                    continue
                expected = pred[1]
                if isinstance(expected, Symbol):
                    expected = expected.name.lower() == "true"
                # Look for death in context
                death_value = None
                for key, val in result.context:
                    if key == "death":
                        # Normalize to bool - context may have string "True" or bool True
                        if isinstance(val, str):
                            death_value = val.lower() == "true"
                        else:
                            death_value = bool(val)
                        break
                if death_value != expected:
                    failures.append(
                        f"Expected death={expected}, got death={death_value}"
                    )

            elif name == "victory?":
                # Check if result context contains (victory true)
                if len(pred) != 2:
                    failures.append("(victory? EXPECTED) requires 1 argument")
                    continue
                expected = pred[1]
                if isinstance(expected, Symbol):
                    expected = expected.name.lower() == "true"
                # Look for victory in context
                victory_value = None
                for key, val in result.context:
                    if key == "victory":
                        # Normalize to bool - context may have string "True" or bool True
                        if isinstance(val, str):
                            victory_value = val.lower() == "true"
                        else:
                            victory_value = bool(val)
                        break
                if victory_value != expected:
                    failures.append(
                        f"Expected victory={expected}, got victory={victory_value}"
                    )

            else:
                # Try evaluating as a general predicate
                try:
                    evaluator = ExprEvaluator(runtime, self._functions)
                    if not evaluator.eval(pred):
                        failures.append(f"Predicate failed: {to_string(pred)}")
                except Exception as e:
                    failures.append(f"Error evaluating {to_string(pred)}: {e}")

        return failures

    def run_test_group(self, group_form: SList) -> list[TestResult]:
        """
        Run a (test-group ...) form.

        Format:
            (test-group NAME
              :setup EFFECTS
              (test ...)
              (test ...)
              ...)

        Group :setup runs before each test. Test-level :setup is additive.
        Each test still gets a fresh world state.
        """
        if len(group_form) < 2:
            return [TestResult(
                name="<invalid group>",
                passed=False,
                error="Test-group form too short"
            )]

        name = group_form[1]
        if isinstance(name, str):
            group_name = name
        elif isinstance(name, Symbol):
            group_name = name.name
        else:
            group_name = to_string(name)

        # Parse group :setup and collect nested tests
        group_setup: list[SExpr] = []
        nested_tests: list[SList] = []

        i = 2
        while i < len(group_form):
            item = group_form[i]

            if isinstance(item, Keyword):
                if i + 1 >= len(group_form):
                    return [TestResult(
                        name=group_name,
                        passed=False,
                        error=f"Missing value for :{item.name}"
                    )]
                value = group_form[i + 1]

                if item.name == "setup":
                    if isinstance(value, SList):
                        group_setup = list(value.items)
                i += 2

            elif isinstance(item, SList) and len(item) > 0:
                head = item[0]
                if isinstance(head, Symbol) and head.name == "test":
                    nested_tests.append(item)
                i += 1
            else:
                i += 1

        # Run each nested test with group setup prepended
        results = []
        for test_form in nested_tests:
            # Extract test's own setup
            test_setup: list[SExpr] = []
            test_name = ""
            test_action = None
            test_expect: list[SExpr] = []

            if len(test_form) >= 2:
                tn = test_form[1]
                if isinstance(tn, str):
                    test_name = tn
                elif isinstance(tn, Symbol):
                    test_name = tn.name
                else:
                    test_name = to_string(tn)

            j = 2
            while j < len(test_form):
                item = test_form[j]
                if isinstance(item, Keyword):
                    if j + 1 >= len(test_form):
                        break
                    value = test_form[j + 1]

                    if item.name == "setup":
                        if isinstance(value, SList):
                            test_setup = list(value.items)
                    elif item.name == "action":
                        test_action = value
                    elif item.name == "expect":
                        if isinstance(value, SList):
                            test_expect = list(value.items)
                    j += 2
                else:
                    j += 1

            # Build combined test with group setup + test setup
            full_name = f"{group_name} / {test_name}"
            combined_setup = group_setup + test_setup

            if test_action is None:
                results.append(TestResult(
                    name=full_name,
                    passed=False,
                    error="Test missing :action"
                ))
                continue

            # Create fresh runtime for this test
            runtime = GrueRuntime(self.world)
            executor = EffectExecutor(runtime, self._functions)

            try:
                # Run combined setup effects
                for effect in combined_setup:
                    executor.execute(effect)

                # Execute action
                result = self._execute_action(runtime, test_action)

                # Check expectations
                failures = self._check_expectations(runtime, result, test_expect)

                results.append(TestResult(
                    name=full_name,
                    passed=len(failures) == 0,
                    failures=failures
                ))

            except Exception as e:
                results.append(TestResult(
                    name=full_name,
                    passed=False,
                    error=str(e)
                ))

        return results

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
            elif head.name == "test-group":
                results.extend(self.run_test_group(form))
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
