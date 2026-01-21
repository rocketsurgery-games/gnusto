"""
LLM integration for Gnusto.

Provides a thin wrapper around litellm for model-agnostic LLM calls with tool use.
This module handles the low-level details of communicating with language models,
while the agent module handles the higher-level game-playing logic.
"""

import json
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
