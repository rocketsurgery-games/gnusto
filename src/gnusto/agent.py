"""
Agent-driven game player for Gnusto.

This module provides the agent that plays GRUE games. It interprets natural
language input, translates it to game actions via tool calling, and renders
results. The default mode uses plain text for automation compatibility.
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from grue.parser import load_grue
from grue.repl import ActionBlocked, ActionDone, ActionError, ReplEvaluator
from grue.runtime import ActionResult, GrueRuntime
from grue.save import save_game, load_game, list_saves
from grue.sexpr import Keyword, SList, Symbol, parse, to_string

from .images import scan_images, filter_images_for_state, format_image_catalog, ImageInfo
from .llm import LLMClient, LLMConfig, AgentResponse, ActionRequest, ImageRequest
from .state import GameState, ObjectInfo, get_game_state

SYSTEM_PROMPT = """\
You are the narrator for an interactive fiction game. You interpret the player's commands,
execute game actions, and narrate the results.

You MUST respond with valid JSON matching this schema:
```json
{
  "actions": [
    {"tool": "do_action", "target": "@object-id", "verb": "examine", "args": []},
    {"tool": "move", "direction": "north"},
    {"tool": "wait"}
  ],
  "narrative": "Your narrative text here...",
  "images": [
    {"path": "/gfx/image.jpg", "alt": "description", "layout": "inline", "size": "medium"}
  ],
  "needs_player_input": false
}
```

## Actions

- **do_action**: Interact with objects. Requires `target` (object ID like @hacker) and `verb` (like examine, take, ask). Optional `args` for additional objects.
- **move**: Navigate rooms. Requires `direction` (north, south, up, down, etc.)
- **wait**: Pass time. No additional fields needed.

## Object References

Match natural language to object IDs from the game state:
- "the hacker" or "him" → @hacker
- "his keyring" or "the keys" → @keyring
- "the computer" or "terminal" → @pc

## Narrative Guidelines

- **Preserve dialogue verbatim**: Quote characters' exact words
- **Be concise**: 1-3 sentences, don't pad with atmosphere
- **Second person**: "You examine the terminal..."

## Images

Include images to enhance the narrative when focusing on specific objects or characters.

**Important:**
- Room images are already displayed in the UI header - DON'T include them
- Only include images for objects/characters the player is examining or interacting with
- Never include the same image twice
- Use at most ONE image per response

Layouts: `inline`, `float-left`, `float-right`, `background`
Sizes: `small`, `medium`, `large`, `full`

## Flow

1. If you need to execute actions, put them in `actions` and set `needs_player_input: false`
2. After seeing action results, narrate what happened and decide if more actions are needed
3. Set `needs_player_input: true` when:
   - You're done with the player's request
   - Something unexpected happened (stop the sequence!)
   - You need clarification

## Example Response

Player says "ask the hacker about his keys":
```json
{
  "actions": [{"tool": "do_action", "target": "@hacker", "verb": "ask", "args": ["@keyring"]}],
  "narrative": null,
  "images": [],
  "needs_player_input": false
}
```

After seeing the result:
```json
{
  "actions": [],
  "narrative": "The hacker looks up from his terminal. \"Oh, this?\" He holds up a worn keyring. \"It's my master key. Opens every door in the building.\"",
  "images": [{"path": "/gfx/hacker.jpg", "layout": "float-right", "size": "small"}],
  "needs_player_input": true
}
```
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
    game_dir: Path
    all_images: list[ImageInfo] = field(default_factory=list)
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
        game_dir = Path(game_path).resolve()
        if game_dir.is_file():
            game_dir = game_dir.parent

        world = load_grue(game_path)
        runtime = GrueRuntime(world)
        evaluator = ReplEvaluator(runtime)
        llm = LLMClient(llm_config)

        # Scan for available images
        all_images = scan_images(game_dir)

        session = cls(
            runtime=runtime,
            evaluator=evaluator,
            llm=llm,
            game_dir=game_dir,
            all_images=all_images,
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

        # Current turn: fresh state + images + player command
        state_context = current_state.to_context_string()

        # Filter images relevant to current state
        relevant_images = filter_images_for_state(self.all_images, current_state)
        image_context = format_image_catalog(relevant_images)

        messages.append({
            "role": "user",
            "content": f"{state_context}\n\n{image_context}\n\n---\n\nPlayer command: {player_command}"
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
        on_narrative: "Callable[[str], None] | None" = None,
        on_image: "Callable[[ImageRequest], None] | None" = None,
    ) -> tuple[str, list[str]]:
        """
        Process natural language input and return response.

        Uses structured JSON output from the LLM. The loop:
        1. Send game state + player command
        2. LLM returns actions, narrative, images
        3. Execute actions, collect results
        4. If needs_player_input, stop; otherwise add results and loop

        Args:
            user_input: Natural language command from player
            max_iterations: Maximum number of LLM calls (default 10)
            on_narrative: Optional callback for streaming narrative text
            on_image: Optional callback for streaming image requests

        Returns:
            Tuple of (final narrative, raw action results list)
        """
        # Get initial state and build base messages from history
        initial_state = self.get_state()
        initial_room = initial_state.room

        if self.debug:
            _debug_log("LLM Context (game state)", self._format_state_debug(initial_state), style="cyan")

        # Build fresh messages: history + current state + command
        working_messages = self._build_messages(initial_state, user_input)

        all_results: list[str] = []  # Raw results for caller
        all_actions: list[str] = []  # Action summaries for TurnRecord
        all_action_results: list[str] = []  # Results paired with actions for TurnRecord
        all_narratives: list[str] = []  # LLM narratives per step
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            if self.debug and iteration > 1:
                _debug_log(f"Agentic Loop Iteration {iteration}", "", style="blue")

            # Get structured response from LLM
            try:
                response = self.llm.chat_structured(messages=working_messages)
            except Exception as e:
                error_msg = str(e)
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                return f"[LLM error: {error_msg}. Please try again.]", []

            if self.debug:
                _debug_log("Agent Response", json.dumps({
                    "actions": [{"tool": a.tool, "target": a.target, "verb": a.verb} for a in response.actions],
                    "narrative": response.narrative[:100] + "..." if response.narrative and len(response.narrative) > 100 else response.narrative,
                    "images": [i.path for i in response.images],
                    "needs_player_input": response.needs_player_input,
                }, indent=2), style="magenta")

            # Emit images first (so they appear before narrative)
            for image in response.images:
                if on_image:
                    on_image(image)

            # Emit narrative
            if response.narrative:
                all_narratives.append(response.narrative)
                if on_narrative:
                    on_narrative(response.narrative)

            # If no actions or needs player input, we're done
            if not response.actions or response.needs_player_input:
                break

            # Execute actions
            action_results: list[str] = []
            for action in response.actions:
                if self.debug:
                    _debug_log(f"Executing: {action.tool}", f"target={action.target} verb={action.verb} direction={action.direction}", style="yellow")

                result = self._execute_action(action)
                action_results.append(result)
                all_results.append(result)

                # Track for history
                action_summary = self._summarize_action(action)
                all_actions.append(action_summary)
                all_action_results.append(result)

                if self.debug:
                    _debug_log("Action Result", result, style="green")

            # Add assistant response to messages (as JSON)
            working_messages.append({
                "role": "assistant",
                "content": json.dumps({
                    "actions": [{"tool": a.tool, "target": a.target, "verb": a.verb, "args": a.args, "direction": a.direction} for a in response.actions],
                    "narrative": response.narrative,
                    "images": [{"path": i.path, "layout": i.layout, "size": i.size} for i in response.images],
                    "needs_player_input": response.needs_player_input,
                })
            })

            # Add action results
            results_text = "\n".join(f"- {r}" for r in action_results)
            working_messages.append({
                "role": "user",
                "content": f"Action results:\n{results_text}"
            })

            # Add updated game state
            state = self.get_state()
            if self.debug:
                _debug_log("LLM Context (updated state)", self._format_state_debug(state), style="cyan")

            # Filter images for new state
            relevant_images = filter_images_for_state(self.all_images, state)
            image_context = format_image_catalog(relevant_images)

            state_context = state.to_context_string()
            working_messages.append({
                "role": "user",
                "content": f"[Updated game state:]\n{state_context}\n\n{image_context}\n\nNarrate what happened, then continue or set needs_player_input to true if done."
            })

        else:
            # Hit max iterations
            if self.debug:
                _debug_log("Max Iterations", f"Stopped after {max_iterations} iterations", style="red")

        # Combine all narratives for final output
        final_response_text = "\n\n".join(all_narratives)

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

    def _execute_action(self, action: ActionRequest) -> str:
        """Execute a single action and return the result string."""
        if action.tool == "do_action":
            return self._do_action(
                target=action.target or "",
                verb=action.verb or "",
                action_args=action.args or [],
            )
        elif action.tool == "move":
            return self._move(action.direction or "")
        elif action.tool == "wait":
            return self._wait()
        else:
            return f"Unknown action: {action.tool}"

    def _summarize_action(self, action: ActionRequest) -> str:
        """Generate a compact summary of an action for history."""
        if action.tool == "do_action":
            if action.args:
                return f"{action.verb} {action.target} with {', '.join(action.args)}"
            return f"{action.verb} {action.target}"
        elif action.tool == "move":
            return f"go {action.direction}"
        elif action.tool == "wait":
            return "wait"
        else:
            return f"{action.tool}(...)"

    def _do_action(self, target: str, verb: str, action_args: list[str]) -> str:
        """Execute a do action."""
        # Build S-expression: (do @target :verb arg1 arg2 ...)
        items = [Symbol("do"), Symbol(target), Keyword(verb)]
        for arg in action_args:
            # Arguments starting with @ are object references (Symbols)
            # Numeric strings become integers
            # Everything else stays as a string value
            if arg.startswith("@"):
                items.append(Symbol(arg))
            elif arg.lstrip("-").isdigit():
                items.append(int(arg))
            else:
                items.append(arg)  # Keep as string

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
            parts = []
            # Include structured output (narrate/say effects)
            for out_type, entity, text in result.output:
                if out_type == "narrate":
                    parts.append(text)
                elif out_type == "say":
                    parts.append(f'{entity}: "{text}"')
            # Include reason (used for describe/examine descriptions)
            if result.reason:
                parts.append(result.reason)
            # Fall back to legacy context values
            for key, value in result.context:
                if key in ("description", "message", "response"):
                    parts.append(str(value))
            return " ".join(parts) if parts else "Done."
        elif isinstance(result, ActionBlocked):
            parts = []
            # Include structured output (narrate/say effects)
            for out_type, entity, text in result.output:
                if out_type == "narrate":
                    parts.append(text)
                elif out_type == "say":
                    parts.append(f'{entity}: "{text}"')
            if parts:
                return " ".join(parts) + f" (Blocked: {result.reason})"
            return f"Blocked: {result.message}"
        elif isinstance(result, ActionError):
            return f"Error: {result.message}"
        elif isinstance(result, ActionResult):
            # Runtime ActionResult (from events)
            parts = []
            # Include structured output
            for out_type, entity, text in result.output:
                if out_type == "narrate":
                    parts.append(text)
                elif out_type == "say":
                    parts.append(f'{entity}: "{text}"')
            # Include reason for describe/examine
            if result.reason:
                parts.append(result.reason)
            # Fall back to legacy context
            for key, value in result.context:
                if key in ("description", "message", "response"):
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

        # Process game command with streaming narrative
        def on_narrative(text: str) -> None:
            if text:
                print()
                print(text)

        session.process_input(user_input, on_narrative=on_narrative)

        if session.debug:
            state = session.get_state()
            _debug_log("LLM Context", session._format_state_debug(state))

        print()
        render_game_state(session.get_state(), debug=session.debug)
