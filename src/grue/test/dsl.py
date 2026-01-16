"""
Grue-native test DSL.

Tests are S-expressions that exercise the full Grue stack.

== Test Forms ==

Simple single-action test (legacy style):
    (test "door opens"
      :setup ((move! @player @room))
      :action (do @door :open)
      :expect ((outcome? success)))

Sequential test (new style - use for multi-step tests and walkthroughs):
    (test "complete puzzle"
      :setup ((move! @player @room))    ; optional setup
      (do @door :unlock @key)           ; bare actions
      (do @door :open)
      (assert (has-flag? @door OPENBIT))
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
      :setup ((move! @player @room))
      (test "opens" :action (do @door :open) :expect ((outcome? success)))
      (test "closes" :action (do @door :close) :expect ((outcome? success))))

== Test Body Forms ==

    (do @obj :verb args...)   - Execute action
    (assert PRED)             - Check predicate, fail if false
    (until PRED BODY...)      - Loop until predicate true (max 100 iterations)
    (wait)                    - Process events (shorthand for process-events)
    (run ACTION-LIST)         - Execute a list of actions (symbol or quoted list)
    (seq ACTIONS...)          - Execute actions in sequence (legacy, optional)
    (step :action A :expect P) - Action with inline expectations (legacy)

== Predicates ==

    (outcome? success|blocked|error|redirect)
    (reason? REASON)
    (context? KEY VALUE)
    (player-at? ROOM)
    (loc? OBJ LOCATION)
    (has-flag? OBJ FLAG)
    (no-flag? OBJ FLAG)
    (held? OBJ)              - Object in player inventory
    (prop? OBJ PROP VALUE)
    (global? NAME VALUE)
    (queued? EVENT)
    (victory? true|false)
    (death? true|false)

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

    def run_test(self, test_form: SList) -> TestResult:
        """
        Run a (test ...) form.

        Supports two styles:
        1. Legacy single-action: (test NAME :setup S :action A :expect E)
        2. Sequential: (test NAME :setup S (do ...) (assert ...) ...)

        Detects style by presence of :action keyword.
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

        # Detect style: look for :action keyword
        has_action_keyword = any(
            isinstance(test_form[i], Keyword) and test_form[i].name == "action"
            for i in range(2, len(test_form))
        )

        if has_action_keyword:
            return self._run_test_legacy(test_form, test_name)
        else:
            return self._run_test_sequential(test_form, test_name)

    def _run_test_legacy(self, test_form: SList, test_name: str) -> TestResult:
        """Run legacy single-action test: (test NAME :setup S :action A :expect E)"""
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

        runtime = GrueRuntime(self.world)
        executor = EffectExecutor(runtime, self._functions)

        try:
            for effect in setup_effects:
                executor.execute(effect)

            result = self._execute_action(runtime, action)
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

    def _run_test_sequential(self, test_form: SList, test_name: str) -> TestResult:
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
        elif form_type == "seq":
            return self._run_seq(runtime, form, form_idx)
        elif form_type == "step":
            return self._run_step(runtime, executor, form, form_idx)
        elif form_type == "go":
            # Allow (go :direction X) as shorthand
            try:
                self._execute_action(runtime, form)
                return []
            except Exception as e:
                return [f"Form {form_idx}: {e}"]
        elif form_type == "process-events":
            try:
                self._execute_action(runtime, form)
                return []
            except Exception as e:
                return [f"Form {form_idx}: {e}"]
        else:
            return [f"Form {form_idx}: Unknown form type '{form_type}'"]

    def _run_do(
        self,
        runtime: GrueRuntime,
        form: SList,
        form_idx: int
    ) -> list[str]:
        """Run a bare (do ...) form."""
        try:
            self._execute_action(runtime, form)
            return []
        except Exception as e:
            return [f"Form {form_idx}: {e}"]

    def _run_wait(self, runtime: GrueRuntime, form_idx: int) -> list[str]:
        """Run a (wait) form - process events."""
        try:
            runtime.process_events()
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

    def run_test_sequence(self, seq_form: SList) -> TestResult:
        """
        Run a (test-sequence ...) form.

        Format:
            (test-sequence NAME
              :setup EFFECTS
              (step :action ACTION :expect PREDICATES)
              (seq ACTION ACTION ...)
              (assert PREDICATE)
              (until PREDICATE ACTION ACTION ...)
              ...)

        State persists across steps within the sequence.

        Forms:
            (step :action A :expect P) - Execute action, check expectations (expect optional)
            (seq A1 A2 ...) - Execute actions in sequence, no assertions
            (assert PRED) - Check predicate, fail if false
            (until PRED A1 A2 ...) - Loop actions until predicate is true (max 100 iterations)
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

        # Parse initial :setup and collect forms
        setup_effects: list[SExpr] = []
        forms: list[SList] = []

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
                if isinstance(head, Symbol) and head.name in ("step", "seq", "assert", "until"):
                    forms.append(item)
                i += 1
            else:
                i += 1

        if not forms:
            return TestResult(
                name=test_name,
                passed=False,
                error="Test-sequence has no forms"
            )

        # Create ONE runtime for the whole sequence - state persists!
        runtime = GrueRuntime(self.world)
        executor = EffectExecutor(runtime, self._functions)

        all_failures: list[str] = []

        try:
            # Run setup effects once
            for effect in setup_effects:
                executor.execute(effect)

            # Run each form in sequence
            for form_idx, form in enumerate(forms, 1):
                head = form[0]
                form_type = head.name if isinstance(head, Symbol) else ""

                if form_type == "step":
                    failures = self._run_step(runtime, executor, form, form_idx)
                    all_failures.extend(failures)

                elif form_type == "seq":
                    failures = self._run_seq(runtime, form, form_idx)
                    all_failures.extend(failures)

                elif form_type == "assert":
                    failures = self._run_assert(runtime, form, form_idx)
                    all_failures.extend(failures)

                elif form_type == "until":
                    failures = self._run_until(runtime, form, form_idx)
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

    def _run_step(
        self,
        runtime: GrueRuntime,
        executor: EffectExecutor,
        step: SList,
        step_idx: int
    ) -> list[str]:
        """Run a (step :action A :expect P) form."""
        failures: list[str] = []
        step_action = None
        step_expects: list[SExpr] = []
        step_setup: list[SExpr] = []

        # Parse step form: (step :setup S :action A :expect P)
        j = 1
        while j < len(step):
            item = step[j]
            if isinstance(item, Keyword):
                if j + 1 >= len(step):
                    failures.append(f"Step {step_idx}: Missing value for :{item.name}")
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
            failures.append(f"Step {step_idx}: Missing :action")
            return failures

        # Run per-step setup effects
        for effect in step_setup:
            executor.execute(effect)

        # Execute this step's action
        result = self._execute_action(runtime, step_action)

        # Check this step's expectations (optional - empty list is fine)
        step_failures = self._check_expectations(runtime, result, step_expects)

        for failure in step_failures:
            failures.append(f"Step {step_idx}: {failure}")

        return failures

    def _run_seq(
        self,
        runtime: GrueRuntime,
        seq: SList,
        seq_idx: int
    ) -> list[str]:
        """Run a (seq ACTION ACTION ...) form - execute actions in sequence."""
        failures: list[str] = []

        # All items after 'seq' are actions to execute
        for i, action in enumerate(list(seq.items)[1:], 1):
            if not isinstance(action, SList):
                failures.append(f"Seq {seq_idx}.{i}: Invalid action (not a list)")
                continue
            try:
                self._execute_action(runtime, action)
            except Exception as e:
                failures.append(f"Seq {seq_idx}.{i}: {e}")

        return failures

    def _run_assert(
        self,
        runtime: GrueRuntime,
        assert_form: SList,
        assert_idx: int
    ) -> list[str]:
        """Run an (assert PREDICATE) form - check predicate, fail if false."""
        failures: list[str] = []

        if len(assert_form) < 2:
            failures.append(f"Assert {assert_idx}: Missing predicate")
            return failures

        predicate = assert_form[1]

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
