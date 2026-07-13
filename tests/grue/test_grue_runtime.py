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
        (world :player PLAYER)
        (room LOBBY :description "A lobby" :properties (:lit true))
        (object PLAYER :location LOBBY :properties (:person true))
        (object KEY :location LOBBY :properties (:takeable true))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert runtime.get_player_location() == "LOBBY"
        assert "KEY" in runtime.get_visible_objects()
        assert len(runtime.get_inventory()) == 0

    def test_room_description(self):
        """Can get room descriptions."""
        source = """
        (world :player PLAYER)
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
        (world :player PLAYER)
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
        (world :player PLAYER)
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
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("_movement", "go", "north")
        assert result.outcome == "blocked"
        # Reason codes deprecated

    def test_blocked_message_exit(self):
        """A message-only :blocked exit refuses movement with its message."""
        source = """
        (world :player PLAYER)
        (room LOBBY :description "A lobby"
          :exits ((north :to HALLWAY)
                  (west :blocked "You would need a machete to go further west.")))
        (room HALLWAY :description "A hallway")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("_movement", "go", "west")
        assert result.outcome == "blocked"
        assert runtime.get_player_location() == "LOBBY"
        ctx = dict(result.context)
        assert ctx["message"] == "You would need a machete to go further west."

        # A message-only blocked exit is not a traversable exit.
        assert "west" not in runtime.get_exits()
        assert "north" in runtime.get_exits()


class TestBehaviorExecution:
    """Test behavior execution."""

    def test_simple_success_behavior(self):
        """Simple always-succeeds behavior."""
        source = """
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object DOOR
          :location LOBBY
          :properties (:door true)
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
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object DOOR
          :location LOBBY
          :properties (:door true :locked true)
          :behaviors (
            :open (fn ()
              (cond
                ((not (:locked ?self)) (success))
                (true (blocked :reason locked))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Door is locked, so should be blocked
        result = runtime.do("DOOR", "open")
        assert result.outcome == "blocked"
        # Note: reason codes are deprecated, always returns "unknown"

    def test_behavior_with_effects(self):
        """Behavior that modifies state."""
        source = """
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object DOOR
          :location LOBBY
          :properties (:door true :locked true)
          :behaviors (
            :unlock (fn ()
              (cond
                ((:locked ?self)
                  '((set ?self :locked false) (success)))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Door starts locked
        assert runtime.state.objects["DOOR"].properties.get("locked")

        result = runtime.do("DOOR", "unlock")
        assert result.outcome == "success"

        # Now unlocked
        assert not runtime.state.objects["DOOR"].properties.get("locked")

    def test_behavior_with_context(self):
        """Behavior returns context hints."""
        source = """
        (world :player PLAYER)
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
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object ROCK :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("ROCK", "open")
        assert result.outcome == "blocked"
        # Reason codes deprecated


class TestMovementViaDoors:
    """Test movement through doors."""

    def test_door_with_through_behavior(self):
        """Exit via door triggers through behavior and completes movement."""
        source = """
        (world :player PLAYER)
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
        (world :player PLAYER)
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
        (world :player PLAYER)
        (room LOBBY :description "A lobby" :properties (:lit true))
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
        # Reason codes deprecated

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
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object KEY :location LOBBY :properties (:takeable true))
        (object COIN :location PLAYER :properties (:takeable true))
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
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object KEY :location PLAYER :properties (:takeable true))
        (object LAMP :location LOBBY :properties (:takeable true))
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
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (room GARDEN :description "A garden")
        (object PLAYER :location LOBBY :properties (:score 0 :moves 0))
        (object KEY :location LOBBY :properties (:takeable true))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Modify state
        runtime.state.objects["PLAYER"].location = "GARDEN"
        runtime.state.objects["KEY"].location = "PLAYER"
        runtime.set_object_property("PLAYER", "score", 100)

        assert runtime.get_player_location() == "GARDEN"
        assert "KEY" in runtime.get_inventory()

        # Reset
        runtime.reset()

        assert runtime.get_player_location() == "LOBBY"
        assert "KEY" not in runtime.get_inventory()
        assert runtime.get_object_property("PLAYER", "score") == 0


class TestEventQueue:
    """Test event queue functionality."""

    def test_queue_basic(self):
        """Can queue and check events."""
        source = """
        (world :player PLAYER)
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
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        runtime.queue_event("LANTERN", 200)
        assert runtime.is_queued("LANTERN")
        assert runtime.get_queue_countdown("LANTERN") == 200

    def test_queue_in_behavior(self):
        """Behaviors can use queue and queued? predicates."""
        source = """
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object BUTTON
          :location LOBBY
          :behaviors (
            :push (fn ()
              (cond
                ((queued? ALARM)
                  '((dequeue ALARM) (success :context ((result alarm-off)))))
                (true
                  '((queue ALARM) (success :context ((result alarm-on)))))))))
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
        (world :player PLAYER)
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
        # Reason codes deprecated

    def test_reset_clears_queues(self):
        """Reset clears all queued events."""
        source = """
        (world :player PLAYER)
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
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object CHAIR :location LOBBY :properties (:furniture true)
          :behaviors (
            :sit (fn ()
              (cond
                (true '((move PLAYER CHAIR)
                        (success :message "You sit in the chair.")))))))
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
        (world :player PLAYER)
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
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object DOOR :location LOBBY :properties (:locked true)
          :behaviors (
            :open (fn ()
              (cond
                ((:locked ?self) (blocked :reason locked))
                (true (success))))
            :enter (fn ()
              (cond
                (true (redirect :action (do DOOR :open)))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("DOOR", "enter")
        assert result.outcome == "blocked"
        # Reason codes deprecated
        assert len(result.redirects) == 1

    def test_redirect_loop_detection(self):
        """Redirect loops are detected and return error."""
        source = """
        (world :player PLAYER)
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
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object THING :location LOBBY
          :behaviors (
            :target (fn ()
              (cond (true (success :final true))))
            :source (fn ()
              (cond (true (redirect :action (do THING :target)
                                    :redirected true))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("THING", "source")
        assert result.outcome == "success"
        # Both contexts should be present
        assert ("redirected", True) in result.context
        assert ("final", True) in result.context



class TestDefaultGlobals:
    """Test built-in runtime globals (score, moves)."""

    def test_properties_in_behavior_conditions(self):
        """Object properties can be checked in behavior conditions."""
        source = """
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object THING :location LOBBY
          :properties (:counter 5)
          :behaviors (
            :examine (fn ()
              (cond
                ((> (:counter ?self) 3)
                  (success :message "Counter is high"))
                (true
                  (success :message "Counter is low"))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("THING", "examine")
        assert result.outcome == "success"
        assert ("message", "Counter is high") in result.context

    def test_properties_modified_by_effects(self):
        """Object properties can be modified by set effects."""
        source = """
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object BUTTON :location LOBBY
          :properties (:counter 0)
          :behaviors (
            :push (fn ()
              (let ((?new-val (+ (:counter ?self) 1)))
                `((set ?self :counter ,?new-val)
                  (success :message "Counter incremented"))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert runtime.get_object_property("BUTTON", "counter") == 0
        runtime.do("BUTTON", "push")
        assert runtime.get_object_property("BUTTON", "counter") == 1
        runtime.do("BUTTON", "push")
        assert runtime.get_object_property("BUTTON", "counter") == 2


class TestEventSystem:
    """Test turn-based event handlers."""

    def test_event_fires_when_queued(self):
        """Events fire when queued and processed."""
        source = """
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)

        (event test-event
          :on-turn (success :context ((message "Event fired"))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Event shouldn't fire if not queued
        results = runtime.process_events()
        assert len(results) == 0

        # Queue the event
        runtime.queue_event("test-event")
        results = runtime.process_events()
        assert len(results) == 1
        assert results[0].outcome == "success"

    def test_event_location_constraint(self):
        """Events with location only fire when player is there."""
        source = """
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (room GARDEN :description "A garden")
        (object PLAYER :location GARDEN)

        (event lobby-only
          :location LOBBY
          :on-turn (success))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        runtime.queue_event("lobby-only")

        # Player is in GARDEN, event shouldn't fire
        results = runtime.process_events()
        assert len(results) == 0

        # Move player to LOBBY
        runtime.state.objects["PLAYER"].location = "LOBBY"
        results = runtime.process_events()
        assert len(results) == 1
        assert results[0].outcome == "success"

    def test_event_countdown(self):
        """Events with countdown wait before firing.

        Countdown semantics: countdown=N means "fire on the Nth turn" (1-indexed).
        - countdown=1 fires immediately (this turn)
        - countdown=2 fires on the second call to process_events
        - countdown=3 fires on the third call, etc.
        """
        source = """
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)

        (event delayed-event
          :on-turn (success :context ((message "Event fired"))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Queue with 3-turn countdown (fire on 3rd call)
        runtime.queue_event("delayed-event", countdown=3)

        # First call: countdown 3 -> 2, doesn't fire
        results = runtime.process_events()
        assert len(results) == 0
        assert runtime.get_queue_countdown("delayed-event") == 2

        # Second call: countdown 2 -> 1, doesn't fire
        results = runtime.process_events()
        assert len(results) == 0
        assert runtime.get_queue_countdown("delayed-event") == 1

        # Third call: countdown 1, event fires
        results = runtime.process_events()
        assert len(results) == 1
        assert results[0].outcome == "success"

    def test_event_staged_logic(self):
        """Events can dequeue themselves after completing their sequence."""
        source = """
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)

        (event hacker-helps
          :location LOBBY
          :on-turn '((dequeue hacker-helps)
                     (success :context ((message "Hacker helps you")))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        runtime.queue_event("hacker-helps")

        # Event fires and dequeues itself
        results = runtime.process_events()
        assert len(results) == 1
        assert ("message", "Hacker helps you") in results[0].context
        assert not runtime.is_queued("hacker-helps")

        # No more events
        results = runtime.process_events()
        assert len(results) == 0

    def test_event_dequeues_self(self):
        """Events can dequeue themselves."""
        source = """
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)

        (event one-shot
          :on-turn (cond
            (true '((dequeue one-shot) (success)))))
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
        (world :player PLAYER)
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
        # Reason codes deprecated

    def test_room_before_action_allows(self):
        """Room :before-action with (default) allows action to proceed."""
        source = """
        (world :player PLAYER)
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

    def test_room_before_action_blocks_certain_targets(self):
        """Room :before-action can block certain targets."""
        source = """
        (world :player PLAYER)
        (room TERMINAL-ROOM
          :description "Terminal room"
          :behaviors (
            :before-action (fn (?verb ?target)
              (cond
                ; Always block screen touch
                ((= ?target "SCREEN")
                  (blocked :reason not-allowed
                           :message "The screen is off-limits."))
                (true (default))))))

        (object PLAYER :location TERMINAL-ROOM)
        (object SCREEN
          :location TERMINAL-ROOM
          :behaviors (
            :click (fn () (cond (true (success :message "You click the screen."))))))
        (object LAMP
          :location TERMINAL-ROOM
          :behaviors (
            :examine (fn () (cond (true (success :message "A lamp."))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Click screen - blocked by before-action
        result = runtime.do("SCREEN", "click")
        assert result.outcome == "blocked"
        # Reason codes deprecated

        # Examine lamp - allowed
        result = runtime.do("LAMP", "examine")
        assert result.outcome == "success"

    def test_room_without_before_action(self):
        """Rooms without :before-action behavior work normally."""
        source = """
        (world :player PLAYER)
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
        (world :player PLAYER)
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
        # Reason codes deprecated

        # Give key - allowed
        result = runtime.do("HACKER", "give", "KEY")
        assert result.outcome == "success"

    def test_room_on_enter_triggered(self):
        """Room :on-enter is called when player enters."""
        source = """
        (world :player PLAYER)
        (room LOBBY
          :description "A lobby"
          :exits ((north :to GARDEN)))

        (room GARDEN
          :description "A garden"
          :exits ((south :to LOBBY))
          :behaviors (
            :on-enter (fn (?from-room)
              (success :welcome true :from ?from-room))))

        (object PLAYER :location LOBBY)
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Move to garden
        result = runtime.do("_movement", "go", "north")
        assert result.outcome == "success"
        assert runtime.get_player_location() == "GARDEN"
        # Check on-enter was triggered and received the from-room
        assert ("welcome", True) in result.context
        assert ("from", "LOBBY") in result.context

    def test_room_on_enter_with_different_origins(self):
        """Room :on-enter can distinguish between different origin rooms."""
        source = """
        (world :player PLAYER)
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
        (world :player PLAYER)
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
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object DOOR :location LOBBY :properties (:locked true)
          :behaviors (
            :open (fn ()
              (if (:locked ?self)
                  (blocked :reason locked :message "The door is locked.")
                  (success :message "The door opens.")))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Door is locked
        result = runtime.do("DOOR", "open")
        assert result.outcome == "blocked"
        # Reason codes deprecated

        # Unlock the door
        runtime.set_object_property("DOOR", "locked", False)
        result = runtime.do("DOOR", "open")
        assert result.outcome == "success"

    def test_behavior_with_direct_success(self):
        """Behavior body can be just (success ...)."""
        source = """
        (world :player PLAYER)
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
        (world :player PLAYER)
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
        (world :player PLAYER)
        (room LOBBY :description "A lobby")
        (object PLAYER :location LOBBY)
        (object BOX :location LOBBY :properties (:locked true :sealed true)
          :behaviors (
            :open (fn ()
              (if (:locked ?self)
                  (blocked :reason locked)
                  (if (:sealed ?self)
                      (blocked :reason sealed)
                      (success))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Both flags set - LOCKED takes precedence
        result = runtime.do("BOX", "open")
        assert result.outcome == "blocked"
        # Reason codes deprecated

        # Remove locked property
        runtime.set_object_property("BOX", "locked", False)
        result = runtime.do("BOX", "open")
        assert result.outcome == "blocked"
        # Reason codes deprecated

        # Remove sealed property
        runtime.set_object_property("BOX", "sealed", False)
        result = runtime.do("BOX", "open")
        assert result.outcome == "success"

    def test_fn_with_parameters_and_if(self):
        """Behavior fn can have parameters and use (if ...)."""
        source = """
        (world :player PLAYER)
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
        # Reason codes deprecated

    def test_mixed_cond_and_if_in_same_world(self):
        """Different behaviors can use cond or if interchangeably."""
        source = """
        (world :player PLAYER)
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


class TestEffectListSyntax:
    """Test the new pure effect list syntax for behaviors.

    In the new syntax, behaviors return quoted lists of effect descriptors:
        '((move @key @player) (success :message "Found!"))

    This enables static analysis because effects are data, not executed code.
    """

    def test_success_with_move_effect(self):
        """Behavior returns effect list with move and success."""
        source = """
        (world :player @player)
        (room LOBBY :description "A lobby")
        (object @player :location LOBBY :properties (:person true))
        (object @key :location LOBBY :properties (:takeable true)
          :behaviors (
            :take (fn ()
              '((move @key @player)
                (success :message "You take the key.")))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # Key starts in LOBBY
        assert runtime.state.objects["@key"].location == "LOBBY"

        result = runtime.do("@key", "take")
        assert result.outcome == "success"
        assert ("message", "You take the key.") in result.context

        # Key should now be on player
        assert runtime.state.objects["@key"].location == "@player"

    def test_blocked_with_reason(self):
        """Behavior returns blocked with reason."""
        source = """
        (world :player @player)
        (room LOBBY :description "A lobby")
        (object @player :location LOBBY :properties (:person true))
        (object @door :location LOBBY
          :behaviors (
            :open (fn ()
              '((blocked :reason locked :message "The door is locked.")))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("@door", "open")
        assert result.outcome == "blocked"
        # Reason codes deprecated
        assert ("message", "The door is locked.") in result.context

    def test_set_flag_effect(self):
        """Effect list can set flags."""
        source = """
        (world :player @player)
        (room LOBBY :description "A lobby")
        (object @player :location LOBBY :properties (:person true))
        (object @lamp :location LOBBY :properties (:lightable true :lit false)
          :behaviors (
            :turn-on (fn ()
              '((set @lamp :lit true)
                (success :message "The lamp is now on.")))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        assert not runtime.state.objects["@lamp"].properties.get("lit")

        result = runtime.do("@lamp", "turn-on")
        assert result.outcome == "success"
        assert runtime.state.objects["@lamp"].properties.get("lit")

    def test_conditional_effects(self):
        """Behaviors can use conditionals to decide which effects to return."""
        source = """
        (world :player @player)
        (room LOBBY :description "A lobby")
        (object @player :location LOBBY :properties (:person true))
        (object @box :location LOBBY :properties (:openable true)
          :behaviors (
            :open (fn ()
              (if (:open @box)
                  '((blocked :reason already-open :message "It's already open."))
                  '((set @box :open true)
                    (success :message "You open the box."))))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # First open succeeds
        result = runtime.do("@box", "open")
        assert result.outcome == "success"
        assert runtime.state.objects["@box"].properties.get("open")

        # Second open is blocked
        result = runtime.do("@box", "open")
        assert result.outcome == "blocked"
        # Reason codes deprecated

    def test_redirect_effect(self):
        """Effect list can redirect to another action.

        Note: The runtime handles redirect by returning outcome="redirect"
        and the caller (do method) follows the redirect.
        """
        source = """
        (world :player @player)
        (room LOBBY :description "A lobby")
        (object @player :location LOBBY :properties (:person true))
        (object @button :location LOBBY
          :behaviors (
            :push (fn ()
              '((redirect (do @mechanism :activate))))))
        (object @mechanism :location LOBBY :properties (:active false)
          :behaviors (
            :activate (fn ()
              '((set @mechanism :active true)
                (success :message "Click!")))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # The do method follows redirects automatically
        result = runtime.do("@button", "push")
        # After redirect, the mechanism should be activated
        assert result.outcome == "success"
        assert runtime.state.objects["@mechanism"].properties.get("active")

    def test_default_terminator(self):
        """Effect list can fall through to default behavior."""
        source = """
        (world :player @player)
        (room LOBBY :description "A lobby")
        (object @player :location LOBBY :properties (:person true))
        (object @generic-item :location LOBBY :properties (:takeable true)
          :behaviors (
            :examine (fn ()
              '((default)))))
        ; Note: default behaviors don't need (fn) wrapper - the body is evaluated directly
        (default examine (success :message "Nothing special."))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("@generic-item", "examine")
        assert result.outcome == "success"
        assert ("message", "Nothing special.") in result.context

    def test_effects_applied_tracking(self):
        """Effect list tracks which effects were applied."""
        source = """
        (world :player @player)
        (room LOBBY :description "A lobby")
        (object @player :location LOBBY :properties (:person true))
        (object @widget :location LOBBY :properties (:active false :powered false)
          :behaviors (
            :activate (fn ()
              '((set @widget :active true)
                (set @widget :powered true)
                (success :message "Activated!")))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        result = runtime.do("@widget", "activate")
        assert result.outcome == "success"
        assert len(result.effects_applied) == 2  # Two set effects

    def test_multiple_mutations_in_effect_list(self):
        """Effect list can have multiple mutations before terminator."""
        source = """
        (world :player @player)
        (room LOBBY :description "A lobby")
        (object @player :location LOBBY :properties (:person true :score 0))
        (object @treasure :location LOBBY :properties (:takeable true :taken false)
          :behaviors (
            :take (fn ()
              '((move @treasure @player)
                (set @treasure :taken true)
                (inc @player :score 10)
                (success :message "You take the treasure! +10 points")))))
        """
        world = parse_grue(source)
        runtime = GrueRuntime(world)

        # score starts at 0
        assert runtime.get_object_property("@player", "score") == 0

        result = runtime.do("@treasure", "take")
        assert result.outcome == "success"
        assert runtime.state.objects["@treasure"].location == "@player"
        assert runtime.state.objects["@treasure"].properties.get("taken")
        assert runtime.get_object_property("@player", "score") == 10


class TestDarkness:
    """Deterministic darkness / light model (gnusto-fa93.4)."""

    def test_room_lit_by_default(self):
        """A room that doesn't declare :lit is lit (darkness is opt-in)."""
        source = """
        (world :player @player)
        (room CAVE :description "A cave")
        (object @player :location CAVE)
        """
        rt = GrueRuntime(parse_grue(source))
        assert rt.is_room_lit("CAVE") is True

    def test_lit_false_room_is_dark(self):
        """A room declared :lit false with no light source is dark."""
        source = """
        (world :player @player
          :dark-message "It is pitch black. You are likely to be eaten by a grue.")
        (room CAVE :description "A cave" :properties (:lit false))
        (object @player :location CAVE)
        """
        rt = GrueRuntime(parse_grue(source))
        assert rt.is_room_lit("CAVE") is False
        assert rt.get_room_description() == (
            "It is pitch black. You are likely to be eaten by a grue."
        )
        assert rt.get_visible_objects(for_description=True) == []

    def test_default_dark_message(self):
        source = """
        (world :player @player)
        (room CAVE :description "A cave" :properties (:lit false))
        (object @player :location CAVE)
        """
        rt = GrueRuntime(parse_grue(source))
        assert rt.get_room_description() == "It is pitch black."

    def test_light_source_illuminates_dark_room(self):
        """Carrying a lit light source relights an otherwise-dark room."""
        source = """
        (world :player @player)
        (room CAVE :description "A cave" :properties (:lit false))
        (object @player :location CAVE)
        (object @lamp :location @player :properties (:takeable true :lightable true))
        """
        rt = GrueRuntime(parse_grue(source))
        assert rt.is_room_lit("CAVE") is False   # lamp off
        rt.set_object_property("@lamp", "lit", True)
        assert rt.is_room_lit("CAVE") is True     # lamp on

    def test_light_source_in_open_container_illuminates(self):
        """A lit source inside an OPEN container (in the room) lights the room;
        a CLOSED container hides its light."""
        source = """
        (world :player @player)
        (room CAVE :description "A cave" :properties (:lit false))
        (object @player :location CAVE)
        (object @basket :location CAVE
          :properties (:container true :openable true :open true))
        (object @torch :location @basket
          :properties (:takeable true :lightable true :lit true))
        """
        rt = GrueRuntime(parse_grue(source))
        assert rt.is_room_lit("CAVE") is True      # open basket -> torch seen
        rt.set_object_property("@basket", "open", False)
        assert rt.is_room_lit("CAVE") is False     # closed -> torch hidden

    def test_dark_hides_listing_but_not_accessibility(self):
        """Darkness suppresses the room listing only; objects stay accessible."""
        source = """
        (world :player @player)
        (room CAVE :description "A cave" :properties (:lit false))
        (object @player :location CAVE)
        (object @rock :location CAVE :properties (:takeable true))
        """
        rt = GrueRuntime(parse_grue(source))
        assert "@rock" not in rt.get_visible_objects(for_description=True)
        assert "@rock" in rt.get_visible_objects(for_description=False)


class TestStartEvents:
    """Persistent always-on events queued at init (world :start-events)."""

    def test_start_events_queued_at_init(self):
        source = """
        (world :player @player :start-events (background-clock))
        (room LOBBY :description "A lobby")
        (object @player :location LOBBY)
        (event background-clock :on-turn (success))
        """
        rt = GrueRuntime(parse_grue(source))
        assert rt.is_queued("background-clock")
        # Indefinite (None countdown), so it survives turns.
        assert rt.get_queue_countdown("background-clock") is None
