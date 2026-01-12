"""Tests for GRUE runtime."""

import pytest
from pathlib import Path

from grue import (
    parse_grue,
    load_grue,
    GrueRuntime,
    ActionResult,
)


class TestBasicRuntime:
    """Test basic runtime functionality."""

    def test_init_state(self):
        """Runtime initializes state from world definition."""
        source = """
        (room LOBBY :description "A lobby" :flags (LIT))
        (object PLAYER :location LOBBY :flags (PERSON))
        (object KEY :location LOBBY :flags (TAKEABLE))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert runtime.get_player_location() == "LOBBY"
        assert "KEY" in runtime.get_visible_objects()
        assert len(runtime.get_inventory()) == 0

    def test_room_description(self):
        """Can get room descriptions."""
        source = """
        (room LOBBY :description "The main lobby")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert runtime.get_room_description() == "The main lobby"
        assert runtime.get_room_description("LOBBY") == "The main lobby"

    def test_exits(self):
        """Can get available exits."""
        source = """
        (room LOBBY
          :description "A lobby"
          :exits ((north :to HALLWAY) (east :to GARDEN)))
        (room HALLWAY :description "A hallway")
        (room GARDEN :description "A garden")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        exits = runtime.get_exits()
        assert exits["north"] == "HALLWAY"
        assert exits["east"] == "GARDEN"


class TestSimpleMovement:
    """Test basic movement."""

    def test_go_direction(self):
        """Can move through simple exits."""
        source = """
        (room LOBBY :description "A lobby" :exits ((north :to HALLWAY)))
        (room HALLWAY :description "A hallway")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert runtime.get_player_location() == "LOBBY"

        result = runtime.do("_movement", "go", "north")
        assert result.outcome == "success"
        assert runtime.get_player_location() == "HALLWAY"

    def test_go_invalid_direction(self):
        """Cannot go in invalid direction."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("_movement", "go", "north")
        assert result.outcome == "blocked"
        assert result.reason == "no-exit"


class TestBehaviorExecution:
    """Test behavior execution."""

    def test_simple_success_behavior(self):
        """Simple always-succeeds behavior."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object DOOR
          :location LOBBY
          :flags (DOOR)
          :behaviors (
            :open (fn ()
              (cond
                (true (success))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("DOOR", "open")
        assert result.outcome == "success"

    def test_conditional_behavior(self):
        """Behavior with conditions."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object DOOR
          :location LOBBY
          :flags (DOOR LOCKED)
          :behaviors (
            :open (fn ()
              (cond
                ((not (has-flag ?self LOCKED)) (success))
                (true (blocked :reason locked))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Door is locked, so should be blocked
        result = runtime.do("DOOR", "open")
        assert result.outcome == "blocked"
        assert result.reason == "locked"

    def test_behavior_with_effects(self):
        """Behavior that modifies state."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object DOOR
          :location LOBBY
          :flags (DOOR LOCKED)
          :behaviors (
            :unlock (fn ()
              (cond
                ((has-flag ?self LOCKED)
                  (success :effects ((clear-flag! ?self LOCKED))))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Door starts locked
        assert "LOCKED" in runtime.state.objects["DOOR"].flags

        result = runtime.do("DOOR", "unlock")
        assert result.outcome == "success"

        # Now unlocked
        assert "LOCKED" not in runtime.state.objects["DOOR"].flags

    def test_behavior_with_context(self):
        """Behavior returns context hints."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object DOOR
          :location LOBBY
          :behaviors (
            :open (fn ()
              (cond
                (true (success :context ((mechanism push-bar))))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("DOOR", "open")
        assert result.outcome == "success"
        assert ("mechanism", "push-bar") in result.context

    def test_no_behavior_for_verb(self):
        """Object without behavior for verb."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object ROCK :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("ROCK", "open")
        assert result.outcome == "blocked"
        assert result.reason == "no-behavior"


class TestMovementViaDoors:
    """Test movement through doors."""

    def test_door_with_through_behavior(self):
        """Exit via door triggers through behavior and completes movement."""
        source = """
        (room OUTSIDE
          :description "Outside"
          :exits ((in :to LOBBY :via DOOR)))
        (room LOBBY :description "Lobby")
        (object PLAYER :location OUTSIDE)
        (object DOOR
          :location OUTSIDE
          :behaviors (
            :through (fn ()
              (cond
                (true (default :action (do _movement :go in)))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert runtime.get_player_location() == "OUTSIDE"

        # Going "in" triggers DOOR's through behavior, which allows passage
        result = runtime.do("_movement", "go", "in")
        assert result.outcome == "success"
        assert runtime.get_player_location() == "LOBBY"


class TestVictoryDefeat:
    """Test win/lose conditions."""

    def test_victory_condition(self):
        """Victory condition check."""
        source = """
        (room LOBBY :description "A lobby")
        (room ENDROOM :description "The end")
        (object PLAYER :location LOBBY)
        (victory :when (= (loc PLAYER) ENDROOM))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert not runtime.check_victory()

        # Move player to end room
        runtime.state.objects["PLAYER"].location = "ENDROOM"
        assert runtime.check_victory()

    def test_defeat_condition(self):
        """Defeat condition check."""
        source = """
        (room LOBBY :description "A lobby" :flags (LIT))
        (room DARKNESS :description "Darkness")
        (object PLAYER :location LOBBY)
        (defeat EATEN-BY-GRUE :when (= (loc PLAYER) DARKNESS))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert runtime.check_defeat() is None

        runtime.state.objects["PLAYER"].location = "DARKNESS"
        assert runtime.check_defeat() == "EATEN-BY-GRUE"


class TestOutsideDoorExample:
    """Test with the actual outside-door.grue example."""

    @pytest.fixture
    def runtime(self):
        example_path = Path(__file__).parent.parent / "games" / "examples" / "outside-door.grue"
        if not example_path.exists():
            pytest.skip("Example file not found")
        world = load_grue(example_path)
        return GrueRuntime(world)

    def test_initial_state(self, runtime):
        """Player starts at @mass-ave."""
        assert runtime.get_player_location() == "@mass-ave"
        assert "@master-key" in runtime.get_inventory()

    def test_open_door_from_outside(self, runtime):
        """Opening door from outside at push-bar location succeeds."""
        result = runtime.do("@outside-door", "open")
        assert result.outcome == "success"
        assert ("mechanism", "push-bar") in result.context

    def test_unlock_door_with_key_from_outside(self, runtime):
        """Unlocking door from outside with physical key fails."""
        result = runtime.do("@outside-door", "unlock", "@master-key")
        assert result.outcome == "blocked"
        assert result.reason == "wrong-key-type"

    def test_victory_in_hallway(self, runtime):
        """Victory when player reaches hallway."""
        assert not runtime.check_victory()

        runtime.state.objects["@player"].location = "@hallway"
        assert runtime.check_victory()

    def test_close_door(self, runtime):
        """Closing door always succeeds (spring-loaded)."""
        result = runtime.do("@outside-door", "close")
        assert result.outcome == "success"
        assert ("note", "spring-loaded") in result.context


class TestInventoryManagement:
    """Test object manipulation."""

    def test_visible_objects(self):
        """Objects in room are visible."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object KEY :location LOBBY :flags (TAKEABLE))
        (object COIN :location PLAYER :flags (TAKEABLE))
        (object HIDDEN :location ELSEWHERE)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        visible = runtime.get_visible_objects()
        assert "KEY" in visible
        assert "COIN" in visible  # In inventory is visible
        assert "HIDDEN" not in visible

    def test_inventory(self):
        """Objects with PLAYER location are inventory."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object KEY :location PLAYER :flags (TAKEABLE))
        (object LAMP :location LOBBY :flags (TAKEABLE))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        inv = runtime.get_inventory()
        assert "KEY" in inv
        assert "LAMP" not in inv


class TestReset:
    """Test state reset."""

    def test_reset_state(self):
        """Reset restores initial state."""
        source = """
        (room LOBBY :description "A lobby")
        (room GARDEN :description "A garden")
        (object PLAYER :location LOBBY)
        (object KEY :location LOBBY :flags (TAKEABLE))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Modify state
        runtime.state.objects["PLAYER"].location = "GARDEN"
        runtime.state.objects["KEY"].location = "PLAYER"
        runtime.state.globals["score"] = 100

        assert runtime.get_player_location() == "GARDEN"
        assert "KEY" in runtime.get_inventory()

        # Reset
        runtime.reset()

        assert runtime.get_player_location() == "LOBBY"
        assert "KEY" not in runtime.get_inventory()
        assert runtime.state.globals["score"] == 0


class TestEventQueue:
    """Test event queue functionality."""

    def test_queue_basic(self):
        """Can queue and check events."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Initially not queued
        assert not runtime.is_queued("HACKER-HELPS")

        # Queue it
        runtime.queue_event("HACKER-HELPS")
        assert runtime.is_queued("HACKER-HELPS")

        # Dequeue it
        runtime.dequeue_event("HACKER-HELPS")
        assert not runtime.is_queued("HACKER-HELPS")

    def test_queue_with_countdown(self):
        """Can queue events with countdown."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        runtime.queue_event("LANTERN", 200)
        assert runtime.is_queued("LANTERN")
        assert runtime.get_queue_countdown("LANTERN") == 200

    def test_queue_in_behavior(self):
        """Behaviors can use queue! and queued? predicates."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object BUTTON
          :location LOBBY
          :behaviors (
            :push (fn ()
              (cond
                ((queued? ALARM)
                  (success :effects ((dequeue! ALARM))
                           :context ((result alarm-off))))
                (true
                  (success :effects ((queue! ALARM))
                           :context ((result alarm-on))))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # First push queues alarm
        result = runtime.do("BUTTON", "push")
        assert result.outcome == "success"
        assert ("result", "alarm-on") in result.context
        assert runtime.is_queued("ALARM")

        # Second push dequeues alarm
        result = runtime.do("BUTTON", "push")
        assert result.outcome == "success"
        assert ("result", "alarm-off") in result.context
        assert not runtime.is_queued("ALARM")

    def test_queue_blocks_action(self):
        """Queued events can block actions."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object PC
          :location LOBBY
          :behaviors (
            :turn-off (fn ()
              (cond
                ((queued? HACKER-HELPS)
                  (blocked :reason hacker-interference
                           :context ((blocker HACKER))))
                (true
                  (success))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Without queue, action succeeds
        result = runtime.do("PC", "turn-off")
        assert result.outcome == "success"

        # Queue the event
        runtime.queue_event("HACKER-HELPS")

        # Now action is blocked
        result = runtime.do("PC", "turn-off")
        assert result.outcome == "blocked"
        assert result.reason == "hacker-interference"

    def test_reset_clears_queues(self):
        """Reset clears all queued events."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        runtime.queue_event("EVENT1")
        runtime.queue_event("EVENT2", 10)
        assert runtime.is_queued("EVENT1")
        assert runtime.is_queued("EVENT2")

        runtime.reset()

        assert not runtime.is_queued("EVENT1")
        assert not runtime.is_queued("EVENT2")


class TestRedirectFollowing:
    """Test automatic redirect following."""

    def test_simple_redirect(self):
        """Redirect is followed automatically."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object CHAIR :location LOBBY :flags (FURNITURE)
          :behaviors (
            :sit (fn ()
              (cond
                (true (success :effects ((move! PLAYER CHAIR))
                              :message "You sit in the chair."))))))
        (object DESK :location LOBBY
          :behaviors (
            :sit-at (fn ()
              (cond
                (true (redirect :action (do CHAIR :sit)))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # sit-at DESK should redirect to sit CHAIR
        result = runtime.do("DESK", "sit-at")
        assert result.outcome == "success"
        assert len(result.redirects) == 1
        assert runtime.state.objects["PLAYER"].location == "CHAIR"

    def test_redirect_chain(self):
        """Multiple redirects are followed."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object THING :location LOBBY
          :behaviors (
            :final (fn ()
              (cond (true (success :message "Reached final!"))))
            :middle (fn ()
              (cond (true (redirect :action (do THING :final)))))
            :start (fn ()
              (cond (true (redirect :action (do THING :middle)))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("THING", "start")
        assert result.outcome == "success"
        assert len(result.redirects) == 2
        assert ("message", "Reached final!") in result.context

    def test_redirect_to_blocked(self):
        """Redirect to blocked action returns blocked."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object DOOR :location LOBBY :flags (LOCKED)
          :behaviors (
            :open (fn ()
              (cond
                ((has-flag ?self LOCKED) (blocked :reason locked))
                (true (success))))
            :enter (fn ()
              (cond
                (true (redirect :action (do DOOR :open)))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("DOOR", "enter")
        assert result.outcome == "blocked"
        assert result.reason == "locked"
        assert len(result.redirects) == 1

    def test_redirect_loop_detection(self):
        """Redirect loops are detected and return error."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object THING :location LOBBY
          :behaviors (
            :action-a (fn ()
              (cond (true (redirect :action (do THING :action-b)))))
            :action-b (fn ()
              (cond (true (redirect :action (do THING :action-a)))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("THING", "action-a")
        assert result.outcome == "error"
        assert "loop" in result.error.lower()

    def test_redirect_preserves_context(self):
        """Context from redirect is preserved."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object THING :location LOBBY
          :behaviors (
            :target (fn ()
              (cond (true (success :context ((final true))))))
            :source (fn ()
              (cond (true (redirect :action (do THING :target)
                                    :context ((redirected true))))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("THING", "source")
        assert result.outcome == "success"
        # Both contexts should be present
        assert ("redirected", True) in result.context
        assert ("final", True) in result.context



class TestGlobalsRuntime:
    """Test globals initialization and usage at runtime."""

    def test_globals_initialized_from_world(self):
        """Globals from world definition are available at runtime."""
        source = """
        (globals
          :lair-cnt 0
          :hacker-help 0
          :active true)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert runtime.get_global("lair-cnt") == 0
        assert runtime.get_global("hacker-help") == 0
        assert runtime.get_global("active") is True

    def test_default_globals_preserved(self):
        """Default globals (score, moves) are set if not defined."""
        source = """
        (globals :custom-var 42)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Custom global is set
        assert runtime.get_global("custom-var") == 42
        # Default globals still present
        assert runtime.get_global("score") == 0
        assert runtime.get_global("moves") == 0

    def test_world_can_override_defaults(self):
        """World can override default global values."""
        source = """
        (globals :score 100 :moves 50)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert runtime.get_global("score") == 100
        assert runtime.get_global("moves") == 50

    def test_globals_in_behavior_conditions(self):
        """Globals can be checked in behavior conditions."""
        source = """
        (globals :counter 5)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object THING :location LOBBY
          :behaviors (
            :examine (fn ()
              (cond
                ((> counter 3)
                  (success :message "Counter is high"))
                (true
                  (success :message "Counter is low"))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("THING", "examine")
        assert result.outcome == "success"
        assert ("message", "Counter is high") in result.context

    def test_globals_modified_by_effects(self):
        """Globals can be modified by set! effects."""
        source = """
        (globals :counter 0)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object BUTTON :location LOBBY
          :behaviors (
            :push (fn ()
              (cond
                (true (success
                        :effects ((inc! counter))
                        :message "Counter incremented"))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert runtime.get_global("counter") == 0
        runtime.do("BUTTON", "push")
        assert runtime.get_global("counter") == 1
        runtime.do("BUTTON", "push")
        assert runtime.get_global("counter") == 2


class TestEventSystem:
    """Test turn-based event handlers."""

    def test_event_fires_when_queued(self):
        """Events fire when queued and processed."""
        source = """
        (globals :stage 0)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)

        (event test-event
          :on-turn (cond
            (true (success
                    :effects ((inc! stage))
                    :context ((message "Event fired"))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Event shouldn't fire if not queued
        results = runtime.process_events()
        assert len(results) == 0
        assert runtime.get_global("stage") == 0

        # Queue the event
        runtime.queue_event("test-event")
        results = runtime.process_events()
        assert len(results) == 1
        assert results[0].outcome == "success"
        assert runtime.get_global("stage") == 1

    def test_event_location_constraint(self):
        """Events with location only fire when player is there."""
        source = """
        (globals :stage 0)
        (room LOBBY :description "A lobby")
        (room GARDEN :description "A garden")
        (object PLAYER :location GARDEN)

        (event lobby-only
          :location LOBBY
          :on-turn (cond
            (true (success :effects ((inc! stage))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        runtime.queue_event("lobby-only")

        # Player is in GARDEN, event shouldn't fire
        results = runtime.process_events()
        assert len(results) == 0
        assert runtime.get_global("stage") == 0

        # Move player to LOBBY
        runtime.state.objects["PLAYER"].location = "LOBBY"
        results = runtime.process_events()
        assert len(results) == 1
        assert runtime.get_global("stage") == 1

    def test_event_countdown(self):
        """Events with countdown wait before firing."""
        source = """
        (globals :stage 0)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)

        (event delayed-event
          :on-turn (cond
            (true (success :effects ((inc! stage))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Queue with 2-turn countdown
        runtime.queue_event("delayed-event", countdown=2)

        # First call: countdown 2 -> 1
        results = runtime.process_events()
        assert len(results) == 0
        assert runtime.get_global("stage") == 0
        assert runtime.get_queue_countdown("delayed-event") == 1

        # Second call: countdown 1 -> 0
        results = runtime.process_events()
        assert len(results) == 0
        assert runtime.get_global("stage") == 0
        assert runtime.get_queue_countdown("delayed-event") == 0

        # Third call: countdown 0, event fires
        results = runtime.process_events()
        assert len(results) == 1
        assert runtime.get_global("stage") == 1

    def test_event_staged_logic(self):
        """Events can use stage-based conditions like I-HACKER-HELPS."""
        source = """
        (globals :help-stage 0)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)

        (event hacker-helps
          :location LOBBY
          :on-turn (cond
            ((= help-stage 0)
              (success
                :effects ((inc! help-stage))
                :context ((message "Hacker walks over"))))
            ((= help-stage 1)
              (success
                :effects ((inc! help-stage))
                :context ((message "Hacker types furiously"))))
            ((= help-stage 2)
              (success
                :effects ((inc! help-stage))
                :context ((message "Hacker explains problem"))))
            (true
              (success
                :effects ((dequeue! hacker-helps))
                :context ((message "Hacker returns to seat"))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        runtime.queue_event("hacker-helps")

        # Stage 1
        results = runtime.process_events()
        assert len(results) == 1
        assert ("message", "Hacker walks over") in results[0].context
        assert runtime.get_global("help-stage") == 1

        # Stage 2
        results = runtime.process_events()
        assert ("message", "Hacker types furiously") in results[0].context
        assert runtime.get_global("help-stage") == 2

        # Stage 3
        results = runtime.process_events()
        assert ("message", "Hacker explains problem") in results[0].context
        assert runtime.get_global("help-stage") == 3

        # Final stage - dequeues itself
        results = runtime.process_events()
        assert ("message", "Hacker returns to seat") in results[0].context
        assert not runtime.is_queued("hacker-helps")

        # No more events
        results = runtime.process_events()
        assert len(results) == 0

    def test_event_dequeues_self(self):
        """Events can dequeue themselves."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)

        (event one-shot
          :on-turn (cond
            (true (success :effects ((dequeue! one-shot))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        runtime.queue_event("one-shot")
        assert runtime.is_queued("one-shot")

        results = runtime.process_events()
        assert len(results) == 1
        assert not runtime.is_queued("one-shot")

        # Won't fire again
        results = runtime.process_events()
        assert len(results) == 0


class TestRoomBehaviors:
    """Test room behaviors with :before-action hook."""

    def test_room_before_action_blocks(self):
        """Room :before-action can block an action."""
        source = """
        (room LOBBY
          :description "A lobby"
          :behaviors (
            :before-action (fn (?verb ?target)
              (cond
                ; Block examining the lamp
                ((and (= ?verb "examine") (= ?target "LAMP"))
                  (blocked :reason haunted :message "The ghost won't let you."))
                (true (default))))))

        (object PLAYER :location LOBBY)
        (object LAMP
          :location LOBBY
          :behaviors (
            :examine (fn () (cond (true (success :message "A brass lamp."))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Examine lamp is blocked by room
        result = runtime.do("LAMP", "examine")
        assert result.outcome == "blocked"
        assert result.reason == "haunted"

    def test_room_before_action_allows(self):
        """Room :before-action with (default) allows action to proceed."""
        source = """
        (room LOBBY
          :description "A lobby"
          :behaviors (
            :before-action (fn (?verb ?target)
              (cond
                ; Only block examine on LAMP
                ((and (= ?verb "examine") (= ?target "LAMP"))
                  (blocked :reason haunted))
                (true (default))))))

        (object PLAYER :location LOBBY)
        (object KEY
          :location LOBBY
          :behaviors (
            :examine (fn () (cond (true (success :message "A brass key."))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Examine key is allowed
        result = runtime.do("KEY", "examine")
        assert result.outcome == "success"

    def test_room_before_action_with_event_state(self):
        """Room :before-action can check event queue state."""
        source = """
        (globals :helping false)

        (room TERMINAL-ROOM
          :description "Terminal room"
          :behaviors (
            :before-action (fn (?verb ?target)
              (cond
                ; Block screen actions while helping
                ((and helping (= ?target "SCREEN"))
                  (blocked :reason hacker-busy
                           :message "The hacker snarls at you."))
                (true (default))))))

        (object PLAYER :location TERMINAL-ROOM)
        (object SCREEN
          :location TERMINAL-ROOM
          :behaviors (
            :click (fn () (cond (true (success :message "You click the screen."))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Click screen when not helping - allowed
        result = runtime.do("SCREEN", "click")
        assert result.outcome == "success"

        # Set helping flag
        runtime.set_global("helping", True)

        # Click screen when helping - blocked
        result = runtime.do("SCREEN", "click")
        assert result.outcome == "blocked"
        assert result.reason == "hacker-busy"

    def test_room_without_before_action(self):
        """Rooms without :before-action behavior work normally."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object LAMP
          :location LOBBY
          :behaviors (
            :examine (fn () (cond (true (success :message "A lamp."))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("LAMP", "examine")
        assert result.outcome == "success"

    def test_room_before_action_receives_args(self):
        """Room :before-action receives action arguments."""
        source = """
        (room LOBBY
          :description "A lobby"
          :behaviors (
            :before-action (fn (?verb ?target ?arg1)
              (cond
                ; Block giving food to anyone
                ((and (= ?verb "give") (= ?arg1 "FOOD"))
                  (blocked :reason no-sharing))
                (true (default))))))

        (object PLAYER :location LOBBY)
        (object HACKER
          :location LOBBY
          :behaviors (
            :give (fn (?item)
              (cond (true (success :message "Thanks!"))))))
        (object FOOD :location LOBBY)
        (object KEY :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Give food - blocked
        result = runtime.do("HACKER", "give", "FOOD")
        assert result.outcome == "blocked"
        assert result.reason == "no-sharing"

        # Give key - allowed
        result = runtime.do("HACKER", "give", "KEY")
        assert result.outcome == "success"

    def test_room_on_enter_triggered(self):
        """Room :on-enter is called when player enters."""
        source = """
        (globals :entered-from nil)

        (room LOBBY
          :description "A lobby"
          :exits ((north :to GARDEN)))

        (room GARDEN
          :description "A garden"
          :exits ((south :to LOBBY))
          :behaviors (
            :on-enter (fn (?from-room)
              (success
                :effects ((set! entered-from ?from-room))
                :context ((welcome true) (from ?from-room))))))

        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Move to garden
        result = runtime.do("_movement", "go", "north")
        assert result.outcome == "success"
        assert runtime.get_player_location() == "GARDEN"
        # Check on-enter was triggered
        assert ("welcome", True) in result.context
        assert ("from", "LOBBY") in result.context
        # Check effect was applied
        assert runtime.state.globals.get("entered-from") == "LOBBY"

    def test_room_on_enter_with_different_origins(self):
        """Room :on-enter can distinguish between different origin rooms."""
        source = """
        (room LOBBY
          :description "A lobby"
          :exits ((north :to GARDEN)))

        (room KITCHEN
          :description "A kitchen"
          :exits ((east :to GARDEN)))

        (room GARDEN
          :description "A garden"
          :exits ((south :to LOBBY) (west :to KITCHEN))
          :behaviors (
            :on-enter (fn (?from-room)
              (cond
                ((= ?from-room "LOBBY")
                  (success :context ((entrance "front"))))
                ((= ?from-room "KITCHEN")
                  (success :context ((entrance "side"))))
                (true (success))))))

        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Enter from lobby
        result = runtime.do("_movement", "go", "north")
        assert ("entrance", "front") in result.context

        # Go to kitchen via garden
        runtime.do("_movement", "go", "west")
        assert runtime.get_player_location() == "KITCHEN"

        # Enter garden from kitchen
        result = runtime.do("_movement", "go", "east")
        assert ("entrance", "side") in result.context

    def test_room_without_on_enter(self):
        """Rooms without :on-enter work normally."""
        source = """
        (room LOBBY
          :description "A lobby"
          :exits ((north :to GARDEN)))

        (room GARDEN
          :description "A garden"
          :exits ((south :to LOBBY)))

        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Move to garden - no on-enter, should still work
        result = runtime.do("_movement", "go", "north")
        assert result.outcome == "success"
        assert runtime.get_player_location() == "GARDEN"


class TestGeneralizedFn:
    """Test generalized fn support - behaviors not limited to cond."""

    def test_behavior_with_if_instead_of_cond(self):
        """Behavior body can use (if ...) instead of (cond ...)."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object DOOR :location LOBBY :flags (locked)
          :behaviors (
            :open (fn ()
              (if (has-flag ?self locked)
                  (blocked :reason locked :message "The door is locked.")
                  (success :message "The door opens.")))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Door is locked
        result = runtime.do("DOOR", "open")
        assert result.outcome == "blocked"
        assert result.reason == "locked"

        # Unlock the door
        runtime.clear_object_flag("DOOR", "locked")
        result = runtime.do("DOOR", "open")
        assert result.outcome == "success"

    def test_behavior_with_direct_success(self):
        """Behavior body can be just (success ...)."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object LAMP :location LOBBY
          :behaviors (
            :examine (fn () (success :message "A brass lamp."))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("LAMP", "examine")
        assert result.outcome == "success"
        assert ("message", "A brass lamp.") in result.context

    def test_behavior_with_let_binding(self):
        """Behavior body can use (let ...)."""
        source = """
        (globals :base-price 100)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object ITEM :location LOBBY
          :properties (:multiplier 2)
          :behaviors (
            :appraise (fn ()
              (let ((?mult (prop ?self multiplier)))
                (if (> ?mult 1)
                    (success :value "expensive")
                    (success :value "cheap"))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("ITEM", "appraise")
        assert result.outcome == "success"
        assert ("value", "expensive") in result.context

    def test_behavior_with_nested_if(self):
        """Behavior body can have nested (if ...)."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object BOX :location LOBBY :flags (locked sealed)
          :behaviors (
            :open (fn ()
              (if (has-flag ?self locked)
                  (blocked :reason locked)
                  (if (has-flag ?self sealed)
                      (blocked :reason sealed)
                      (success))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Both flags set - locked takes precedence
        result = runtime.do("BOX", "open")
        assert result.outcome == "blocked"
        assert result.reason == "locked"

        # Remove locked flag
        runtime.clear_object_flag("BOX", "locked")
        result = runtime.do("BOX", "open")
        assert result.outcome == "blocked"
        assert result.reason == "sealed"

        # Remove sealed flag
        runtime.clear_object_flag("BOX", "sealed")
        result = runtime.do("BOX", "open")
        assert result.outcome == "success"

    def test_fn_with_parameters_and_if(self):
        """Behavior fn can have parameters and use (if ...)."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object NPC :location LOBBY
          :behaviors (
            :give (fn (?item)
              (if (= ?item "FOOD")
                  (success :message "Thanks for the food!")
                  (blocked :reason wrong-item :message "I don't want that.")))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("NPC", "give", "FOOD")
        assert result.outcome == "success"
        assert ("message", "Thanks for the food!") in result.context

        result = runtime.do("NPC", "give", "ROCK")
        assert result.outcome == "blocked"
        assert result.reason == "wrong-item"

    def test_mixed_cond_and_if_in_same_world(self):
        """Different behaviors can use cond or if interchangeably."""
        source = """
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)

        ; This object uses cond
        (object OLD_STYLE :location LOBBY
          :behaviors (
            :examine (fn ()
              (cond
                (true (success :style "cond"))))))

        ; This object uses if
        (object NEW_STYLE :location LOBBY
          :behaviors (
            :examine (fn ()
              (if true
                  (success :style "if")
                  (blocked :reason impossible)))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("OLD_STYLE", "examine")
        assert result.outcome == "success"
        assert ("style", "cond") in result.context

        result = runtime.do("NEW_STYLE", "examine")
        assert result.outcome == "success"
        assert ("style", "if") in result.context
