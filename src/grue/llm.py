"""
LLM integration for GRUE.

Provides a thin wrapper around litellm for model-agnostic LLM calls with tool use.
"""

import os
from dataclasses import dataclass, field
from typing import Any

import litellm


@dataclass
class LLMConfig:
    """Configuration for LLM calls."""

    model: str = "anthropic/claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_tokens: int = 1024

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create config from environment variables."""
        return cls(
            model=os.getenv("GRUE_LLM_MODEL", cls.model),
            temperature=float(os.getenv("GRUE_LLM_TEMPERATURE", cls.temperature)),
            max_tokens=int(os.getenv("GRUE_LLM_MAX_TOKENS", cls.max_tokens)),
        )


@dataclass
class ToolCall:
    """A tool call from the LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Response from an LLM call."""

    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None  # Original response for debugging


class LLMClient:
    """Client for making LLM calls with tool support."""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig.from_env()

    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict | None = None,
    ) -> LLMResponse:
        """
        Send a chat request to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            tools: Optional list of tool definitions (OpenAI function calling format)
            tool_choice: Optional tool choice ("auto", "none", or specific tool)

        Returns:
            LLMResponse with content and/or tool calls
        """
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        if tools:
            kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice

        response = litellm.completion(**kwargs)
        return self._parse_response(response)

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse litellm response into our format."""
        message = response.choices[0].message

        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                import json

                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                )

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            raw=response,
        )


# =============================================================================
# Tool Definitions for Game Actions
# =============================================================================

GAME_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "do_action",
            "description": "Perform an action on an object in the game world. Use this for all interactions with objects, items, characters, and the environment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "The object ID to act on (e.g., '@door', '@key', '@hacker'). Must be a visible or held object.",
                    },
                    "verb": {
                        "type": "string",
                        "description": "The action to perform (e.g., 'open', 'take', 'examine', 'give', 'unlock'). Check the object's available behaviors.",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional arguments for the action (e.g., the key to unlock with, the item to give). Use object IDs.",
                    },
                },
                "required": ["target", "verb"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move",
            "description": "Move in a direction to another room. Use the available exits shown in the game state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "description": "The direction to move (e.g., 'north', 'south', 'east', 'west', 'up', 'down', 'in', 'out').",
                    },
                },
                "required": ["direction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wait",
            "description": "Wait and let time pass. Use this when you want to wait for something to happen or pass a turn.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


def get_game_tools() -> list[dict[str, Any]]:
    """Get the list of game action tools for LLM tool calling."""
    return GAME_TOOLS


# =============================================================================
# Game State Serialization for LLM Context
# =============================================================================

@dataclass
class ObjectInfo:
    """Information about a game object for LLM context."""

    id: str
    description: str
    behaviors: list[str] = field(default_factory=list)  # Available verbs
    properties: dict[str, Any] = field(default_factory=dict)  # Visible properties


@dataclass
class GameState:
    """Current game state for LLM context."""

    room: str
    room_description: str
    visible_objects: list[ObjectInfo]
    inventory: list[ObjectInfo]
    exits: dict[str, str]
    vehicle: tuple[str, str] | None = None  # (vehicle_name, preposition) if in vehicle

    def to_context_string(self) -> str:
        """Format game state as a string for LLM context."""
        lines = []

        # Location
        lines.append(f"## Current Location: {self.room}")
        if self.vehicle:
            lines.append(f"(You are {self.vehicle[1]} the {self.vehicle[0]})")
        lines.append("")
        lines.append(self.room_description)
        lines.append("")

        # Exits
        if self.exits:
            exits_str = ", ".join(f"{d} -> {dest}" for d, dest in self.exits.items())
            lines.append(f"**Exits:** {exits_str}")
        else:
            lines.append("**Exits:** none")
        lines.append("")

        # Visible objects
        if self.visible_objects:
            lines.append("**Visible objects:**")
            for obj in self.visible_objects:
                behaviors_str = ", ".join(obj.behaviors) if obj.behaviors else "none"
                lines.append(f"- {obj.id}: {obj.description} [actions: {behaviors_str}]")
        else:
            lines.append("**Visible objects:** none")
        lines.append("")

        # Inventory
        if self.inventory:
            lines.append("**Inventory:**")
            for obj in self.inventory:
                lines.append(f"- {obj.id}: {obj.description}")
        else:
            lines.append("**Inventory:** empty")

        return "\n".join(lines)


def get_game_state(runtime: Any) -> GameState:
    """
    Extract current game state from runtime for LLM context.

    Args:
        runtime: GrueRuntime instance

    Returns:
        GameState with current room, objects, inventory, exits
    """
    room = runtime.get_player_room()
    room_desc = runtime.get_room_description()
    exits = runtime.get_exits()
    vehicle = runtime.get_player_vehicle()

    # Get visible objects with their behaviors
    visible_names = runtime.get_visible_objects()
    visible_objects = []
    for name in visible_names:
        if name not in runtime.get_inventory():
            obj_info = _get_object_info(runtime, name)
            visible_objects.append(obj_info)

    # Get inventory items
    inv_names = runtime.get_inventory()
    inventory = [_get_object_info(runtime, name) for name in inv_names]

    return GameState(
        room=room,
        room_description=room_desc,
        visible_objects=visible_objects,
        inventory=inventory,
        exits=exits,
        vehicle=vehicle,
    )


def _format_behavior(verb: str, params: list[str]) -> str:
    """Format a behavior with its parameters for LLM context.

    Examples:
        give, [item] -> "give <item>"
        take, [] -> "take"
        unlock, [key] -> "unlock <key>"
    """
    if params:
        param_str = " ".join(f"<{p}>" for p in params)
        return f"{verb} {param_str}"
    return verb


def _get_object_info(runtime: Any, obj_name: str) -> ObjectInfo:
    """Get object info including available behaviors."""
    desc = runtime.get_object_description(obj_name)

    # Get behaviors from world definition
    # Track verb -> formatted string (with params)
    behavior_map: dict[str, str] = {}
    if obj_name in runtime.world.objects:
        obj_def = runtime.world.objects[obj_name]
        for b in obj_def.behaviors:
            # Skip internal behaviors (on-enter, describe, etc.)
            if not b.verb.startswith("on-") and b.verb not in ("describe", "through"):
                behavior_map[b.verb] = _format_behavior(b.verb, b.params)

    # Also check defaults for common behaviors
    # Objects can respond to default behaviors even without explicit definition
    for verb in runtime.world.defaults:
        if verb not in behavior_map:
            # Defaults have no params (they operate on just the object)
            behavior_map[verb] = verb

    return ObjectInfo(
        id=obj_name,
        description=desc,
        behaviors=sorted(behavior_map.values()),
    )
