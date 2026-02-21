"""
Agent-driven game player for Gnusto.

This module provides the agent that plays GRUE games. It interprets natural
language input, translates it to game actions via tool calling, and renders
results. The default mode uses plain text for automation compatibility.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from grue.parser import load_grue
from grue.repl import ActionBlocked, ActionDone, ActionError, ReplEvaluator
from grue.runtime import ActionResult, GrueRuntime
from grue.save import save_game, load_game, list_saves
from grue.sexpr import Keyword, SList, Symbol, parse, to_string

from .commands import handle_command, render_blocks_to_text
from .images import scan_images, filter_images_for_state, format_image_catalog, add_renderable_entities, ImageInfo
from .llm import LLMClient, LLMConfig, AgentResponse, ActionRequest, ContentBlockData, content_block_data_to_render
from .render import ContentBlock
from .state import GameState, ObjectInfo, get_game_state

SYSTEM_PROMPT = """\
You are the narrator for an interactive fiction game. You interpret the player's commands,
execute game actions, and narrate the results using structured content blocks.

You MUST respond with valid JSON matching this schema:
```json
{
  "actions": [...],
  "blocks": [
    {"type": "narrate", "text": "..."},
    {"type": "speak", "text": "...", "speaker": "@entity-id", "manner": null},
    {"type": "think", "text": "..."},
    {"type": "ambient", "text": "..."},
    {"type": "reveal", "text": "...", "entity": "@entity-id"},
    {"type": "focus", "text": "...", "entity": "@entity-id"}
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

## Content Blocks

Use these block types to structure your narrative output:

- **narrate**: Second-person prose describing what happens. "You step forward and peer into the darkness."
- **speak**: Character dialogue. Set `speaker` to the entity ID (e.g., `@hacker`). Set optional `manner` for delivery (e.g., "whispering", "shouting"). The `text` is the spoken words only, without quotes.
- **think**: Player's inner monologue or dramatic realization. Use sparingly for significant moments.
- **ambient**: Atmospheric detail — sounds, smells, temperature. Sets mood without advancing action.
- **reveal**: Discovery of something new or important. Set `entity` if a specific object is being discovered.
- **focus**: Close-up examination of an entity. Set `entity` to the object/character ID being examined. The system will display the entity's image alongside the text.

### Block Guidelines

- Use `narrate` as your default — most prose should be narrate blocks
- Use `speak` for ALL character dialogue, with `@entity` speaker IDs
- Use `focus` when the player examines or closely interacts with an entity
- Use `reveal` when something new is discovered or first noticed
- Use `ambient` for atmosphere that enriches the scene
- Use `think` sparingly — only for dramatic moments
- Do NOT describe room transitions — the system handles those automatically
- Be concise: 1-3 blocks per response is typical, rarely more than 5
- Preserve dialogue verbatim in speak blocks

## Flow

1. If you need to execute actions, put them in `actions` and set `needs_player_input: false`
2. After seeing action results, narrate what happened using blocks and decide if more actions are needed
3. Set `needs_player_input: true` when:
   - You're done with the player's request
   - Something unexpected happened (stop the sequence!)
   - You need clarification

## Examples

Player says "ask the hacker about his keys":
```json
{
  "actions": [{"tool": "do_action", "target": "@hacker", "verb": "ask", "args": ["@keyring"]}],
  "blocks": [],
  "needs_player_input": false
}
```

After seeing the result:
```json
{
  "actions": [],
  "blocks": [
    {"type": "focus", "text": "The hacker looks up from his terminal, a glint of amusement in his eyes.", "entity": "@hacker", "speaker": null, "manner": null},
    {"type": "speak", "text": "Oh, this? It's my master key. Opens every door in the building.", "speaker": "@hacker", "manner": "casually", "entity": null}
  ],
  "needs_player_input": true
}
```

Player says "look around":
```json
{
  "actions": [],
  "blocks": [
    {"type": "ambient", "text": "The fluorescent lights hum overhead, casting a sterile glow across the cluttered workstations.", "speaker": null, "manner": null, "entity": null},
    {"type": "narrate", "text": "You take in your surroundings, noting the scattered papers and half-empty coffee cups.", "speaker": null, "manner": null, "entity": null}
  ],
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
    objects_with_ldesc = [obj for obj in state.visible_objects if obj.ldesc]
    if objects_with_ldesc:
        print()
        for obj in objects_with_ldesc:
            print(obj.ldesc)

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


# Prompt for summarizing a batch of turns into narrative
SUMMARIZE_PROMPT = """\
Summarize these game turns into a brief narrative paragraph (2-4 sentences).

Preserve:
- Room names and locations visited
- Objects found, taken, or interacted with
- NPC interactions and key dialogue
- Important events or discoveries

Write in second person past tense ("You found...", "You spoke with...").
Focus on what the player learned or accomplished, not mechanical details.
"""


@dataclass
class GameSession:
    """An agent-driven game session."""

    runtime: GrueRuntime
    evaluator: ReplEvaluator
    llm: LLMClient
    game_dir: Path
    all_images: list[ImageInfo] = field(default_factory=list)
    turn_history: list[TurnRecord] = field(default_factory=list)
    summaries: list[str] = field(default_factory=list)  # Narrative summary blocks
    debug: bool = False

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

        # Scan for available images and add renderable entities
        all_images = scan_images(game_dir)
        all_images = add_renderable_entities(all_images, runtime)

        session = cls(
            runtime=runtime,
            evaluator=evaluator,
            llm=llm,
            game_dir=game_dir,
            all_images=all_images,
            debug=debug,
        )
        return session

    # History settings (action-based, not turn-based)
    recent_actions: int = 15  # Keep ~15 actions in full detail
    pending_buffer_actions: int = 10  # Summarize when buffer exceeds this

    def _count_actions(self) -> int:
        """Count total actions across all TurnRecords."""
        return sum(len(t.actions) or 1 for t in self.turn_history)

    def _maybe_summarize(self) -> None:
        """
        Check if pending buffer is full and summarize if needed.

        Uses action count (not turn count) to determine when to summarize.
        A single user command can execute many game actions, so we need
        to track at action granularity for proper context management.

        When total actions exceed recent_actions + pending_buffer_actions,
        we remove whole TurnRecords (oldest first) until we've removed
        ~pending_buffer_actions worth of actions.
        """
        threshold = self.recent_actions + self.pending_buffer_actions
        if self._count_actions() <= threshold:
            return

        # Extract TurnRecords until we've removed enough actions
        turns_to_summarize = []
        actions_removed = 0
        while self.turn_history and actions_removed < self.pending_buffer_actions:
            turn = self.turn_history.pop(0)
            turns_to_summarize.append(turn)
            actions_removed += len(turn.actions) or 1

        if self.debug:
            _debug_log(
                "Summarizing turns",
                f"{len(turns_to_summarize)} turns ({actions_removed} actions) -> narrative block",
                style="blue"
            )

        # Format turns for summarization
        turn_descriptions = []
        for turn in turns_to_summarize:
            lines = [f"In {turn.room}: {turn.player_command}"]
            for i, action in enumerate(turn.actions):
                result = turn.results[i] if i < len(turn.results) else ""
                if result and result != "Done.":
                    lines.append(f"  {action}: {result}")
            turn_descriptions.append("\n".join(lines))

        turns_text = "\n\n".join(turn_descriptions)

        # Call LLM to generate summary
        messages = [
            {"role": "system", "content": SUMMARIZE_PROMPT},
            {"role": "user", "content": turns_text},
        ]

        try:
            # Use basic chat for summarization (not structured JSON)
            response = self.llm.chat(messages)
            summary = response.content or ""
            self.summaries.append(summary.strip())

            if self.debug:
                _debug_log("Summary generated", summary.strip(), style="green")

        except Exception as e:
            # On error, fall back to mechanical summary
            fallback = "; ".join(
                f"[{t.room}] {t.player_command}" for t in turns_to_summarize
            )
            self.summaries.append(f"(Summary unavailable: {fallback})")

            if self.debug:
                _debug_log("Summary error", str(e), style="red")

    def _build_messages(self, current_state: GameState, player_command: str) -> list[dict[str, Any]]:
        """
        Build fresh message list for LLM from history + current state.

        Structure:
        1. System prompt
        2. Summaries ("the story so far" - oldest to newest)
        3. Recent full turns (as user/assistant pairs)
        4. Current game state + player command
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        # Add summaries as "story so far" context
        if self.summaries:
            story_so_far = "\n\n".join(self.summaries)
            messages.append({
                "role": "user",
                "content": f"[Story so far:]\n{story_so_far}"
            })
            messages.append({
                "role": "assistant",
                "content": "(Acknowledged - I'll continue narrating from here.)"
            })

        # Add recent turns in full detail
        for turn in self.turn_history:
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

        Returns dict with breakdown:
        - system_prompt: Tokens in system prompt
        - summaries: Tokens in narrative summaries
        - recent_turns: Tokens in recent full-detail turns
        - state_estimate: Estimated tokens for typical game state
        - total: Sum of all components
        """
        system_tokens = estimate_tokens(SYSTEM_PROMPT)

        # Summaries
        summaries_text = "\n\n".join(self.summaries)
        summaries_tokens = estimate_tokens(summaries_text) if self.summaries else 0

        # Recent turns (full detail)
        recent_tokens = sum(turn.estimate_tokens() for turn in self.turn_history)

        # Estimate typical game state size (varies by room)
        state_estimate = 500  # Rough average

        total = system_tokens + summaries_tokens + recent_tokens + state_estimate

        return {
            "system_prompt": system_tokens,
            "summaries": summaries_tokens,
            "summaries_count": len(self.summaries),
            "recent_turns": recent_tokens,
            "recent_turns_count": len(self.turn_history),
            "recent_actions_count": self._count_actions(),
            "state_estimate": state_estimate,
            "total": total,
        }

    def get_state_context(self) -> str:
        """Get current game state as context string for agent."""
        return self.get_state().to_context_string()

    def process_input(
        self,
        user_input: str,
        max_iterations: int = 10,
        on_blocks: "Callable[[list[ContentBlock]], None] | None" = None,
        on_debug: "Callable[[str, str], None] | None" = None,
    ) -> tuple[str, list[str]]:
        """
        Process natural language input and return response.

        Uses structured JSON output from the LLM. The loop:
        1. Send game state + player command
        2. LLM returns actions + content blocks
        3. Execute actions, collect results
        4. If needs_player_input, stop; otherwise add results and loop

        Args:
            user_input: Natural language command from player
            max_iterations: Maximum number of LLM calls (default 10)
            on_blocks: Optional callback for streaming content blocks
            on_debug: Optional callback for debug info (label, content)

        Returns:
            Tuple of (final narrative, raw action results list)
        """
        # Get initial state and build base messages from history
        initial_state = self.get_state()
        initial_room = initial_state.room

        # Build fresh messages: history + current state + command
        working_messages = self._build_messages(initial_state, user_input)

        all_results: list[str] = []  # Raw results for caller
        all_actions: list[str] = []  # Action summaries for TurnRecord
        all_action_results: list[str] = []  # Results paired with actions for TurnRecord
        all_narratives: list[str] = []  # Flattened block text for history
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Get structured response from LLM
            try:
                response = self.llm.chat_structured(messages=working_messages)
            except Exception as e:
                error_msg = str(e)
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                return f"[LLM error: {error_msg}. Please try again.]", []

            # Convert and emit content blocks
            if response.blocks:
                render_blocks = [content_block_data_to_render(b) for b in response.blocks]
                if on_blocks:
                    on_blocks(render_blocks)
                # Flatten block text for history
                for b in response.blocks:
                    all_narratives.append(b.text)

            # If no actions or needs player input, we're done
            if not response.actions or response.needs_player_input:
                break

            # Execute actions
            action_results: list[str] = []
            for action in response.actions:
                action_summary = self._summarize_action(action)
                raw_results, formatted_result = self._execute_action(action)

                action_results.append(formatted_result)
                all_results.append(formatted_result)

                # Track for history
                all_actions.append(action_summary)
                all_action_results.append(formatted_result)

                # Emit compact debug output
                if self.debug and on_debug:
                    action_sexpr = self._format_action_sexpr(action)
                    result_debug = self._format_compact_debug(raw_results)
                    on_debug(action_sexpr, result_debug)

            # Add assistant response to messages (as JSON)
            working_messages.append({
                "role": "assistant",
                "content": json.dumps({
                    "actions": [{"tool": a.tool, "target": a.target, "verb": a.verb, "args": a.args, "direction": a.direction} for a in response.actions],
                    "blocks": [{"type": b.type, "text": b.text, "speaker": b.speaker, "manner": b.manner, "entity": b.entity} for b in response.blocks],
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

            # Filter images for new state
            relevant_images = filter_images_for_state(self.all_images, state)
            image_context = format_image_catalog(relevant_images)

            state_context = state.to_context_string()
            working_messages.append({
                "role": "user",
                "content": f"[Updated game state:]\n{state_context}\n\n{image_context}\n\nNarrate what happened using content blocks, then continue or set needs_player_input to true if done."
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

        # Check if we need to summarize older turns
        self._maybe_summarize()

        return final_response_text, all_results

    def _execute_action(self, action: ActionRequest) -> tuple[list[Any], str]:
        """Execute a single action and return (raw_results, formatted_string)."""
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
            return ([], f"Unknown action: {action.tool}")

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

    def _format_action_sexpr(self, action: ActionRequest) -> str:
        """Format an action as a Grue S-expression for debug display."""
        if action.tool == "do_action":
            parts = [f"(do {action.target} :{action.verb}"]
            for arg in action.args or []:
                parts.append(f" {arg}")
            return "".join(parts) + ")"
        elif action.tool == "move":
            return f"(go {action.direction})"
        elif action.tool == "wait":
            return "(wait)"
        else:
            return f"({action.tool} ...)"

    def _do_action(self, target: str, verb: str, action_args: list[str]) -> tuple[list[Any], str]:
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

    def _move(self, direction: str) -> tuple[list[Any], str]:
        """Execute a move action."""
        expr = SList([Symbol("go"), Symbol(direction)])
        return self._eval_and_format(expr)

    def _wait(self) -> tuple[list[Any], str]:
        """Execute a wait action."""
        expr = SList([Symbol("wait")])
        return self._eval_and_format(expr)

    def _eval_and_format(self, expr: SList) -> tuple[list[Any], str]:
        """Evaluate expression and format result.

        Returns:
            Tuple of (raw_results, formatted_string) where raw_results includes
            the main action result and any event results.
        """
        result = self.evaluator.eval(expr)

        # Process turn-based events after action (like repl does)
        event_results = self.runtime.process_events()

        # Collect all raw results
        raw_results = [result] + list(event_results)

        # Combine action result with any event descriptions for LLM
        parts = [self._format_action_result(result)]
        for event_result in event_results:
            event_text = self._format_action_result(event_result)
            if event_text and event_text != "Done.":
                parts.append(event_text)

        return (raw_results, " ".join(parts))

    def _format_compact_debug(self, results: list[Any]) -> str:
        """Format results in compact debug format for display."""
        lines = []
        for result in results:
            if isinstance(result, ActionDone):
                # Show key context fields
                for key, value in result.context:
                    lines.append(f"{key}: {value}")
                # Show output (narrate/say)
                for out_type, entity, text in result.output:
                    if out_type == "say" and entity:
                        lines.append(f'{entity}: "{text}"')
                    elif out_type == "narrate":
                        lines.append(f"narrate: {text}")
                # Show reason if present
                if result.reason:
                    lines.append(f"description: {result.reason}")
                # Show effects
                if result.effects:
                    if len(result.effects) == 1:
                        lines.append(f"effects: {result.effects[0]}")
                    else:
                        lines.append("effects: " + result.effects[0])
                        for eff in result.effects[1:]:
                            lines.append(f"         {eff}")
            elif isinstance(result, ActionBlocked):
                lines.append(f"blocked: {result.reason}")
                if result.message:
                    lines.append(f"message: {result.message}")
                for out_type, entity, text in result.output:
                    if out_type == "say" and entity:
                        lines.append(f'{entity}: "{text}"')
            elif isinstance(result, ActionError):
                lines.append(f"error: {result.message}")
            elif isinstance(result, ActionResult):
                # From runtime.ActionResult
                lines.append(f"outcome: {result.outcome}")
                for key, value in result.context:
                    lines.append(f"{key}: {value}")
                if result.effects_applied:
                    if len(result.effects_applied) == 1:
                        lines.append(f"effects: {result.effects_applied[0]}")
                    else:
                        lines.append("effects: " + result.effects_applied[0])
                        for eff in result.effects_applied[1:]:
                            lines.append(f"         {eff}")
        return "\n".join(lines)

    def _format_result_debug(self, result: Any) -> str:
        """Format a result for debug display (legacy verbose format)."""
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

        # Summaries (story so far)
        lines.append("## Story So Far")
        if not self.summaries:
            lines.append("(no summaries yet)")
        else:
            lines.append(f"({len(self.summaries)} summary blocks)")
            for i, summary in enumerate(self.summaries, 1):
                lines.append(f"  [{i}] {summary}")
        lines.append("")

        # Recent turns
        lines.append("## Recent Turns")
        if not self.turn_history:
            lines.append("(no turns yet)")
        else:
            action_count = self._count_actions()
            lines.append(f"({len(self.turn_history)} turns, {action_count} actions)")
            lines.append("")
            for turn in self.turn_history:
                lines.append(f"[FULL] {turn.to_summary()}")
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


def _handle_slash_command(session: "GameSession", command: str, game_dir: Path | None = None) -> bool:
    """Handle slash commands. Returns True to continue, False to quit."""
    result = handle_command(command, session, game_dir)

    # Print any output blocks
    if result.blocks:
        print(render_blocks_to_text(result.blocks))

    # Handle special actions
    if result.action == "quit":
        return False
    elif result.action == "clear":
        print("\033[2J\033[H")  # ANSI clear screen
    elif result.action == "reset":
        # Reset is handled by the caller checking result.action
        pass

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
            if not _handle_slash_command(session, user_input, session.game_dir):
                print("Goodbye!")
                break
            continue

        # Legacy quit commands
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        # Process game command with streaming output
        def on_blocks(blocks: list[ContentBlock]) -> None:
            for block in blocks:
                text = getattr(block, "text", "")
                if text:
                    print()
                    print(text)

        def on_debug(action_sexpr: str, result_details: str) -> None:
            # Show action as S-expression, then result details indented
            print(action_sexpr)
            for line in result_details.split("\n"):
                if line:
                    print(f"  {line}")
            print()

        session.process_input(
            user_input,
            on_blocks=on_blocks,
            on_debug=on_debug if session.debug else None,
        )

        # Only show room state if not in debug mode (debug already shows details)
        if not session.debug:
            print()
            render_game_state(session.get_state(), debug=False)
