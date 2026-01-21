"""
Agent-driven game player for Gnusto.

This module provides the agent that plays GRUE games. It interprets natural
language input, translates it to game actions via tool calling, and renders
results. The default mode uses plain text for automation compatibility.
"""

import json
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

from grue.parser import load_grue
from grue.repl import ActionBlocked, ActionDone, ActionError, ReplEvaluator
from grue.runtime import ActionResult, GrueRuntime
from grue.save import save_game, load_game, list_saves
from grue.sexpr import Keyword, SList, Symbol, parse, to_string

from .llm import LLMClient, LLMConfig, LLMResponse, ToolCall, get_game_tools
from .state import GameState, ObjectInfo, get_game_state


SYSTEM_PROMPT = """\
You are a command interpreter for an interactive fiction game. Your ONLY role is to:

1. Parse the player's natural language into game actions
2. Call the appropriate tools
3. Report the results exactly as returned

Tools:
- do_action: Interact with objects (examine, take, open, etc.)
- move: Navigate (go north, enter building, etc.)
- wait: Pass time

Rules:
- Use object IDs exactly as shown (e.g., @door, @key)
- Match player intent to available actions on visible objects
- If the command is unclear: ask for clarification in one short sentence
- If action is impossible: state why briefly

CRITICAL: Do NOT add narrative, descriptions, atmosphere, or suggestions.
The game provides all narrative text through tool results.
Your final response should be minimal - just acknowledge completion or report errors.
"""


def render_game_state(state: GameState, debug: bool = False) -> None:
    """Render game state as plain text.

    Args:
        state: Current game state
        debug: If True, use IDs instead of descriptions
    """
    # Room header
    print(f"\n=== {state.room_name} ===")
    if state.vehicle:
        print(f"(You are {state.vehicle[1]} the {state.vehicle[0]})")
    print()

    # Room description
    print(state.room_description)

    # Object listings (visually separated from room description)
    objects_with_fdesc = [obj for obj in state.visible_objects if obj.fdesc]
    if objects_with_fdesc:
        print()
        for obj in objects_with_fdesc:
            print(obj.fdesc)

    # Exits - use nearby_rooms for player-friendly display, exits for debug
    if debug:
        if state.exits:
            exits_str = ", ".join(f"{d} -> {dest}" for d, dest in state.exits.items())
            print(f"\nExits: {exits_str}")
    else:
        if state.nearby_rooms:
            nearby_str = ", ".join(r.description for r in state.nearby_rooms)
            print(f"\nNearby: {nearby_str}")

    # Inventory
    if state.inventory:
        if debug:
            inv_items = ", ".join(obj.id for obj in state.inventory)
        else:
            inv_items = ", ".join(obj.description for obj in state.inventory)
        print(f"Carrying: {inv_items}")
    print()


def _debug_log(title: str, content: str, style: str = "dim") -> None:
    """Print debug information as plain text."""
    print(f"--- {title} ---")
    print(content)
    print()


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.

    Uses a simple heuristic: ~4 characters per token on average for English.
    This is a rough estimate - for precise counting, use tiktoken.
    """
    return len(text) // 4 + 1


def estimate_message_tokens(message: dict[str, Any]) -> int:
    """Estimate tokens for a single message dict."""
    tokens = 4  # Message overhead (role, structure)
    content = message.get("content", "")
    if content:
        tokens += estimate_tokens(content)
    # Tool calls add overhead
    if "tool_calls" in message:
        tokens += len(message["tool_calls"]) * 20  # Rough estimate per tool call
    return tokens


@dataclass
class TurnRecord:
    """Compact record of a player turn for history."""

    room: str
    player_command: str
    actions: list[str]  # e.g., ["examine @carton", "go south"]
    results: list[str]  # e.g., ["Opened.", "Blocked: locked"]
    narrative: str  # LLM's final response

    def to_summary(self) -> str:
        """Generate a multi-line summary of this turn with results."""
        lines = []
        # Header: room and command
        actions_str = ", ".join(self.actions) if self.actions else "no actions"
        lines.append(f"[{self.room}] {self.player_command} → {actions_str}")
        # Results (indented, one per action where available)
        for i, action in enumerate(self.actions):
            result = self.results[i] if i < len(self.results) else ""
            if result and result != "Done.":
                lines.append(f"  → {result}")
        return "\n".join(lines)

    def estimate_tokens(self) -> int:
        """Estimate token count for this turn when rendered to messages."""
        # User message: "[Previous turn in {room}]\nPlayer: {command}"
        user_tokens = estimate_tokens(f"[Previous turn in {self.room}]\nPlayer: {self.player_command}")
        # Results add to context
        results_tokens = sum(estimate_tokens(r) for r in self.results if r and r != "Done.")
        # Assistant message: narrative
        assistant_tokens = estimate_tokens(self.narrative)
        return user_tokens + results_tokens + assistant_tokens + 8  # +8 for message overhead


@dataclass
class GameSession:
    """An agent-driven game session."""

    runtime: GrueRuntime
    evaluator: ReplEvaluator
    llm: LLMClient
    turn_history: list[TurnRecord] = field(default_factory=list)
    debug: bool = False
    max_history_turns: int = 20  # Keep last N turns in full detail

    @classmethod
    def from_game_file(
        cls,
        game_path: str,
        llm_config: LLMConfig | None = None,
        debug: bool = False,
    ) -> "GameSession":
        """Create a new game session from a game file."""
        world = load_grue(game_path)
        runtime = GrueRuntime(world)
        evaluator = ReplEvaluator(runtime)
        llm = LLMClient(llm_config)

        session = cls(
            runtime=runtime,
            evaluator=evaluator,
            llm=llm,
            debug=debug,
        )
        return session

    # Tiered history settings
    recent_turns_full: int = 5  # Last N turns get full narrative
    medium_turns_brief: int = 15  # Next N turns get brief narrative

    def _build_messages(self, current_state: GameState, player_command: str) -> list[dict[str, Any]]:
        """
        Build fresh message list for LLM from history + current state.

        Structure:
        1. System prompt
        2. Turn history (tiered detail level)
        3. Current game state + player command

        History tiers:
        - Recent (last 5): Full narrative
        - Medium (5-20): First sentence of narrative
        - Old (20+): One-line summary only
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        # Get turns to include (with position for tiering)
        turns_to_include = self.turn_history[-self.max_history_turns:]
        num_turns = len(turns_to_include)

        for i, turn in enumerate(turns_to_include):
            # Calculate how "old" this turn is (0 = most recent)
            age = num_turns - 1 - i

            if age < self.recent_turns_full:
                # Recent: full detail with results
                user_lines = [f"[Previous turn in {turn.room}]", f"Player: {turn.player_command}"]
                # Include action results (skip "Done." noise)
                for j, action in enumerate(turn.actions):
                    result = turn.results[j] if j < len(turn.results) else ""
                    if result and result != "Done.":
                        user_lines.append(f"  {action}: {result}")
                    else:
                        user_lines.append(f"  {action}")
                user_content = "\n".join(user_lines)
                assistant_content = turn.narrative
            elif age < self.recent_turns_full + self.medium_turns_brief:
                # Medium: abbreviated - command with results, brief narrative
                user_lines = [f"[Turn in {turn.room}] {turn.player_command}"]
                for j, action in enumerate(turn.actions):
                    result = turn.results[j] if j < len(turn.results) else ""
                    if result and result != "Done.":
                        user_lines.append(f"  → {result}")
                user_content = "\n".join(user_lines)
                # Take first sentence or first 100 chars of narrative
                narrative = turn.narrative
                if ". " in narrative:
                    assistant_content = narrative[:narrative.index(". ") + 1]
                elif len(narrative) > 100:
                    assistant_content = narrative[:100] + "..."
                else:
                    assistant_content = narrative
            else:
                # Old: summary only (single message, no assistant response)
                messages.append({
                    "role": "user",
                    "content": f"[Earlier: {turn.to_summary()}]"
                })
                continue

            messages.append({"role": "user", "content": user_content})
            messages.append({"role": "assistant", "content": assistant_content})

        # Current turn: fresh state + player command
        state_context = current_state.to_context_string()
        messages.append({
            "role": "user",
            "content": f"{state_context}\n\n---\n\nPlayer command: {player_command}"
        })

        return messages

    def get_state(self) -> GameState:
        """Get current game state."""
        return get_game_state(self.runtime)

    def estimate_context_tokens(self) -> dict[str, int]:
        """
        Estimate current context token usage.

        Returns dict with breakdown by tier:
        - system_prompt: Tokens in system prompt
        - history_recent: Full-detail recent turns
        - history_medium: Abbreviated medium turns
        - history_old: Summary-only old turns
        - state_estimate: Estimated tokens for typical game state
        - total: Sum of all components
        """
        system_tokens = estimate_tokens(SYSTEM_PROMPT)

        turns = self.turn_history[-self.max_history_turns:]
        num_turns = len(turns)

        recent_tokens = 0
        medium_tokens = 0
        old_tokens = 0

        for i, turn in enumerate(turns):
            age = num_turns - 1 - i

            if age < self.recent_turns_full:
                # Full tokens
                recent_tokens += turn.estimate_tokens()
            elif age < self.recent_turns_full + self.medium_turns_brief:
                # Abbreviated: ~half tokens
                medium_tokens += turn.estimate_tokens() // 2
            else:
                # Summary only: ~20 tokens
                old_tokens += 20

        # Estimate typical game state size (varies by room)
        state_estimate = 500  # Rough average

        history_total = recent_tokens + medium_tokens + old_tokens

        return {
            "system_prompt": system_tokens,
            "history_recent": recent_tokens,
            "history_medium": medium_tokens,
            "history_old": old_tokens,
            "history_total": history_total,
            "history_turns": num_turns,
            "state_estimate": state_estimate,
            "total": system_tokens + history_total + state_estimate,
        }

    def get_state_context(self) -> str:
        """Get current game state as context string for agent."""
        return self.get_state().to_context_string()

    def process_input(
        self,
        user_input: str,
        max_iterations: int = 10,
        on_action: "Callable[[str], None] | None" = None,
    ) -> tuple[str, list[str]]:
        """
        Process natural language input and return response.

        Uses an agentic loop: executes tool calls, feeds results back to the LLM,
        and repeats until the LLM responds without tool calls or max iterations.

        Context management:
        - Fresh game state is injected at each LLM call (not persisted)
        - Only compact TurnRecords are kept in history
        - Working messages during the loop are ephemeral

        Args:
            user_input: Natural language command from player
            max_iterations: Maximum number of LLM calls (default 10)
            on_action: Optional callback for streaming action results

        Returns:
            Tuple of (response text, action results list)
        """
        # Get initial state and build base messages from history
        initial_state = self.get_state()
        initial_room = initial_state.room

        if self.debug:
            _debug_log("LLM Context (game state)", self._format_state_debug(initial_state), style="cyan")

        # Build fresh messages: history + current state + command
        working_messages = self._build_messages(initial_state, user_input)

        all_results: list[str] = []  # Results returned to caller
        all_actions: list[str] = []  # Action summaries for TurnRecord
        all_action_results: list[str] = []  # Results paired with actions for TurnRecord
        final_response_text = ""
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            if self.debug and iteration > 1:
                _debug_log(f"Agentic Loop Iteration {iteration}", "", style="blue")

            # Get agent response with tools
            try:
                response = self.llm.chat(
                    messages=working_messages,
                    tools=get_game_tools(),
                    tool_choice="auto",
                )
            except Exception as e:
                error_msg = str(e)
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                return f"[LLM error: {error_msg}. Please try again.]", []

            # If no tool calls, we're done - LLM is just responding
            if not response.tool_calls:
                final_response_text = response.content or ""
                break

            # Process tool calls
            iteration_results: list[tuple[str, str]] = []  # (tool_call_id, result)
            for tool_call in response.tool_calls:
                if self.debug:
                    args_str = json.dumps(tool_call.arguments, indent=2)
                    _debug_log(
                        f"Agent Tool Call: {tool_call.name}",
                        args_str,
                        style="magenta",
                    )

                # Stream action description before executing
                if on_action:
                    action_desc = self._describe_action(tool_call)
                    on_action(action_desc)

                result = self._execute_tool(tool_call)
                iteration_results.append((tool_call.id, result))
                all_results.append(result)

                # Stream result if callback provided (skip generic "Done.")
                if on_action and result and result != "Done.":
                    on_action(result)

                # Track action and result for history
                action_summary = self._summarize_tool_call(tool_call)
                all_actions.append(action_summary)
                all_action_results.append(result)

                if self.debug:
                    _debug_log("Tool Result", result, style="green")

            # Add assistant message with tool calls to working messages
            assistant_msg = self._build_assistant_tool_message(response)
            working_messages.append(assistant_msg)

            # Add tool result messages
            for tool_call_id, result in iteration_results:
                tool_msg = {"role": "tool", "tool_call_id": tool_call_id, "content": result}
                working_messages.append(tool_msg)

            # Get updated game state for next iteration
            state = self.get_state()
            if self.debug:
                _debug_log("LLM Context (updated state)", self._format_state_debug(state), style="cyan")

            # Add fresh state update for next iteration (ephemeral)
            state_context = state.to_context_string()
            state_update = f"[Game state after actions:]\n{state_context}"
            working_messages.append({"role": "user", "content": state_update})

        else:
            # Hit max iterations
            if self.debug:
                _debug_log("Max Iterations", f"Stopped after {max_iterations} iterations", style="red")
            final_response_text = response.content or ""

        # Record this turn in history (compact form)
        turn_record = TurnRecord(
            room=initial_room,
            player_command=user_input,
            actions=all_actions,
            results=all_action_results,
            narrative=final_response_text,
        )
        self.turn_history.append(turn_record)

        if self.debug:
            _debug_log("Turn Record", turn_record.to_summary(), style="blue")

        return final_response_text, all_results

    def _summarize_tool_call(self, tool_call: ToolCall) -> str:
        """Generate a compact summary of a tool call for history."""
        name = tool_call.name
        args = tool_call.arguments

        if name == "do_action":
            target = args.get("target", "?")
            verb = args.get("verb", "?")
            action_args = args.get("args", [])
            if action_args:
                return f"{verb} {target} with {', '.join(str(a) for a in action_args)}"
            return f"{verb} {target}"
        elif name == "move":
            return f"go {args.get('direction', '?')}"
        elif name == "wait":
            return "wait"
        else:
            return f"{name}(...)"

    def _describe_action(self, tool_call: ToolCall) -> str:
        """Generate a natural language description of what the agent is doing."""
        name = tool_call.name
        args = tool_call.arguments

        if name == "do_action":
            target = args.get("target", "?")
            verb = args.get("verb", "?")
            action_args = args.get("args", [])
            # Convert verb to present participle
            if verb.endswith("e"):
                verb_ing = verb[:-1] + "ing"
            else:
                verb_ing = verb + "ing"
            verb_ing = verb_ing.capitalize()
            if action_args:
                return f"{verb_ing} {target} with {', '.join(str(a) for a in action_args)}..."
            return f"{verb_ing} {target}..."
        elif name == "move":
            direction = args.get("direction", "?")
            return f"Going {direction}..."
        elif name == "wait":
            return "Waiting..."
        else:
            return f"{name}..."

    def _build_assistant_tool_message(self, response: "LLMResponse") -> dict[str, Any]:
        """Build an assistant message with tool calls for the conversation history."""
        msg: dict[str, Any] = {"role": "assistant"}
        if response.content:
            msg["content"] = response.content
        if response.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in response.tool_calls
            ]
        return msg

    def _execute_tool(self, tool_call: ToolCall) -> str:
        """Execute a tool call and return result string."""
        name = tool_call.name
        args = tool_call.arguments

        if name == "do_action":
            # Normalize args to list - LLM sometimes returns string instead of array
            action_args = args.get("args", [])
            if isinstance(action_args, str):
                action_args = [action_args]
            return self._do_action(
                target=args.get("target", ""),
                verb=args.get("verb", ""),
                action_args=action_args,
            )
        elif name == "move":
            return self._move(args.get("direction", ""))
        elif name == "wait":
            return self._wait()
        else:
            return f"Unknown tool: {name}"

    def _do_action(self, target: str, verb: str, action_args: list[str]) -> str:
        """Execute a do action."""
        # Build S-expression: (do @target :verb arg1 arg2 ...)
        items = [Symbol("do"), Symbol(target), Keyword(verb)]
        for arg in action_args:
            items.append(Symbol(arg))

        expr = SList(items)
        return self._eval_and_format(expr)

    def _move(self, direction: str) -> str:
        """Execute a move action."""
        expr = SList([Symbol("go"), Symbol(direction)])
        return self._eval_and_format(expr)

    def _wait(self) -> str:
        """Execute a wait action."""
        expr = SList([Symbol("wait")])
        return self._eval_and_format(expr)

    def _eval_and_format(self, expr: SList) -> str:
        """Evaluate expression and format result, with optional debug output."""
        expr_str = to_string(expr)

        if self.debug:
            _debug_log("Grue Input", expr_str, style="yellow")

        result = self.evaluator.eval(expr)

        if self.debug:
            result_str = self._format_result_debug(result)
            _debug_log("Grue Output", result_str, style="green")

        # Process turn-based events after action (like repl does)
        event_results = self.runtime.process_events()
        if self.debug and event_results:
            for event_result in event_results:
                _debug_log("Event Fired", self._format_result_debug(event_result), style="cyan")

        # Combine action result with any event descriptions
        parts = [self._format_action_result(result)]
        for event_result in event_results:
            event_text = self._format_action_result(event_result)
            if event_text and event_text != "Done.":
                parts.append(event_text)

        return " ".join(parts)

    def _format_result_debug(self, result: Any) -> str:
        """Format a result for debug display."""
        if isinstance(result, ActionDone):
            parts = [f"ActionDone(message={result.message!r}"]
            if result.context:
                parts.append(f"  context={result.context!r}")
            if result.effects:
                parts.append(f"  effects={result.effects!r}")
            return "\n".join(parts) + ")"
        elif isinstance(result, ActionBlocked):
            return f"ActionBlocked(reason={result.reason!r}, message={result.message!r})"
        elif isinstance(result, ActionError):
            return f"ActionError(message={result.message!r})"
        elif isinstance(result, ActionResult):
            parts = [f"ActionResult(outcome={result.outcome!r}"]
            if result.context:
                parts.append(f"  context={result.context!r}")
            if result.effects_applied:
                parts.append(f"  effects={result.effects_applied!r}")
            return "\n".join(parts) + ")"
        else:
            return repr(result)

    def _format_state_debug(self, state: GameState) -> str:
        """Format game state for debug display - shows exactly what LLM sees."""
        return state.to_context_string()

    def format_debug_context(self) -> str:
        """Format full LLM context for debug display (history + current state)."""
        lines = []

        # Turn history summary
        lines.append("## Turn History")
        if not self.turn_history:
            lines.append("(no turns yet)")
        else:
            num_turns = len(self.turn_history)
            turns_shown = min(num_turns, self.max_history_turns)
            lines.append(f"({num_turns} turns, showing last {turns_shown})")
            lines.append("")

            # Show turns with tier indicators
            turns_to_show = self.turn_history[-self.max_history_turns:]
            for i, turn in enumerate(turns_to_show):
                age = len(turns_to_show) - 1 - i
                if age < self.recent_turns_full:
                    tier = "FULL"
                elif age < self.recent_turns_full + self.medium_turns_brief:
                    tier = "BRIEF"
                else:
                    tier = "SUMMARY"

                lines.append(f"[{tier}] {turn.to_summary()}")
        lines.append("")

        # Current state
        lines.append("## Current Game State")
        state = self.get_state()
        lines.append(state.to_context_string())

        return "\n".join(lines)

    def _format_action_result(self, result: Any) -> str:
        """Format an action result for display."""
        if isinstance(result, ActionDone):
            parts = [result.message] if result.message else []
            for key, value in result.context:
                # Extract user-facing context values
                if key in ("description", "message"):
                    parts.append(str(value))
            return " ".join(parts) if parts else "Done."
        elif isinstance(result, ActionBlocked):
            return f"Blocked: {result.message}"
        elif isinstance(result, ActionError):
            return f"Error: {result.message}"
        elif isinstance(result, ActionResult):
            # Runtime ActionResult (from events)
            parts = []
            for key, value in result.context:
                if key in ("description", "message"):
                    parts.append(str(value))
            return " ".join(parts) if parts else ""
        else:
            return str(result)


def _handle_slash_command(session: "GameSession", command: str) -> bool:
    """Handle slash commands. Returns True if command was handled."""
    parts = command[1:].split(maxsplit=1)
    cmd = parts[0].lower() if parts else ""
    arg = parts[1] if len(parts) > 1 else ""

    if cmd in ("help", "h", "?"):
        print("""
Slash Commands:
  /help, /h, /?     Show this help
  /save [slot]      Save game (default slot: "default")
  /load [slot]      Load game
  /saves            List available saves
  /debug, /d        Toggle debug mode (show LLM context)
  /state, /s        Show current game state (LLM context format)
  /eval <expr>      Evaluate a Grue expression
  /history          Show turn history
  /quit, /q         Exit the game
""")
        return True

    elif cmd in ("debug", "d"):
        session.debug = not session.debug
        print(f"Debug mode: {'on' if session.debug else 'off'}")
        return True

    elif cmd in ("state", "s"):
        print(session.format_debug_context())
        return True

    elif cmd == "eval":
        if not arg:
            print("Usage: /eval <grue-expression>")
            return True
        try:
            expr = parse(arg)
            result = session.evaluator.eval(expr)
            print(f"=> {result}")
        except Exception as e:
            print(f"Error: {e}")
        return True

    elif cmd == "history":
        if not session.turn_history:
            print("No turns yet.")
        else:
            for i, turn in enumerate(session.turn_history, 1):
                print(f"{i}. [{turn.room}] {turn.player_command}")
                if turn.actions:
                    print(f"   Actions: {', '.join(turn.actions)}")
        return True

    elif cmd == "save":
        slot = arg or "default"
        try:
            path = save_game(session.runtime, slot, session.turn_history)
            print(f"Game saved to {path}")
        except Exception as e:
            print(f"Error saving: {e}")
        return True

    elif cmd == "load":
        slot = arg or "default"
        try:
            history_data, warnings = load_game(session.runtime, slot)
            for w in warnings:
                print(f"Warning: {w}")
            # Restore turn history
            session.turn_history.clear()
            for turn_data in history_data:
                turn = TurnRecord(
                    room=turn_data.get("room", ""),
                    player_command=turn_data.get("command", ""),
                    actions=turn_data.get("actions", []),
                    results=turn_data.get("results", []),
                    narrative=turn_data.get("narrative", ""),
                )
                session.turn_history.append(turn)
            print(f"Game loaded ({len(session.turn_history)} turns of history)")
        except FileNotFoundError:
            print(f"No save found for slot '{slot}'")
        except Exception as e:
            print(f"Error loading: {e}")
        return True

    elif cmd == "saves":
        game_name = session.runtime.world.name or "unknown"
        saves = list_saves(game_name)
        if not saves:
            print("No saves found.")
        else:
            print("Available saves:")
            for slot, timestamp, path in saves:
                print(f"  {slot}: {timestamp}")
        return True

    elif cmd in ("quit", "q"):
        return False  # Signal to quit

    else:
        print(f"Unknown command: /{cmd}")
        print("Type /help for available commands.")
        return True


def play_game(game_path: str, debug: bool = False) -> None:
    """Run an interactive game session with plain text output.

    Uses slash commands for meta-operations like /debug, /eval, /state.
    Suitable for terminal automation.
    """
    print(f"Loading game: {game_path}")
    if debug:
        print("Debug mode enabled")

    session = GameSession.from_game_file(game_path, debug=debug)

    print()
    print("=" * 40)
    print("Game Start")
    print("=" * 40)

    # Show intro text if available
    if session.runtime.world.intro:
        print()
        print(session.runtime.world.intro)

    # Show initial state
    initial_state = session.get_state()
    if debug:
        _debug_log("LLM Context", session._format_state_debug(initial_state))
    render_game_state(initial_state, debug=debug)

    print("Type commands in natural language. Use /help for slash commands.\n")

    while True:
        try:
            print("> ", end="", flush=True)
            user_input = input()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        # Handle slash commands
        if user_input.startswith("/"):
            if not _handle_slash_command(session, user_input):
                print("Goodbye!")
                break
            continue

        # Legacy quit commands
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        # Process game command with streaming output
        def on_action(result: str) -> None:
            print(f"  {result}")

        response_text, results = session.process_input(user_input, on_action=on_action)

        if session.debug:
            state = session.get_state()
            _debug_log("LLM Context", session._format_state_debug(state))

        # Only show response (results already streamed)
        if response_text:
            print()
            print(response_text)
        print()
        render_game_state(session.get_state(), debug=session.debug)
