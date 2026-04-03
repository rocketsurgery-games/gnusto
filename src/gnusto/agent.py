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
from .knowledge import KnowledgeGraph
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

- **do_action**: Interact with objects. Requires `target` (entity ID like @hacker) and `verb` (like examine, take, ask-about). Optional `args` for action parameters.
- **move**: Navigate rooms. Requires `direction` (north, south, up, down, etc.)
- **wait**: Pass time. No additional fields needed.

## Knowledge Queries

Query your accumulated knowledge without spending a turn. Use these to look up details
about things the player has seen, places visited, or events that happened earlier.

- **recall**: What do you know about an entity? Set `target` to the entity ID (e.g., @key, @hallway). Returns description, location, observations, and related events.
- **map**: Review all explored rooms and connections. No target needed.
- **history**: Review what happened. Set `target` to a room or entity ID to filter, or omit for recent events.
- **search**: Search knowledge for a keyword. Set `target` to the search term.

Knowledge queries don't advance the game — they return information for you to use.
Use them when the player refers to something from earlier, or when you need context
about an entity or location before deciding what to do.

## Entity References and Action Arguments

Each object in the game state has an entity ID starting with `@` (like `@hacker`, `@master-key`).
You MUST always resolve natural language to entity IDs by matching against the visible objects list:
- "the hacker" or "him" → `@hacker`
- "his keyring" or "the keys" → `@keyring`
- "the master key" → `@master-key`

**Action arguments (`args`):** Each behavior's parameter list tells you what type of argument to pass.
- `<@param>` means pass an **entity ID** — look up the matching `@id` from visible objects, inventory, or known references. Example: `ask-about <@topic>` → `args: ["@master-key"]`
- `<param>` (no @) means pass a **literal value** — a string, number, or keyword. Example: `set-timer <seconds>` → `args: ["120"]`

Entity ID args MUST start with `@`. Never pass natural language like `"master key"` — find the entity ID.
If a behavior requires `<@entity>` but no matching entity exists in visible objects, inventory, or known references, do NOT guess or pass a raw string — instead narrate that you're unsure what the player means.

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
The visible objects list includes `@keyring: keyring`. The behavior is `ask-about <@topic>`.
Resolve "his keys" → `@keyring` from the visible objects list:
```json
{
  "actions": [{"tool": "do_action", "target": "@hacker", "verb": "ask-about", "args": ["@keyring"]}],
  "blocks": [],
  "needs_player_input": false
}
```

Player says "set the microwave to 2 minutes":
The behavior is `set-timer <seconds>` (no @, so pass a literal value):
```json
{
  "actions": [{"tool": "do_action", "target": "@microwave", "verb": "set-timer", "args": ["120"]}],
  "blocks": [],
  "needs_player_input": false
}
```

After seeing action results, narrate what happened:
```json
{
  "actions": [],
  "blocks": [
    {"type": "focus", "text": "The hacker looks up from his terminal, a glint of amusement in his eyes.", "entity": "@hacker"},
    {"type": "speak", "text": "Oh, this? It's my master key. Opens every door in the building.", "speaker": "@hacker", "manner": "casually"}
  ],
  "needs_player_input": true
}
```
"""

# Simplified prompt for parsing-only mode: LLM just picks actions, no narrative generation.
PARSING_ONLY_PROMPT = """\
You are a command parser for an interactive fiction game. Your ONLY job is to translate
the player's natural language into structured game actions. Do NOT generate any narrative,
descriptions, or dialogue — the game engine handles all text output.

Respond with JSON:
```json
{
  "actions": [{"tool": "do_action|move|wait", "target": "@entity-id", "verb": "action-verb", "args": ["@arg"], "direction": "dir"}],
  "needs_player_input": true
}
```

## Action types
- **do_action**: Interact with objects. Requires `target` (entity ID) and `verb` (from the object's available behaviors). Optional `args` for parameters.
- **move**: Navigate. Requires `direction` (must match an available exit).
- **wait**: Pass time.

## Rules
1. Match player intent to available objects and their behaviors
2. Entity IDs start with @ (e.g., @hacker, @pc). Resolve "the hacker" → @hacker
3. Only use verbs listed in an object's behaviors
4. Only use directions listed in exits
5. For behavior params marked <@param>, pass an entity ID. For <param>, pass a literal.
6. If the player's intent doesn't match any available action, return empty actions with needs_player_input: true
7. Set needs_player_input: true after every action sequence (you never need to narrate)
8. NEVER include a "blocks" field — the game engine generates all text
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
    turn_history: list[TurnRecord] = field(default_factory=list)
    summaries: list[str] = field(default_factory=list)  # Narrative summary blocks
    knowledge: KnowledgeGraph = field(default_factory=KnowledgeGraph)
    debug: bool = False
    parsing_only: bool = False  # LLM only picks actions; engine generates all text

    @classmethod
    def from_game_file(
        cls,
        game_path: str,
        llm_config: LLMConfig | None = None,
        debug: bool = False,
        parsing_only: bool | None = None,
    ) -> "GameSession":
        """Create a new game session from a game file."""
        game_dir = Path(game_path).resolve()
        if game_dir.is_file():
            game_dir = game_dir.parent

        world = load_grue(game_path)
        runtime = GrueRuntime(world)
        evaluator = ReplEvaluator(runtime)
        llm = LLMClient(llm_config)

        # Auto-enable parsing-only mode for local models
        if parsing_only is None:
            config = llm_config or LLMConfig.from_env()
            parsing_only = config.api_base is not None

        session = cls(
            runtime=runtime,
            evaluator=evaluator,
            llm=llm,
            game_dir=game_dir,
            debug=debug,
            parsing_only=parsing_only,
        )
        # Observe initial game state (turn 0, no command)
        session.knowledge.observe_turn(
            state=session.get_state(),
            command=None,
            actions=[],
            results=[],
            blocks=[],
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
        prompt = PARSING_ONLY_PROMPT if self.parsing_only else SYSTEM_PROMPT
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": prompt}
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
        all_render_blocks: list[ContentBlock] = []  # For knowledge graph
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

            # Convert and emit content blocks (full agent mode only)
            if not self.parsing_only and response.blocks:
                render_blocks = [content_block_data_to_render(b) for b in response.blocks]
                all_render_blocks.extend(render_blocks)
                if on_blocks:
                    on_blocks(render_blocks)
                # Flatten block text for history
                for b in response.blocks:
                    all_narratives.append(b.text)

            # If no actions, we're done.
            # In full agent mode, also stop if needs_player_input (LLM narrates first).
            # In parsing-only mode, execute actions first then stop.
            if not response.actions:
                break
            if response.needs_player_input and not self.parsing_only:
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

                # In parsing-only mode, generate content blocks from engine results
                if self.parsing_only:
                    engine_blocks = self._blocks_from_results(raw_results)
                    if engine_blocks:
                        all_render_blocks.extend(engine_blocks)
                        if on_blocks:
                            on_blocks(engine_blocks)
                        for b in engine_blocks:
                            if hasattr(b, 'text'):
                                all_narratives.append(b.text)

            # In parsing-only mode, we're done after executing — no multi-turn narration
            if self.parsing_only:
                break

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
            state_context = state.to_context_string()
            working_messages.append({
                "role": "user",
                "content": f"[Updated game state:]\n{state_context}\n\nNarrate what happened using content blocks, then continue or set needs_player_input to true if done."
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

        # Update knowledge graph with what the player learned
        final_state = self.get_state()
        self.knowledge.observe_turn(
            state=final_state,
            command=user_input,
            actions=all_actions,
            results=all_action_results,
            blocks=all_render_blocks,
        )

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
        elif action.tool == "recall":
            return ([], self.knowledge.recall(action.target or ""))
        elif action.tool == "map":
            return ([], self.knowledge.map_summary())
        elif action.tool == "history":
            if action.target:
                # Detect whether target is a room or entity
                node = self.knowledge.nodes.get(action.target)
                if node and node.kind == 'room':
                    return ([], self.knowledge.history(room_id=action.target))
                return ([], self.knowledge.history(entity_id=action.target))
            return ([], self.knowledge.history())
        elif action.tool == "search":
            return ([], self.knowledge.search(action.target or ""))
        else:
            return ([], f"Unknown action: {action.tool}")

    def _blocks_from_results(self, raw_results: list[Any]) -> list[ContentBlock]:
        """Convert raw engine results into content blocks for parsing-only mode."""
        from . import render
        blocks: list[ContentBlock] = []
        for result in raw_results:
            # Blocked actions — show the player-facing message
            if isinstance(result, ActionBlocked):
                if result.message:
                    blocks.append(render.Narrate(text=result.message))
                continue
            # Error actions
            if isinstance(result, ActionError):
                blocks.append(render.Narrate(text=result.message))
                continue
            if not hasattr(result, 'output'):
                continue
            # Structured output from effects (narrate/say)
            for out_type, entity, text in result.output:
                if not text:
                    continue
                if out_type == "narrate":
                    blocks.append(render.Narrate(text=text))
                elif out_type == "say":
                    blocks.append(render.Speak(speaker=entity or "unknown", text=text))
            # Reason text (used for examine/describe results)
            if hasattr(result, 'reason') and result.reason:
                blocks.append(render.Narrate(text=result.reason))
            # Fall back to context fields
            if not blocks and hasattr(result, 'context'):
                for key, value in result.context:
                    if key in ("description", "message", "response") and str(value):
                        blocks.append(render.Narrate(text=str(value)))
        return blocks

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
        elif action.tool in ("recall", "map", "history", "search"):
            if action.target:
                return f"{action.tool} {action.target}"
            return action.tool
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
        elif action.tool in ("recall", "map", "history", "search"):
            if action.target:
                return f"(kg:{action.tool} {action.target})"
            return f"(kg:{action.tool})"
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
