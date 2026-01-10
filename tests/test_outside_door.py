"""
Tests for the outside-door example.

These tests validate the complex door behavior:
- Opens from push-bar locations (MASS-AVE, SMITH-ST, etc.)
- Blocked from other outside locations
- Opens from inside but auto-closes
- Electronic lock rejects physical keys
"""

from grue.testing import GrueTestCase


class TestOutsideDoorOpen(GrueTestCase):
    """Test OUTSIDE-DOOR open behavior."""

    @classmethod
    def world_path(cls):
        return "examples/outside-door.grue"

    def test_door_opens_from_mass_ave(self):
        """Door opens via push-bar from MASS-AVE."""
        self.assert_player_at("MASS-AVE")

        result = self.do("open", "OUTSIDE-DOOR")

        self.assert_success(result)
        self.assert_context(result, "mechanism", "push-bar")

    def test_door_opens_from_smith_st(self):
        """Door opens via push-bar from SMITH-ST."""
        self.move_player("SMITH-ST")

        result = self.do("open", "OUTSIDE-DOOR")

        self.assert_success(result)
        self.assert_context(result, "mechanism", "push-bar")

    def test_door_opens_from_courtyard(self):
        """Door opens via push-bar from COURTYARD."""
        self.move_player("COURTYARD")

        result = self.do("open", "OUTSIDE-DOOR")

        self.assert_success(result)
        self.assert_context(result, "mechanism", "push-bar")

    def test_door_opens_from_cs_roof(self):
        """Door opens via push-bar from CS-ROOF."""
        self.move_player("CS-ROOF")

        result = self.do("open", "OUTSIDE-DOOR")

        self.assert_success(result)
        self.assert_context(result, "mechanism", "push-bar")

    def test_door_blocked_from_great_court(self):
        """Door is locked from GREAT-COURT (no push-bar)."""
        self.move_player("GREAT-COURT")

        result = self.do("open", "OUTSIDE-DOOR")

        self.assert_blocked(result, "locked-from-outside")

    def test_door_opens_from_lobby(self):
        """Door opens from inside with auto-close note."""
        self.move_player("LOBBY")

        result = self.do("open", "OUTSIDE-DOOR")

        self.assert_success(result)
        self.assert_context(result, "note", "auto-closing")


class TestOutsideDoorUnlock(GrueTestCase):
    """Test OUTSIDE-DOOR unlock behavior."""

    @classmethod
    def world_path(cls):
        return "examples/outside-door.grue"

    def test_master_key_rejected_outside(self):
        """Physical key rejected by electronic lock from outside."""
        # Player starts at MASS-AVE with MASTER-KEY
        self.assert_player_at("MASS-AVE")
        self.assert_object_at("MASTER-KEY", "PLAYER")

        result = self.do("unlock", "OUTSIDE-DOOR", with_obj="MASTER-KEY")

        self.assert_blocked(result, "wrong-key-type")
        self.assert_context(result, "detail", "electronic-lock")
        self.assert_context(result, "expected", "card-key")

    def test_unlock_blocked_from_great_court(self):
        """No unlock mechanism from GREAT-COURT."""
        self.move_player("GREAT-COURT")

        result = self.do("unlock", "OUTSIDE-DOOR", with_obj="MASTER-KEY")

        self.assert_blocked(result, "locked-from-outside")

    def test_master_key_works_inside(self):
        """Physical key works from inside."""
        self.move_player("LOBBY")
        self.assert_has_flag("OUTSIDE-DOOR", "LOCKED")

        result = self.do("unlock", "OUTSIDE-DOOR", with_obj="MASTER-KEY")

        self.assert_success(result)
        self.assert_no_flag("OUTSIDE-DOOR", "LOCKED")

    def test_unlock_needs_key_inside(self):
        """Need a key to unlock from inside."""
        self.move_player("LOBBY")
        # Remove key from player
        self.move_object("MASTER-KEY", "MASS-AVE")

        result = self.do("unlock", "OUTSIDE-DOOR")

        # No ?with provided, so behavior evaluates with ?with = None
        # Should hit the "need-key" case
        self.assert_blocked(result, "need-key")

    def test_unlock_already_unlocked(self):
        """Can't unlock an unlocked door."""
        self.move_player("LOBBY")
        self.clear_flag("OUTSIDE-DOOR", "LOCKED")

        result = self.do("unlock", "OUTSIDE-DOOR", with_obj="MASTER-KEY")

        self.assert_blocked(result, "not-locked")


class TestOutsideDoorClose(GrueTestCase):
    """Test OUTSIDE-DOOR close behavior."""

    @classmethod
    def world_path(cls):
        return "examples/outside-door.grue"

    def test_close_always_succeeds(self):
        """Spring-loaded door always closes."""
        result = self.do("close", "OUTSIDE-DOOR")

        self.assert_success(result)
        self.assert_context(result, "note", "spring-loaded")


class TestOutsideDoorThrough(GrueTestCase):
    """Test OUTSIDE-DOOR through behavior (traversal)."""

    @classmethod
    def world_path(cls):
        return "examples/outside-door.grue"

    def test_go_in_from_outside(self):
        """Going 'in' from outside uses the door."""
        self.assert_player_at("MASS-AVE")

        result = self.go("in")

        self.assert_success(result)
        self.assert_player_at("LOBBY")

    def test_go_out_from_inside(self):
        """Going 'out' from inside uses the door."""
        self.move_player("LOBBY")

        result = self.go("out")

        self.assert_success(result)
        self.assert_player_at("MASS-AVE")

    def test_east_west_movement(self):
        """East/west movement doesn't use door."""
        self.assert_player_at("MASS-AVE")

        result = self.go("east")

        self.assert_success(result)
        self.assert_player_at("SMITH-ST")


class TestStateTracking(GrueTestCase):
    """Test state tracking and traces."""

    @classmethod
    def world_path(cls):
        return "examples/outside-door.grue"

    def test_unlock_changes_flag(self):
        """Verify unlock actually clears LOCKED flag."""
        self.move_player("LOBBY")

        before = self.harness.snapshot()
        self.assert_has_flag("OUTSIDE-DOOR", "LOCKED")

        self.do("unlock", "OUTSIDE-DOOR", with_obj="MASTER-KEY")

        after = self.harness.snapshot()
        self.assert_no_flag("OUTSIDE-DOOR", "LOCKED")

        # Verify trace recorded the change
        trace = self.harness.last_trace
        changes = trace.changes
        self.assertIn("objects", changes)
        self.assertIn("OUTSIDE-DOOR", changes["objects"])

    def test_open_no_state_change(self):
        """Opening push-bar door doesn't change door state."""
        result = self.do("open", "OUTSIDE-DOOR")

        self.assert_success(result)
        # Door state shouldn't change (no effects in this case)
        self.assert_state_unchanged()

    def test_move_increments_moves(self):
        """Moving increments the moves counter."""
        initial_moves = self.harness.get_global("moves")

        self.go("in")

        new_moves = self.harness.get_global("moves")
        self.assertEqual(new_moves, initial_moves + 1)


class TestVictoryCondition(GrueTestCase):
    """Test victory detection."""

    @classmethod
    def world_path(cls):
        return "examples/outside-door.grue"

    def test_victory_in_hallway(self):
        """Victory is reached by entering HALLWAY."""
        self.assertFalse(self.harness.runtime.check_victory())

        # Go to lobby, then hallway
        self.move_player("LOBBY")
        self.go("north")

        self.assert_player_at("HALLWAY")
        self.assertTrue(self.harness.runtime.check_victory())


if __name__ == "__main__":
    import unittest
    unittest.main()
