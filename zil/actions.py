"""
ZIL Action System

Defines game actions with preconditions and effects.
This is the formal layer that the LLM interacts with via tools.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .world import World


class ActionResult(Enum):
    """Result of attempting an action."""

    SUCCESS = "success"
    FAILURE = "failure"
    INVALID = "invalid"  # Action doesn't make sense in context


@dataclass
class ActionResponse:
    """Response from attempting an action."""

    result: ActionResult
    message: str  # Human-readable explanation
    state_changed: bool = False
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    """
    A game action with preconditions and effects.

    Actions are the atomic operations that can change game state.
    The LLM selects actions; the engine executes them.
    """

    name: str
    description: str
    # Synonyms that map to this action
    synonyms: list[str] = field(default_factory=list)
    # What object types this action applies to (empty = no object needed)
    applies_to: list[str] = field(default_factory=list)
    # Whether this action requires an object
    requires_object: bool = True
    # Whether this action can take a second object (e.g., PUT X IN Y)
    takes_indirect_object: bool = False


class ActionExecutor:
    """
    Executes actions against the game world.

    This is the authoritative source of what actions are valid
    and what effects they have.
    """

    def __init__(self, world: World):
        self.world = world
        self._actions: dict[str, Action] = {}
        self._handlers: dict[str, Callable[..., ActionResponse]] = {}
        self._register_core_actions()

    def _register_core_actions(self) -> None:
        """Register the core set of game actions."""

        # Movement
        self.register_action(
            Action(
                name="go",
                description="Move in a direction",
                synonyms=["walk", "move", "head", "travel", "run"],
                requires_object=True,  # Direction is the "object"
                applies_to=["direction"],
            ),
            self._do_go,
        )

        # Object manipulation
        self.register_action(
            Action(
                name="take",
                description="Pick up an object",
                synonyms=["get", "grab", "pick up", "acquire", "snag"],
                requires_object=True,
                applies_to=["takeable"],
            ),
            self._do_take,
        )

        self.register_action(
            Action(
                name="drop",
                description="Put down an object you're carrying",
                synonyms=["put down", "release", "discard", "leave"],
                requires_object=True,
                applies_to=["carried"],
            ),
            self._do_drop,
        )

        # Examination
        self.register_action(
            Action(
                name="examine",
                description="Look at something closely",
                synonyms=["look at", "inspect", "study", "check", "x"],
                requires_object=True,
                applies_to=["visible"],
            ),
            self._do_examine,
        )

        self.register_action(
            Action(
                name="look",
                description="Look around the current location",
                synonyms=["l", "look around"],
                requires_object=False,
            ),
            self._do_look,
        )

        # Container/door operations
        self.register_action(
            Action(
                name="open",
                description="Open a door or container",
                synonyms=["open up"],
                requires_object=True,
                applies_to=["openable"],
            ),
            self._do_open,
        )

        self.register_action(
            Action(
                name="close",
                description="Close a door or container",
                synonyms=["shut"],
                requires_object=True,
                applies_to=["openable"],
            ),
            self._do_close,
        )

        # Device operations
        self.register_action(
            Action(
                name="turn_on",
                description="Turn on a device or light",
                synonyms=["switch on", "activate", "light"],
                requires_object=True,
                applies_to=["device"],
            ),
            self._do_turn_on,
        )

        self.register_action(
            Action(
                name="turn_off",
                description="Turn off a device or light",
                synonyms=["switch off", "deactivate", "extinguish"],
                requires_object=True,
                applies_to=["device"],
            ),
            self._do_turn_off,
        )

        # Reading
        self.register_action(
            Action(
                name="read",
                description="Read text on something",
                synonyms=["peruse"],
                requires_object=True,
                applies_to=["readable"],
            ),
            self._do_read,
        )

        # Inventory
        self.register_action(
            Action(
                name="inventory",
                description="Check what you're carrying",
                synonyms=["i", "inv", "take inventory"],
                requires_object=False,
            ),
            self._do_inventory,
        )

        # Waiting
        self.register_action(
            Action(
                name="wait",
                description="Wait and let time pass",
                synonyms=["z"],
                requires_object=False,
            ),
            self._do_wait,
        )

    def register_action(
        self, action: Action, handler: Callable[..., ActionResponse]
    ) -> None:
        """Register an action and its handler."""
        self._actions[action.name] = action
        self._handlers[action.name] = handler
        # Also register synonyms
        for syn in action.synonyms:
            self._actions[syn] = action

    def get_action(self, name: str) -> Action | None:
        """Get an action by name or synonym."""
        return self._actions.get(name.lower())

    def list_actions(self) -> list[Action]:
        """List all unique actions (not synonyms)."""
        seen = set()
        actions = []
        for action in self._actions.values():
            if action.name not in seen:
                seen.add(action.name)
                actions.append(action)
        return actions

    def get_valid_actions(self) -> list[dict[str, Any]]:
        """
        Get all currently valid actions with context.

        Returns a list suitable for LLM consumption.
        """
        valid = []

        for action in self.list_actions():
            action_info = {
                "action": action.name,
                "description": action.description,
                "requires_object": action.requires_object,
            }

            if action.requires_object:
                # List valid targets for this action
                targets = self._get_valid_targets(action)
                if targets or action.name == "go":  # go always available with directions
                    action_info["valid_targets"] = targets
                    valid.append(action_info)
            else:
                valid.append(action_info)

        return valid

    def _get_valid_targets(self, action: Action) -> list[str]:
        """Get valid targets for an action."""
        targets = []

        if action.name == "go":
            # Directions are always potential targets
            exits = self.world.get_room_exits()
            for direction in exits.keys():
                can_go, _ = self.world.can_go(direction)
                if can_go:
                    targets.append(direction.lower())
            return targets

        if action.name == "drop":
            # Can drop anything in inventory
            return list(self.world.state.inventory)

        # For other actions, check visible objects
        for obj_name in self.world.get_visible_objects():
            obj = self.world.get_object(obj_name)
            obj_state = self.world.get_object_state(obj_name)
            if not obj or not obj_state:
                continue

            if self._object_valid_for_action(action, obj_name, obj_state.flags):
                targets.append(obj_name.lower())

        return targets

    def _object_valid_for_action(
        self, action: Action, obj_name: str, flags: set[str]
    ) -> bool:
        """Check if an object is a valid target for an action."""
        if action.name == "take":
            return "TAKEBIT" in flags

        if action.name == "examine":
            return True  # Can examine anything visible

        if action.name in ("open", "close"):
            return "OPENBIT" in flags or "DOORBIT" in flags or "CONTBIT" in flags

        if action.name in ("turn_on", "turn_off"):
            return "LIGHTBIT" in flags or "DEVICEBIT" in flags

        if action.name == "read":
            return "READBIT" in flags

        return True

    def execute(
        self, action_name: str, obj_name: str | None = None, indirect_obj: str | None = None
    ) -> ActionResponse:
        """
        Execute an action.

        Args:
            action_name: The action to perform
            obj_name: The direct object (if any)
            indirect_obj: The indirect object (if any, e.g., for PUT X IN Y)

        Returns:
            ActionResponse with result and message
        """
        action = self.get_action(action_name)
        if not action:
            return ActionResponse(
                result=ActionResult.INVALID,
                message=f"I don't understand '{action_name}'.",
            )

        handler = self._handlers.get(action.name)
        if not handler:
            return ActionResponse(
                result=ActionResult.INVALID,
                message=f"Action '{action.name}' is not implemented.",
            )

        # Check if object is required
        if action.requires_object and not obj_name:
            return ActionResponse(
                result=ActionResult.INVALID,
                message=f"What do you want to {action.name}?",
            )

        return handler(obj_name, indirect_obj)

    # === Action Handlers ===

    def _do_go(self, direction: str | None, _: str | None) -> ActionResponse:
        """Handle movement."""
        if not direction:
            return ActionResponse(
                result=ActionResult.INVALID,
                message="Which direction do you want to go?",
            )

        direction = direction.upper()
        success, result = self.world.move_player(direction)

        if success:
            room_desc = self.world.describe_room()
            return ActionResponse(
                result=ActionResult.SUCCESS,
                message=room_desc,
                state_changed=True,
                details={"new_room": self.world.state.current_room},
            )
        else:
            return ActionResponse(
                result=ActionResult.FAILURE,
                message=result,
            )

    def _do_take(self, obj_name: str | None, _: str | None) -> ActionResponse:
        """Handle taking objects."""
        if not obj_name:
            return ActionResponse(
                result=ActionResult.INVALID,
                message="What do you want to take?",
            )

        obj_name = obj_name.upper()
        success, message = self.world.take_object(obj_name)

        return ActionResponse(
            result=ActionResult.SUCCESS if success else ActionResult.FAILURE,
            message=message,
            state_changed=success,
        )

    def _do_drop(self, obj_name: str | None, _: str | None) -> ActionResponse:
        """Handle dropping objects."""
        if not obj_name:
            return ActionResponse(
                result=ActionResult.INVALID,
                message="What do you want to drop?",
            )

        obj_name = obj_name.upper()
        success, message = self.world.drop_object(obj_name)

        return ActionResponse(
            result=ActionResult.SUCCESS if success else ActionResult.FAILURE,
            message=message,
            state_changed=success,
        )

    def _do_examine(self, obj_name: str | None, _: str | None) -> ActionResponse:
        """Handle examining objects."""
        if not obj_name:
            return ActionResponse(
                result=ActionResult.INVALID,
                message="What do you want to examine?",
            )

        obj_name = obj_name.upper()

        # Check if it's a room feature
        room = self.world.get_current_room()
        if room:
            # Could check for room-specific examine responses here
            pass

        # Check objects
        obj = self.world.get_object(obj_name)
        if not obj:
            # Also check rooms (for examining the room itself)
            obj = self.world.get_room(obj_name)

        if not obj:
            return ActionResponse(
                result=ActionResult.FAILURE,
                message=f"You don't see any {obj_name.lower()} here.",
            )

        # Build description
        desc = obj.get_property_value("LDESC") or obj.get_property_value("DESC", obj_name)

        # Check for TEXT property (for readable items)
        text = obj.get_property_value("TEXT")
        if text:
            desc = f"{desc}\n\n{text}"

        return ActionResponse(
            result=ActionResult.SUCCESS,
            message=desc if desc else f"You see nothing special about the {obj_name.lower()}.",
            details={"object": obj_name},
        )

    def _do_look(self, _: str | None, __: str | None) -> ActionResponse:
        """Handle looking around."""
        return ActionResponse(
            result=ActionResult.SUCCESS,
            message=self.world.describe_room(),
        )

    def _do_open(self, obj_name: str | None, _: str | None) -> ActionResponse:
        """Handle opening things."""
        if not obj_name:
            return ActionResponse(
                result=ActionResult.INVALID,
                message="What do you want to open?",
            )

        obj_name = obj_name.upper()
        obj_state = self.world.get_object_state(obj_name)

        if not obj_state:
            return ActionResponse(
                result=ActionResult.FAILURE,
                message=f"You don't see any {obj_name.lower()} here.",
            )

        if "OPENBIT" not in obj_state.flags and "DOORBIT" not in obj_state.flags and "CONTBIT" not in obj_state.flags:
            return ActionResponse(
                result=ActionResult.FAILURE,
                message=f"You can't open the {obj_name.lower()}.",
            )

        if "OPENBIT" in obj_state.flags:
            return ActionResponse(
                result=ActionResult.FAILURE,
                message=f"The {obj_name.lower()} is already open.",
            )

        # Open it
        obj_state.flags.add("OPENBIT")
        return ActionResponse(
            result=ActionResult.SUCCESS,
            message=f"You open the {obj_name.lower()}.",
            state_changed=True,
        )

    def _do_close(self, obj_name: str | None, _: str | None) -> ActionResponse:
        """Handle closing things."""
        if not obj_name:
            return ActionResponse(
                result=ActionResult.INVALID,
                message="What do you want to close?",
            )

        obj_name = obj_name.upper()
        obj_state = self.world.get_object_state(obj_name)

        if not obj_state:
            return ActionResponse(
                result=ActionResult.FAILURE,
                message=f"You don't see any {obj_name.lower()} here.",
            )

        if "OPENBIT" not in obj_state.flags:
            return ActionResponse(
                result=ActionResult.FAILURE,
                message=f"The {obj_name.lower()} isn't open.",
            )

        # Close it
        obj_state.flags.remove("OPENBIT")
        return ActionResponse(
            result=ActionResult.SUCCESS,
            message=f"You close the {obj_name.lower()}.",
            state_changed=True,
        )

    def _do_turn_on(self, obj_name: str | None, _: str | None) -> ActionResponse:
        """Handle turning things on."""
        if not obj_name:
            return ActionResponse(
                result=ActionResult.INVALID,
                message="What do you want to turn on?",
            )

        obj_name = obj_name.upper()
        obj_state = self.world.get_object_state(obj_name)

        if not obj_state:
            return ActionResponse(
                result=ActionResult.FAILURE,
                message=f"You don't see any {obj_name.lower()} here.",
            )

        if "LIGHTBIT" not in obj_state.flags and "DEVICEBIT" not in obj_state.flags:
            return ActionResponse(
                result=ActionResult.FAILURE,
                message=f"You can't turn on the {obj_name.lower()}.",
            )

        if "ONBIT" in obj_state.flags:
            return ActionResponse(
                result=ActionResult.FAILURE,
                message=f"The {obj_name.lower()} is already on.",
            )

        obj_state.flags.add("ONBIT")
        return ActionResponse(
            result=ActionResult.SUCCESS,
            message=f"You turn on the {obj_name.lower()}.",
            state_changed=True,
        )

    def _do_turn_off(self, obj_name: str | None, _: str | None) -> ActionResponse:
        """Handle turning things off."""
        if not obj_name:
            return ActionResponse(
                result=ActionResult.INVALID,
                message="What do you want to turn off?",
            )

        obj_name = obj_name.upper()
        obj_state = self.world.get_object_state(obj_name)

        if not obj_state:
            return ActionResponse(
                result=ActionResult.FAILURE,
                message=f"You don't see any {obj_name.lower()} here.",
            )

        if "ONBIT" not in obj_state.flags:
            return ActionResponse(
                result=ActionResult.FAILURE,
                message=f"The {obj_name.lower()} isn't on.",
            )

        obj_state.flags.remove("ONBIT")
        return ActionResponse(
            result=ActionResult.SUCCESS,
            message=f"You turn off the {obj_name.lower()}.",
            state_changed=True,
        )

    def _do_read(self, obj_name: str | None, _: str | None) -> ActionResponse:
        """Handle reading things."""
        if not obj_name:
            return ActionResponse(
                result=ActionResult.INVALID,
                message="What do you want to read?",
            )

        obj_name = obj_name.upper()
        obj = self.world.get_object(obj_name)

        if not obj:
            return ActionResponse(
                result=ActionResult.FAILURE,
                message=f"You don't see any {obj_name.lower()} here.",
            )

        text = obj.get_property_value("TEXT")
        if not text:
            return ActionResponse(
                result=ActionResult.FAILURE,
                message=f"There's nothing to read on the {obj_name.lower()}.",
            )

        return ActionResponse(
            result=ActionResult.SUCCESS,
            message=text,
        )

    def _do_inventory(self, _: str | None, __: str | None) -> ActionResponse:
        """Handle inventory check."""
        return ActionResponse(
            result=ActionResult.SUCCESS,
            message=self.world.describe_inventory(),
        )

    def _do_wait(self, _: str | None, __: str | None) -> ActionResponse:
        """Handle waiting."""
        self.world.state.moves += 1
        return ActionResponse(
            result=ActionResult.SUCCESS,
            message="Time passes.",
            state_changed=True,
        )
