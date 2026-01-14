"""
LLM Interface for ZIL Game Engine

Provides the tool interface that an LLM uses to understand
and interact with the game world.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from .world import World
from .actions import ActionExecutor, ActionResult


@dataclass
class GameContext:
    """
    Complete context for LLM decision-making.

    This is what gets sent to the LLM along with player input.
    """

    # Current location
    room_name: str
    room_description: str
    room_long_description: str | None

    # What's here
    objects_here: list[dict[str, Any]]

    # Where can we go
    exits: list[dict[str, Any]]

    # What we're carrying
    inventory: list[str]

    # What actions are available right now
    valid_actions: list[dict[str, Any]]

    # Game state
    score: int
    moves: int

    def to_prompt(self) -> str:
        """Format as a prompt section for the LLM."""
        lines = []

        lines.append("## Current Location")
        lines.append(f"**{self.room_name}**")
        if self.room_long_description:
            lines.append(self.room_long_description)
        elif self.room_description:
            lines.append(self.room_description)

        if self.objects_here:
            lines.append("\n## Objects Here")
            for obj in self.objects_here:
                desc = obj.get("description", obj["name"])
                flags = obj.get("flags", [])
                props = []
                if obj.get("takeable"):
                    props.append("can take")
                if "OPENBIT" in flags:
                    props.append("open")
                if "ONBIT" in flags:
                    props.append("on")
                prop_str = f" ({', '.join(props)})" if props else ""
                lines.append(f"- {desc}{prop_str}")

        if self.exits:
            lines.append("\n## Exits")
            for exit in self.exits:
                status = "accessible" if exit["accessible"] else "blocked"
                lines.append(f"- {exit['direction']}: {exit['destination']} ({status})")

        if self.inventory:
            lines.append("\n## Inventory")
            for item in self.inventory:
                lines.append(f"- {item}")
        else:
            lines.append("\n## Inventory")
            lines.append("Empty-handed")

        lines.append(f"\n## Game State")
        lines.append(f"Score: {self.score}, Moves: {self.moves}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "room": {
                "name": self.room_name,
                "description": self.room_description,
                "long_description": self.room_long_description,
            },
            "objects_here": self.objects_here,
            "exits": self.exits,
            "inventory": self.inventory,
            "valid_actions": self.valid_actions,
            "score": self.score,
            "moves": self.moves,
        }


@dataclass
class LLMResponse:
    """
    Structure for LLM's response to player input.
    """

    # Did the LLM identify a game action?
    has_action: bool

    # If has_action, what action?
    action: str | None = None
    target: str | None = None
    indirect_target: str | None = None

    # LLM's response text (either action result embellishment or flavor response)
    response_text: str = ""

    # Confidence in the action selection (0-1)
    confidence: float = 1.0

    # Reasoning for the decision
    reasoning: str = ""


class LLMGameInterface:
    """
    Interface between the LLM and the game engine.

    Provides tools for:
    - Querying current game state
    - Listing valid actions
    - Executing actions
    - Generating context for decision-making
    """

    def __init__(self, world: World):
        self.world = world
        self.executor = ActionExecutor(world)

    def get_context(self) -> GameContext:
        """
        Get the current game context for LLM decision-making.
        """
        room = self.world.get_current_room()

        # Get room info
        room_name = self.world.state.current_room
        room_desc = ""
        room_ldesc = None
        if room:
            room_desc = room.get_property_value("DESC", room_name)
            room_ldesc = room.get_property_value("LDESC")

        # Get objects
        objects_here = []
        for obj_name in self.world.get_objects_in_room():
            obj = self.world.get_object(obj_name)
            obj_state = self.world.get_object_state(obj_name)
            if obj and obj_state:
                objects_here.append({
                    "name": obj_name,
                    "description": obj.get_property_value("DESC", obj_name),
                    "flags": list(obj_state.flags),
                    "takeable": "TAKEBIT" in obj_state.flags,
                })

        # Get exits
        exits = []
        room_exits = self.world.get_room_exits()
        for direction, info in room_exits.items():
            can_go, dest = self.world.can_go(direction)
            exits.append({
                "direction": direction.lower(),
                "destination": dest,
                "accessible": can_go,
            })

        # Get valid actions
        valid_actions = self.executor.get_valid_actions()

        return GameContext(
            room_name=room_name,
            room_description=room_desc,
            room_long_description=room_ldesc,
            objects_here=objects_here,
            exits=exits,
            inventory=list(self.world.state.inventory),
            valid_actions=valid_actions,
            score=self.world.state.score,
            moves=self.world.state.moves,
        )

    def get_valid_actions_summary(self) -> str:
        """
        Get a human-readable summary of valid actions.
        """
        valid = self.executor.get_valid_actions()
        lines = ["## Valid Actions"]

        for action in valid:
            name = action["action"]
            desc = action["description"]
            targets = action.get("valid_targets", [])

            if targets:
                lines.append(f"- **{name}** ({desc}): {', '.join(targets)}")
            else:
                lines.append(f"- **{name}** ({desc})")

        return "\n".join(lines)

    def execute_action(
        self,
        action: str,
        target: str | None = None,
        indirect_target: str | None = None
    ) -> dict[str, Any]:
        """
        Execute an action and return the result.

        Returns a dict suitable for LLM consumption.
        """
        result = self.executor.execute(action, target, indirect_target)

        return {
            "success": result.result == ActionResult.SUCCESS,
            "result": result.result.value,
            "message": result.message,
            "state_changed": result.state_changed,
            "details": result.details,
        }

    def build_prompt(self, player_input: str) -> str:
        """
        Build the complete prompt for the LLM to process player input.

        This is the key interface - it gives the LLM everything it needs
        to decide whether to execute an action or generate a flavor response.
        """
        context = self.get_context()

        prompt = f"""You are playing an interactive fiction game. Your job is to interpret the player's input and either:
1. Map it to a valid game action (if one applies)
2. Generate an atmospheric response (if no action applies)

{context.to_prompt()}

{self.get_valid_actions_summary()}

## Player Input
"{player_input}"

## Your Task
Analyze the player's input. If it maps to one of the valid actions above, respond with:
```json
{{
    "has_action": true,
    "action": "<action_name>",
    "target": "<target_object_or_direction>",
    "reasoning": "<why this action fits>"
}}
```

If the input doesn't map to a valid action (it's a question, an impossible request, or just flavor), respond with:
```json
{{
    "has_action": false,
    "response_text": "<your atmospheric/flavor response>",
    "reasoning": "<why no action applies>"
}}
```

Be generous in interpreting player intent - "grab the lamp" should map to "take lamp", "head north" to "go north", etc.
For ambiguous inputs where multiple actions might apply, pick the most likely one.
For impossible or nonsensical requests, generate a brief, in-character response that doesn't change game state.
"""
        return prompt

    def process_llm_response(self, response_json: str) -> tuple[str, bool]:
        """
        Process the LLM's JSON response and execute any action.

        Returns (message_to_player, state_changed)
        """
        try:
            response = json.loads(response_json)
        except json.JSONDecodeError:
            return "I don't understand that.", False

        if response.get("has_action"):
            action = response.get("action", "")
            target = response.get("target")
            indirect = response.get("indirect_target")

            result = self.execute_action(action, target, indirect)
            return result["message"], result["state_changed"]
        else:
            # Flavor response from LLM
            return response.get("response_text", "Nothing happens."), False


def create_test_cases() -> list[dict[str, Any]]:
    """
    Generate test cases for evaluating LLM action selection.

    Each test case has:
    - input: What the player types
    - expected_action: What action should be selected (or None for flavor)
    - expected_target: What target (if applicable)
    - category: Type of test case

    NOTE: These test cases are designed for the Terminal Room in Lurking Horror,
    which contains: hacker, chair, pc. Exits: south, out.
    """
    return [
        # Clear action matches (using objects that exist in Terminal Room)
        {"input": "go south", "expected_action": "go", "expected_target": "south", "category": "clear_match"},
        {"input": "take the chair", "expected_action": "take", "expected_target": "chair", "category": "clear_match"},
        {"input": "look around", "expected_action": "look", "expected_target": None, "category": "clear_match"},
        {"input": "examine the pc", "expected_action": "examine", "expected_target": "pc", "category": "clear_match"},
        {"input": "i", "expected_action": "inventory", "expected_target": None, "category": "clear_match"},
        {"input": "look at the hacker", "expected_action": "examine", "expected_target": "hacker", "category": "clear_match"},

        # Synonym handling (using existing objects)
        {"input": "grab the chair", "expected_action": "take", "expected_target": "chair", "category": "synonym"},
        {"input": "head south", "expected_action": "go", "expected_target": "south", "category": "synonym"},
        {"input": "inspect the computer", "expected_action": "examine", "expected_target": "pc", "category": "synonym"},
        {"input": "check out that person", "expected_action": "examine", "expected_target": "hacker", "category": "synonym"},

        # Natural language variations
        {"input": "I want to pick up that chair", "expected_action": "take", "expected_target": "chair", "category": "natural"},
        {"input": "let me see what's in my pockets", "expected_action": "inventory", "expected_target": None, "category": "natural"},
        {"input": "what's that computer over there?", "expected_action": "examine", "expected_target": "pc", "category": "natural"},
        {"input": "who is that person?", "expected_action": "examine", "expected_target": "hacker", "category": "natural"},
        {"input": "get out of here", "expected_action": "go", "expected_target": "out", "category": "natural"},

        # Ambiguous (should pick most likely)
        {"input": "the chair", "expected_action": "examine", "expected_target": "chair", "category": "ambiguous"},
        {"input": "computer", "expected_action": "examine", "expected_target": "pc", "category": "ambiguous"},

        # Flavor/no action - social or impossible
        {"input": "hello", "expected_action": None, "expected_target": None, "category": "flavor"},
        {"input": "what is the meaning of life?", "expected_action": None, "expected_target": None, "category": "flavor"},
        {"input": "talk to the hacker", "expected_action": None, "expected_target": None, "category": "flavor"},
        {"input": "sing a song", "expected_action": None, "expected_target": None, "category": "flavor"},
        {"input": "why am I here?", "expected_action": None, "expected_target": None, "category": "flavor"},

        # Impossible requests (object doesn't exist or action impossible)
        {"input": "fly to the moon", "expected_action": None, "expected_target": None, "category": "impossible"},
        {"input": "eat the wall", "expected_action": None, "expected_target": None, "category": "impossible"},
        {"input": "teleport home", "expected_action": None, "expected_target": None, "category": "impossible"},
        {"input": "take the lamp", "expected_action": None, "expected_target": None, "category": "impossible"},
        {"input": "go north", "expected_action": None, "expected_target": None, "category": "impossible"},
    ]
