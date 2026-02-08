"""
LLM integration for Gnusto.

Provides a thin wrapper around litellm for model-agnostic LLM calls.
Supports structured JSON output for the agent's response schema.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Literal

import litellm


@dataclass
class LLMConfig:
    """Configuration for LLM calls."""

    model: str = "anthropic/claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_tokens: int = 2048

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create config from environment variables."""
        return cls(
            model=os.getenv("GRUE_LLM_MODEL", cls.model),
            temperature=float(os.getenv("GRUE_LLM_TEMPERATURE", cls.temperature)),
            max_tokens=int(os.getenv("GRUE_LLM_MAX_TOKENS", cls.max_tokens)),
        )


# =============================================================================
# Structured Response Schema
# =============================================================================

@dataclass
class ActionRequest:
    """A game action to execute."""
    tool: Literal["do_action", "move", "wait"]
    target: str | None = None  # For do_action
    verb: str | None = None    # For do_action
    args: list[str] = field(default_factory=list)  # For do_action
    direction: str | None = None  # For move


@dataclass
class ImageRequest:
    """An image to display."""
    path: str  # e.g., "/renders/terminal-room.png"
    alt: str = ""
    layout: Literal["inline", "float-left", "float-right", "background"] = "inline"
    size: Literal["small", "medium", "large", "full"] = "medium"


@dataclass
class AgentResponse:
    """Structured response from the LLM agent."""

    # Actions to execute (if any)
    actions: list[ActionRequest] = field(default_factory=list)

    # Narrative text to display (if any)
    narrative: str | None = None

    # Images to show (if any)
    images: list[ImageRequest] = field(default_factory=list)

    # Should we stop and wait for player input?
    # Set to True when something unexpected happens mid-sequence
    needs_player_input: bool = False

    # Raw response for debugging
    raw: Any = None


# JSON Schema for structured output
AGENT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "description": "Game actions to execute. Execute these in order.",
            "items": {
                "type": "object",
                "properties": {
                    "tool": {
                        "type": "string",
                        "enum": ["do_action", "move", "wait"],
                        "description": "The type of action"
                    },
                    "target": {
                        "type": "string",
                        "description": "For do_action: the object ID (e.g., @hacker, @door)"
                    },
                    "verb": {
                        "type": "string",
                        "description": "For do_action: the action verb (e.g., examine, take, ask)"
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "For do_action: additional arguments (object IDs)"
                    },
                    "direction": {
                        "type": "string",
                        "description": "For move: the direction (north, south, etc.)"
                    }
                },
                "required": ["tool"]
            }
        },
        "narrative": {
            "type": ["string", "null"],
            "description": "Narrative text describing what happened. Preserve dialogue verbatim. Use null if no narrative yet."
        },
        "images": {
            "type": "array",
            "description": "Images to display with the narrative.",
            "items": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Image path (e.g., /renders/terminal-room.png)"
                    },
                    "alt": {
                        "type": "string",
                        "description": "Alt text for the image"
                    },
                    "layout": {
                        "type": "string",
                        "enum": ["inline", "float-left", "float-right", "background"],
                        "description": "How to position the image"
                    },
                    "size": {
                        "type": "string",
                        "enum": ["small", "medium", "large", "full"],
                        "description": "Image size"
                    }
                },
                "required": ["path"]
            }
        },
        "needs_player_input": {
            "type": "boolean",
            "description": "Set to true to stop and ask the player what to do next (e.g., something unexpected happened)"
        }
    },
    "required": ["actions", "needs_player_input"]
}


# Legacy types for backwards compatibility
@dataclass
class ToolCall:
    """A tool call from the LLM (legacy)."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Response from an LLM call (legacy)."""
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None


class LLMClient:
    """Client for making LLM calls with tool support."""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig.from_env()

    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict | None = None,
        max_retries: int = 3,
    ) -> LLMResponse:
        """
        Send a chat request to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            tools: Optional list of tool definitions (OpenAI function calling format)
            tool_choice: Optional tool choice ("auto", "none", or specific tool)
            max_retries: Number of retries on transient errors (default 3)

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

        last_error = None
        for attempt in range(max_retries):
            try:
                response = litellm.completion(**kwargs)
                return self._parse_response(response)
            except Exception as e:
                last_error = e
                # Only retry on network-related errors
                error_str = str(e).lower()
                if any(x in error_str for x in ["connection", "timeout", "network", "http2", "disconnect"]):
                    import time
                    time.sleep(0.5 * (attempt + 1))  # Simple backoff
                    continue
                raise  # Non-network errors, don't retry

        raise last_error  # type: ignore

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

    def chat_structured(self, messages: list[dict[str, str]], max_retries: int = 3) -> AgentResponse:
        """
        Send a chat request expecting structured JSON output.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            max_retries: Number of retries on transient errors (default 3)

        Returns:
            AgentResponse parsed from JSON
        """
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_response",
                    "strict": True,
                    "schema": AGENT_RESPONSE_SCHEMA,
                }
            },
        }

        last_error = None
        for attempt in range(max_retries):
            try:
                response = litellm.completion(**kwargs)
                return self._parse_structured_response(response)
            except Exception as e:
                last_error = e
                # Only retry on network-related errors
                error_str = str(e).lower()
                if any(x in error_str for x in ["connection", "timeout", "network", "http2", "disconnect"]):
                    import time
                    time.sleep(0.5 * (attempt + 1))  # Simple backoff
                    continue
                raise  # Non-network errors, don't retry

        raise last_error  # type: ignore

    def _parse_structured_response(self, response: Any) -> AgentResponse:
        """Parse structured JSON response into AgentResponse."""
        message = response.choices[0].message
        content = message.content

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            # Fall back to empty response on parse error
            return AgentResponse(
                narrative=f"[Error parsing response: {e}]",
                needs_player_input=True,
                raw=response,
            )

        # Parse actions
        actions = []
        for action_data in data.get("actions", []):
            actions.append(ActionRequest(
                tool=action_data.get("tool", "wait"),
                target=action_data.get("target"),
                verb=action_data.get("verb"),
                args=action_data.get("args", []),
                direction=action_data.get("direction"),
            ))

        # Parse images (deduplicate by path)
        images = []
        seen_paths: set[str] = set()
        for image_data in data.get("images", []):
            path = image_data.get("path", "")
            if path and path not in seen_paths:
                seen_paths.add(path)
                images.append(ImageRequest(
                    path=path,
                    alt=image_data.get("alt", ""),
                    layout=image_data.get("layout", "inline"),
                    size=image_data.get("size", "medium"),
                ))

        # Handle narrative - treat "null" string as None (LLM sometimes does this)
        narrative = data.get("narrative")
        if narrative == "null":
            narrative = None

        return AgentResponse(
            actions=actions,
            narrative=narrative,
            images=images,
            needs_player_input=data.get("needs_player_input", False),
            raw=response,
        )


# =============================================================================
# Tool Definitions for Game Actions (Legacy)
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
