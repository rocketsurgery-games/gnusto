"""
Grue Test Framework - Assert on game states, actions, and transitions.

This module provides tools for testing Grue game logic:

    from grue.test import GrueTestCase, load_test_world

    class TestOutsideDoor(GrueTestCase):
        @classmethod
        def world_path(cls):
            return "examples/outside-door.grue"

        def test_door_opens_from_push_bar_location(self):
            # Verify player starts at MASS-AVE
            self.assert_player_at("MASS-AVE")

            # Open the door
            result = self.do("open", "OUTSIDE-DOOR")

            # Verify outcome
            self.assert_success(result)
            self.assert_context(result, "mechanism", "push-bar")

        def test_door_blocked_from_great_court(self):
            # Move player to a non-push-bar location
            self.move_player("GREAT-COURT")

            # Try to open - should fail
            result = self.do("open", "OUTSIDE-DOOR")
            self.assert_blocked(result, "locked-from-outside")

Key features:
- State snapshots for before/after comparison
- Action execution with result inspection
- Rich assertions for outcomes, flags, locations, properties
- Direct state manipulation for test setup
- Integration with pytest

Usage:
    pytest tests/test_outside_door.py -v
"""

from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
from copy import deepcopy
import unittest

from ..parser import GrueWorld
from ..runtime import GrueRuntime, GameState, ObjectState, ActionResult
from .. import load_grue


@dataclass
class StateSnapshot:
    """Immutable snapshot of game state for comparison."""
    player_location: str
    objects: dict[str, tuple[str | None, frozenset[str], dict[str, Any]]]

    @classmethod
    def from_runtime(cls, runtime: GrueRuntime) -> "StateSnapshot":
        """Capture current state from runtime."""
        objects = {}
        for name, obj in runtime.state.objects.items():
            # Extract flags (boolean True properties) from properties
            flags = frozenset(k for k, v in obj.properties.items() if v is True)
            objects[name] = (
                obj.location,
                flags,
                dict(obj.properties),
            )
        return cls(
            player_location=runtime.get_player_location(),
            objects=objects,
        )

    def diff(self, other: "StateSnapshot") -> dict[str, Any]:
        """Return differences between this snapshot and another."""
        changes = {}

        if self.player_location != other.player_location:
            changes["player_location"] = {
                "from": self.player_location,
                "to": other.player_location,
            }

        # Check object changes
        obj_changes = {}
        all_objects = set(self.objects.keys()) | set(other.objects.keys())
        for name in all_objects:
            old = self.objects.get(name)
            new = other.objects.get(name)
            if old != new:
                obj_changes[name] = {"from": old, "to": new}
        if obj_changes:
            changes["objects"] = obj_changes

        return changes


@dataclass
class ActionTrace:
    """Record of an action execution."""
    verb: str
    direct_object: str | None
    kwargs: dict[str, Any]
    before: StateSnapshot
    after: StateSnapshot
    result: ActionResult

    @property
    def changes(self) -> dict[str, Any]:
        """State changes caused by this action."""
        return self.before.diff(self.after)


class GrueTestHarness:
    """
    Test harness for Grue game logic.

    Provides methods to:
    - Execute actions and capture results
    - Assert on outcomes, state, and transitions
    - Manipulate state directly for test setup
    """

    def __init__(self, world: GrueWorld):
        self.world = world
        self.runtime = GrueRuntime(world)
        self._traces: list[ActionTrace] = []

    @classmethod
    def load(cls, path: str | Path) -> "GrueTestHarness":
        """Load a world and create a test harness."""
        world = load_grue(path)
        return cls(world)

    def reset(self) -> None:
        """Reset to initial state."""
        self.runtime.reset()
        self._traces.clear()

    # === State Access ===

    def player_location(self) -> str:
        """Get player's current location."""
        return self.runtime.get_player_location()

    def object_location(self, obj: str) -> str | None:
        """Get an object's location."""
        if obj in self.runtime.state.objects:
            return self.runtime.state.objects[obj].location
        return None

    def has_flag(self, obj: str, flag: str) -> bool:
        """Check if object has flag (stored as boolean property)."""
        if obj in self.runtime.state.objects:
            return bool(self.runtime.state.objects[obj].properties.get(flag, False))
        return False

    def get_flags(self, obj: str) -> set[str]:
        """Get all flags (boolean True properties) on object."""
        if obj in self.runtime.state.objects:
            props = self.runtime.state.objects[obj].properties
            return {k for k, v in props.items() if v is True}
        return set()

    def get_property(self, obj: str, prop: str) -> Any:
        """Get property value."""
        if obj in self.runtime.state.objects:
            return self.runtime.state.objects[obj].properties.get(prop)
        return None

    def snapshot(self) -> StateSnapshot:
        """Capture current state."""
        return StateSnapshot.from_runtime(self.runtime)

    # === State Manipulation ===

    def move_player(self, location: str) -> None:
        """Move player to location (bypasses game logic)."""
        self.runtime.state.objects["PLAYER"].location = location

    def move_object(self, obj: str, location: str) -> None:
        """Move object to location (bypasses game logic)."""
        if obj in self.runtime.state.objects:
            self.runtime.state.objects[obj].location = location

    def set_flag(self, obj: str, flag: str) -> None:
        """Set flag on object (stored as boolean property)."""
        if obj in self.runtime.state.objects:
            self.runtime.state.objects[obj].properties[flag] = True

    def clear_flag(self, obj: str, flag: str) -> None:
        """Clear flag from object (stored as boolean property)."""
        if obj in self.runtime.state.objects:
            self.runtime.state.objects[obj].properties[flag] = False

    def set_property(self, obj: str, prop: str, value: Any) -> None:
        """Set property on object."""
        if obj in self.runtime.state.objects:
            self.runtime.state.objects[obj].properties[prop] = value

    # === Action Execution ===

    def do(
        self,
        target: str,
        verb: str,
        *args,
    ) -> ActionResult:
        """
        Execute an action and record the trace.

        Examples:
            harness.do("HACKER", "give", "FOOD")
            harness.do("DOOR", "unlock", "KEY")
            harness.do("LAMP", "examine")
        """
        before = self.snapshot()

        result = self.runtime.do(target, verb, *args)

        after = self.snapshot()

        trace = ActionTrace(
            verb=verb,
            direct_object=target,
            kwargs={"args": args},
            before=before,
            after=after,
            result=result,
        )
        self._traces.append(trace)

        return result

    def go(self, direction: str) -> ActionResult:
        """Shorthand for movement."""
        return self.runtime.do("_movement", "go", direction)

    @property
    def traces(self) -> list[ActionTrace]:
        """Get all recorded action traces."""
        return list(self._traces)

    @property
    def last_trace(self) -> ActionTrace | None:
        """Get the most recent action trace."""
        return self._traces[-1] if self._traces else None


class GrueTestCase(unittest.TestCase):
    """
    Base class for Grue game logic tests.

    Subclass and implement world_path() to specify the game to test.

    Example:
        class TestOutsideDoor(GrueTestCase):
            @classmethod
            def world_path(cls):
                return "examples/outside-door.grue"

            def test_door_opens(self):
                result = self.do("open", "OUTSIDE-DOOR")
                self.assert_success(result)
    """

    harness: GrueTestHarness

    @classmethod
    def world_path(cls) -> str | Path:
        """Override to specify the world file/directory to load."""
        raise NotImplementedError("Subclass must implement world_path()")

    @classmethod
    def setUpClass(cls) -> None:
        """Load the world once for all tests in this class."""
        cls._world = load_grue(cls.world_path())

    def setUp(self) -> None:
        """Reset harness before each test."""
        self.harness = GrueTestHarness(self._world)

    # === Convenience Methods (delegate to harness) ===

    def do(self, target: str, verb: str, *args) -> ActionResult:
        """Execute an action."""
        return self.harness.do(target, verb, *args)

    def go(self, direction: str) -> ActionResult:
        """Move in direction."""
        return self.harness.go(direction)

    def move_player(self, location: str) -> None:
        """Move player directly."""
        self.harness.move_player(location)

    def move_object(self, obj: str, location: str) -> None:
        """Move object directly."""
        self.harness.move_object(obj, location)

    def set_flag(self, obj: str, flag: str) -> None:
        """Set flag on object."""
        self.harness.set_flag(obj, flag)

    def clear_flag(self, obj: str, flag: str) -> None:
        """Clear flag from object."""
        self.harness.clear_flag(obj, flag)

    # === Assertions ===

    def assert_success(self, result: ActionResult, msg: str | None = None) -> None:
        """Assert action succeeded."""
        self.assertEqual(
            result.outcome, "success",
            msg or f"Expected success, got {result.outcome}: {result.reason or result.error}"
        )

    def assert_blocked(
        self,
        result: ActionResult,
        reason: str | None = None,
        msg: str | None = None
    ) -> None:
        """Assert action was blocked, optionally with specific reason."""
        self.assertEqual(
            result.outcome, "blocked",
            msg or f"Expected blocked, got {result.outcome}"
        )
        if reason is not None:
            self.assertEqual(
                result.reason, reason,
                msg or f"Expected reason '{reason}', got '{result.reason}'"
            )

    def assert_redirect(self, result: ActionResult, msg: str | None = None) -> None:
        """Assert action was redirected."""
        self.assertEqual(
            result.outcome, "redirect",
            msg or f"Expected redirect, got {result.outcome}"
        )

    def assert_error(self, result: ActionResult, msg: str | None = None) -> None:
        """Assert action errored."""
        self.assertEqual(
            result.outcome, "error",
            msg or f"Expected error, got {result.outcome}"
        )

    def assert_context(
        self,
        result: ActionResult,
        key: str,
        expected_value: Any,
        msg: str | None = None
    ) -> None:
        """Assert result context contains key with expected value."""
        context_dict = dict(result.context)
        self.assertIn(key, context_dict, msg or f"Context missing key '{key}'")
        self.assertEqual(
            context_dict[key], expected_value,
            msg or f"Context['{key}'] expected {expected_value!r}, got {context_dict[key]!r}"
        )

    def assert_context_has(self, result: ActionResult, key: str, msg: str | None = None) -> None:
        """Assert result context contains key (any value)."""
        context_dict = dict(result.context)
        self.assertIn(key, context_dict, msg or f"Context missing key '{key}'")

    def assert_player_at(self, location: str, msg: str | None = None) -> None:
        """Assert player is at location."""
        actual = self.harness.player_location()
        self.assertEqual(
            actual, location,
            msg or f"Expected player at {location}, got {actual}"
        )

    def assert_object_at(self, obj: str, location: str, msg: str | None = None) -> None:
        """Assert object is at location."""
        actual = self.harness.object_location(obj)
        self.assertEqual(
            actual, location,
            msg or f"Expected {obj} at {location}, got {actual}"
        )

    def assert_has_flag(self, obj: str, flag: str, msg: str | None = None) -> None:
        """Assert object has flag."""
        self.assertTrue(
            self.harness.has_flag(obj, flag),
            msg or f"Expected {obj} to have flag {flag}"
        )

    def assert_no_flag(self, obj: str, flag: str, msg: str | None = None) -> None:
        """Assert object does not have flag."""
        self.assertFalse(
            self.harness.has_flag(obj, flag),
            msg or f"Expected {obj} to NOT have flag {flag}"
        )

    def assert_property(
        self,
        obj: str,
        prop: str,
        expected: Any,
        msg: str | None = None
    ) -> None:
        """Assert object property has expected value."""
        actual = self.harness.get_property(obj, prop)
        self.assertEqual(
            actual, expected,
            msg or f"Expected {obj}.{prop} = {expected!r}, got {actual!r}"
        )

    def assert_state_unchanged(self, msg: str | None = None) -> None:
        """Assert the last action didn't change state (ignores moves increment on player)."""
        trace = self.harness.last_trace
        self.assertIsNotNone(trace, "No action has been executed")
        changes = dict(trace.changes)  # Make a copy to modify
        # Ignore 'moves' increment on player object as that's expected
        player_name = self.harness.runtime.player_name
        if "objects" in changes and player_name in changes["objects"]:
            player_change = changes["objects"][player_name]
            if player_change:
                # Check if only moves changed
                old_props = player_change["from"][2] if player_change["from"] else {}
                new_props = player_change["to"][2] if player_change["to"] else {}
                old_moves = old_props.get("moves", 0)
                new_moves = new_props.get("moves", 0)
                # If only moves changed, remove player from object changes
                old_no_moves = {k: v for k, v in old_props.items() if k != "moves"}
                new_no_moves = {k: v for k, v in new_props.items() if k != "moves"}
                if old_no_moves == new_no_moves and old_moves != new_moves:
                    changes["objects"] = dict(changes["objects"])  # Copy
                    del changes["objects"][player_name]
                    if not changes["objects"]:
                        del changes["objects"]
        self.assertEqual(changes, {}, msg or f"Expected no state change, got: {changes}")

    def assert_effect_applied(
        self,
        result: ActionResult,
        effect_substring: str,
        msg: str | None = None
    ) -> None:
        """Assert an effect description contains the substring."""
        for effect in result.effects_applied:
            if effect_substring in effect:
                return
        self.fail(
            msg or f"No effect containing '{effect_substring}' in {result.effects_applied}"
        )


# === Pytest fixtures (if pytest is available) ===

def pytest_harness(world_path: str | Path):
    """
    Pytest fixture factory for Grue test harnesses.

    Usage in conftest.py:
        import pytest
        from grue.test import pytest_harness

        @pytest.fixture
        def outside_door():
            return pytest_harness("examples/outside-door.grue")

    Usage in tests:
        def test_door_opens(outside_door):
            result = outside_door.do("open", "OUTSIDE-DOOR")
            assert result.outcome == "success"
    """
    return GrueTestHarness.load(world_path)
