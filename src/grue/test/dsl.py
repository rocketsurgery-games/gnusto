"""
Grue-native test DSL.

Tests are S-expressions that exercise the full Grue stack.

== Test Forms ==

Sequential test (standard style):
    (test "complete puzzle"
      :setup ((move @player @room))      ; optional setup
      (do @door :unlock @key)           ; actions
      (do @door :open)
      (assert (has-flag? @door open))
      (until (loc? @player @goal)       ; loop until condition
        (do @movement :go north))
      (run walkthrough/segment)         ; run named action list
      (assert (victory? true)))

Action lists for walkthroughs:
    (def walkthrough/kitchen
      '((do @movement :go south)
        (do @refrigerator :open)
        (do @carton :take)))

Test groups with shared setup:
    (test-group "door tests"
      :setup ((move @player @room))

      (test "opens"
        (do @door :open)
        (assert (outcome? success)))

      (test "closes"
        (do @door :close)
        (assert (outcome? success))))

== Test Body Forms ==

    (do @obj :verb args...)   - Execute action
    (assert PRED)             - Check predicate, fail if false
    (until PRED BODY...)      - Loop until predicate true (max 100 iterations)
    (wait)                    - Pass time and process queued events
    (run ACTION-LIST)         - Execute a list of actions (symbol or quoted list)
    (go :direction DIR)       - Shorthand for movement

== Predicates ==

Result predicates (check last action result):
    (outcome? success|blocked|error|redirect)
    (context? KEY VALUE)
    (victory? true|false)
    (death? true|false)

State predicates (check game state):
    (player-at? ROOM)
    (loc? OBJ LOCATION)
    (has-flag? OBJ PROP)     - Object has truthy property (use lowercase: open, locked)
    (no-flag? OBJ PROP)      - Object property is falsy (use lowercase: open, locked)
    (held? OBJ)              - Object in player inventory
    (in? OBJ CONTAINER)      - Object inside container
    (prop? OBJ PROP VALUE)   - Object property equals value
    (queued? EVENT)
    (not-queued? EVENT)

Usage:
    from grue.test import run_tests
    results = run_tests("path/to/world.grue", "path/to/tests.grue")
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..sexpr import SExpr, Symbol, Keyword, SList, parse, parse_all, to_string
from ..parser import load_grue, GrueWorld
from ..runtime import GrueRuntime, ActionResult
from ..expr import ExprEvaluator, EffectExecutor, EvalError


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
        # Global definitions (def name value) for action lists etc.
        self._globals: dict[str, SExpr] = {}
        # Last action result (for result predicates in assert)
        self._last_result: ActionResult | None = None

    def run_test(self, test_form: SList) -> TestResult:
        """
        Run a (test ...) form.

        Format:
            (test NAME
              :setup ((effects))
              (do @obj :verb args)
              (assert (predicate))
              ...)

        The test body is a sequence of forms: (do ...), (assert ...), (go ...),
        (wait), (until ...), (run ...).
        """
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

        return self._run_test_impl(test_form, test_name)

    def _run_test_impl(self, test_form: SList, test_name: str) -> TestResult:
        """Run sequential test: (test NAME :setup S (do ...) (assert ...) ...)"""
        setup_effects: list[SExpr] = []
        forms: list[SExpr] = []

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
                i += 2

            elif isinstance(item, SList) and len(item) > 0:
                # Collect form bodies: do, assert, until, wait, run, seq, step
                forms.append(item)
                i += 1
            else:
                i += 1

        if not forms:
            return TestResult(
                name=test_name,
                passed=False,
                error="Test has no body forms"
            )

        runtime = GrueRuntime(self.world)
        executor = EffectExecutor(runtime, self._functions)
        all_failures: list[str] = []
        self._last_result = None  # Reset for this test

        try:
            for effect in setup_effects:
                executor.execute(effect)

            for form_idx, form in enumerate(forms, 1):
                failures = self._run_form(runtime, executor, form, form_idx)
                all_failures.extend(failures)

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

    def _run_form(
        self,
        runtime: GrueRuntime,
        executor: EffectExecutor,
        form: SExpr,
        form_idx: int
    ) -> list[str]:
        """Run a single form in a sequential test body."""
        if not isinstance(form, SList) or len(form) == 0:
            return [f"Form {form_idx}: Invalid form"]

        head = form[0]
        if not isinstance(head, Symbol):
            return [f"Form {form_idx}: Form must start with symbol"]

        form_type = head.name

        if form_type == "do":
            return self._run_do(runtime, form, form_idx)
        elif form_type == "assert":
            return self._run_assert(runtime, form, form_idx)
        elif form_type == "until":
            return self._run_until(runtime, form, form_idx)
        elif form_type == "wait":
            return self._run_wait(runtime, form_idx)
        elif form_type == "run":
            return self._run_run(runtime, form, form_idx)
        elif form_type == "go":
            # Allow (go :direction X) as shorthand
            try:
                self._last_result = self._execute_action(runtime, form)
                return []
            except Exception as e:
                return [f"Form {form_idx}: {e}"]
        elif form_type in ("move", "set", "inc", "queue", "dequeue", "take"):
            # Setup operations - execute directly as effects
            try:
                from ..runtime import EffectExecutor
                executor = EffectExecutor(runtime)
                executor.execute(form)
                return []
            except Exception as e:
                return [f"Form {form_idx}: Setup error - {e}"]
        else:
            return [f"Form {form_idx}: Unknown form type '{form_type}'"]

    def _run_do(
        self,
        runtime: GrueRuntime,
        form: SList,
        form_idx: int
    ) -> list[str]:
        """Run a bare (do ...) form. Stores result for subsequent assertions."""
        try:
            self._last_result = self._execute_action(runtime, form)
            return []
        except Exception as e:
            return [f"Form {form_idx}: {e}"]

    def _run_wait(self, runtime: GrueRuntime, form_idx: int) -> list[str]:
        """Run a (wait) form - process events. Stores first event result."""
        try:
            results = runtime.process_events()
            if results:
                self._last_result = results[0]
            return []
        except Exception as e:
            return [f"Form {form_idx}: {e}"]

    def _run_run(
        self,
        runtime: GrueRuntime,
        form: SList,
        form_idx: int
    ) -> list[str]:
        """Run a (run ACTION-LIST) form - execute a list of actions."""
        failures: list[str] = []

        if len(form) < 2:
            return [f"Run {form_idx}: Missing action list"]

        action_list_expr = form[1]

        # Resolve the action list
        action_list: list[SExpr] = []

        if isinstance(action_list_expr, Symbol):
            # Look up in functions/globals
            sym_name = action_list_expr.name
            if sym_name in self._globals:
                action_list_expr = self._globals[sym_name]
            else:
                return [f"Run {form_idx}: Unknown symbol '{sym_name}'"]

        if isinstance(action_list_expr, SList):
            # Check if it's a quoted list: (quote (...))
            if (len(action_list_expr) == 2 and
                isinstance(action_list_expr[0], Symbol) and
                action_list_expr[0].name == "quote"):
                inner = action_list_expr[1]
                if isinstance(inner, SList):
                    action_list = list(inner.items)
                else:
                    return [f"Run {form_idx}: Quoted value must be a list"]
            else:
                # Assume it's already a list of actions
                action_list = list(action_list_expr.items)

        if not action_list:
            return [f"Run {form_idx}: Empty action list"]

        # Execute each action in the list
        for i, action in enumerate(action_list, 1):
            if not isinstance(action, SList):
                failures.append(f"Run {form_idx}.{i}: Invalid action (not a list)")
                continue
            try:
                self._execute_action(runtime, action)
            except Exception as e:
                failures.append(f"Run {form_idx}.{i}: {e}")

        return failures

    # Predicates with explicit handlers in _check_expectations.
    # Other predicates (held?, in?, visible?, etc.) work via ExprEvaluator fallback.
    _EXPECTATION_PREDICATES = {
        # Result predicates (require _last_result)
        "outcome?", "context?", "death?", "victory?",
        # State predicates (with explicit handlers for better error messages)
        "player-at?", "has-flag?", "no-flag?", "not-flag?", "loc?",
        "prop?", "queued?", "not-queued?",
    }

    # Result predicates require a last action result to check
    _RESULT_PREDICATES = {"outcome?", "context?", "death?", "victory?"}

    def _run_assert(
        self,
        runtime: GrueRuntime,
        assert_form: SList,
        assert_idx: int
    ) -> list[str]:
        """Run an (assert PREDICATE) form - check predicate, fail if false.

        For expectation predicates (outcome?, player-at?, has-flag?, etc.),
        delegates to _check_expectations. For other predicates, evaluates
        against world state using ExprEvaluator.
        """
        failures: list[str] = []

        if len(assert_form) < 2:
            failures.append(f"Assert {assert_idx}: Missing predicate")
            return failures

        predicate = assert_form[1]

        # Check if this is an expectation predicate (handled by _check_expectations)
        if (isinstance(predicate, SList) and len(predicate) > 0 and
            isinstance(predicate[0], Symbol) and
            predicate[0].name in self._EXPECTATION_PREDICATES):

            pred_name = predicate[0].name

            # Result predicates require a last action result
            if pred_name in self._RESULT_PREDICATES and self._last_result is None:
                failures.append(
                    f"Assert {assert_idx}: {to_string(predicate)} - no action result to check"
                )
            else:
                # Use a dummy result for state predicates if no action was taken
                result_to_check = self._last_result or ActionResult(outcome="success")

                # Reuse _check_expectations for all expectation predicates
                check_failures = self._check_expectations(
                    runtime, result_to_check, [predicate]
                )
                for f in check_failures:
                    failures.append(f"Assert {assert_idx}: {f}")
        else:
            # Regular predicate - evaluate against world state
            try:
                evaluator = ExprEvaluator(runtime, self._functions)
                result = evaluator.eval(predicate)
                if not result:
                    failures.append(f"Assert {assert_idx}: {to_string(predicate)} is false")
            except Exception as e:
                failures.append(f"Assert {assert_idx}: Error evaluating {to_string(predicate)}: {e}")

        return failures

    def _run_until(
        self,
        runtime: GrueRuntime,
        until_form: SList,
        until_idx: int,
        max_iterations: int = 100
    ) -> list[str]:
        """Run an (until PREDICATE ACTION...) form - loop until predicate is true."""
        failures: list[str] = []

        if len(until_form) < 3:
            failures.append(f"Until {until_idx}: Requires predicate and at least one action")
            return failures

        predicate = until_form[1]
        actions = list(until_form.items)[2:]

        evaluator = ExprEvaluator(runtime, self._functions)

        for iteration in range(max_iterations):
            # Check if condition is met
            try:
                if evaluator.eval(predicate):
                    return failures  # Success - condition met
            except Exception as e:
                failures.append(f"Until {until_idx}: Error evaluating predicate: {e}")
                return failures

            # Execute all actions in the loop body
            for i, action in enumerate(actions, 1):
                if not isinstance(action, SList):
                    failures.append(f"Until {until_idx}.{i}: Invalid action")
                    continue
                try:
                    self._execute_action(runtime, action)
                except Exception as e:
                    failures.append(f"Until {until_idx}.{i}: {e}")
                    return failures  # Stop on error

        # Max iterations reached
        failures.append(
            f"Until {until_idx}: Max iterations ({max_iterations}) reached, "
            f"condition {to_string(predicate)} never became true"
        )
        return failures

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

        elif name == "wait":
            # Pass time and process queued events
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
                # Normalize flag name to lowercase (properties are lowercase)
                flag = flag.lower()
                if obj not in runtime.state.objects:
                    failures.append(f"Unknown object: {obj}")
                elif not runtime.state.objects[obj].properties.get(flag):
                    failures.append(f"Object '{obj}' missing property '{flag}'")

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
                # Normalize flag name to lowercase (properties are lowercase)
                flag = flag.lower()
                if obj not in runtime.state.objects:
                    failures.append(f"Unknown object: {obj}")
                elif runtime.state.objects[obj].properties.get(flag):
                    failures.append(f"Object '{obj}' has unexpected property '{flag}'")

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
                # Alias for no-flag? - check object does NOT have a property
                if len(pred) != 3:
                    failures.append("(not-flag? OBJ FLAG) requires 2 arguments")
                    continue
                obj = pred[1]
                flag = pred[2]
                if isinstance(obj, Symbol):
                    obj = obj.name
                if isinstance(flag, Symbol):
                    flag = flag.name
                # Normalize flag name to lowercase (properties are lowercase)
                flag = flag.lower()
                if obj not in runtime.state.objects:
                    failures.append(f"Unknown object: {obj}")
                elif runtime.state.objects[obj].properties.get(flag):
                    failures.append(f"Object '{obj}' has unexpected property '{flag}'")

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

        Supports both legacy (:action/:expect) and sequential styles for nested tests.
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
            # Extract test name
            test_name = ""
            if len(test_form) >= 2:
                tn = test_form[1]
                if isinstance(tn, str):
                    test_name = tn
                elif isinstance(tn, Symbol):
                    test_name = tn.name
                else:
                    test_name = to_string(tn)

            full_name = f"{group_name} / {test_name}"

            # Build a new test form with combined setup
            # Find test's existing setup and merge with group setup
            new_items: list[SExpr] = [Symbol("test"), test_form[1]]

            # Extract test's own setup
            test_setup: list[SExpr] = []
            other_items: list[SExpr] = []

            j = 2
            while j < len(test_form):
                item = test_form[j]
                if isinstance(item, Keyword) and item.name == "setup" and j + 1 < len(test_form):
                    value = test_form[j + 1]
                    if isinstance(value, SList):
                        test_setup = list(value.items)
                    j += 2
                else:
                    other_items.append(item)
                    j += 1

            # Add combined setup
            combined_setup = group_setup + test_setup
            if combined_setup:
                new_items.append(Keyword("setup"))
                new_items.append(SList(combined_setup))

            # Add remaining items (action/expect or body forms)
            new_items.extend(other_items)

            # Create new test form and run it
            merged_test = SList(new_items)
            result = self.run_test(merged_test)

            # Update the name to include group prefix
            result.name = full_name
            results.append(result)

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
            elif head.name == "def":
                # Global constant definition: (def NAME VALUE)
                if len(form) >= 3:
                    def_name = form[1]
                    def_value = form[2]
                    if isinstance(def_name, Symbol):
                        self._globals[def_name.name] = def_value
                    else:
                        results.append(TestResult(
                            name=f"def {to_string(def_name)}",
                            passed=False,
                            error="def name must be a symbol"
                        ))

        return results


class _DummyState:
    """Minimal state for parsing defn forms."""
    pass


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
