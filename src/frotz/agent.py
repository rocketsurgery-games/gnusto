"""
Agent-driven game player for Frotz.

This module provides the agent that plays GRUE games. It interprets natural
language input, translates it to game actions via tool calling, and renders
results with a rich terminal UI.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from grue.parser import load_grue
from grue.repl import ActionBlocked, ActionDone, ActionError, ReplEvaluator
from grue.runtime import ActionResult, GrueRuntime
from grue.sexpr import Keyword, SList, Symbol, to_string

from .llm import LLMClient, LLMConfig, LLMResponse, ToolCall, get_game_tools
from .state import GameState, ObjectInfo, get_game_state

console = Console()


SYSTEM_PROMPT = """\
You are a game master for an interactive fiction game. Your role is to:

1. Interpret the player's natural language commands
2. Translate them into game actions using the available tools
3. Describe the results in an engaging, atmospheric way

When the player gives a command:
- Use the do_action tool for interactions with objects (examine, take, open, etc.)
- Use the move tool for navigation (go north, enter building, etc.)
- Use the wait tool when the player wants to wait or pass time

Always use the object IDs exactly as shown in the game state (e.g., @door, @key).
Match the player's intent to the available actions on visible objects.

If the player's command is unclear or impossible, explain why and suggest alternatives.
"""


def render_game_state(state: GameState, debug: bool = False) -> None:
    """Render game state using rich panels and tables.

    Args:
        state: Current game state
        debug: If True, show technical details (IDs, actions, directions)
    """
    # Room panel - build description with object fdesc listings
    room_content = Text()
    if state.vehicle:
        room_content.append(
            f"(You are {state.vehicle[1]} the {state.vehicle[0]})\n\n", style="italic dim"
        )
    room_content.append(state.room_description)

    # Add object descriptions (fdesc) to room description
    for obj in state.visible_objects:
        if obj.fdesc:
            room_content.append(f"\n{obj.fdesc}")

    console.print(
        Panel(
            room_content,
            title=f"[bold cyan]{state.room}[/]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    if debug:
        # Debug mode: show technical details (IDs, actions, directions)
        layout_table = Table.grid(expand=True)
        layout_table.add_column(ratio=1)
        layout_table.add_column(ratio=1)

        # Visible objects with IDs and actions
        if state.visible_objects:
            obj_table = Table(title="Visible Objects", box=box.SIMPLE, show_header=True)
            obj_table.add_column("Object", style="green")
            obj_table.add_column("Actions", style="dim")
            for obj in state.visible_objects:
                actions = ", ".join(obj.behaviors[:5])
                if len(obj.behaviors) > 5:
                    actions += "..."
                obj_table.add_row(f"{obj.id}", actions)
        else:
            obj_table = Text("No objects visible", style="dim italic")

        # Exits with directions
        if state.exits:
            exit_table = Table(title="Exits", box=box.SIMPLE, show_header=True)
            exit_table.add_column("Direction", style="yellow")
            exit_table.add_column("Destination", style="dim")
            for direction, dest in state.exits.items():
                exit_table.add_row(direction, dest)
        else:
            exit_table = Text("No exits", style="dim italic")

        layout_table.add_row(obj_table, exit_table)
        console.print(layout_table)

        # Inventory with IDs
        if state.inventory:
            inv_items = ", ".join(f"[magenta]{obj.id}[/]" for obj in state.inventory)
            console.print(f"[bold]Inventory:[/] {inv_items}")
        else:
            console.print("[bold]Inventory:[/] [dim italic]empty[/]")
    else:
        # Normal mode: natural display without implementation details
        # Nearby rooms
        if state.nearby_rooms:
            nearby = ", ".join(r.description for r in state.nearby_rooms)
            console.print(f"[bold]Nearby:[/] {nearby}")

        # Inventory with descriptions
        if state.inventory:
            inv_items = ", ".join(f"[magenta]{obj.description}[/]" for obj in state.inventory)
            console.print(f"[bold]Inventory:[/] {inv_items}")
        else:
            console.print("[bold]Inventory:[/] [dim italic]empty[/]")

    console.print()


def render_response(response_text: str, action_results: list[str]) -> None:
    """Render agent response and action results."""
    if response_text:
        console.print(
            Panel(
                Markdown(response_text),
                border_style="blue",
                box=box.ROUNDED,
            )
        )

    for result in action_results:
        if "Blocked:" in result:
            console.print(f"[yellow]{result}[/]")
        elif "Error:" in result:
            console.print(f"[red]{result}[/]")
        else:
            console.print(f"[green]{result}[/]")


def _debug_log(title: str, content: str, style: str = "dim") -> None:
    """Print debug information in a styled panel."""
    console.print(
        Panel(
            Syntax(content, "lisp", theme="monokai", word_wrap=True)
            if content.startswith("(")
            else Text(content),
            title=f"[bold {style}]{title}[/]",
            border_style=style,
            box=box.SIMPLE,
        )
    )


@dataclass
class TurnRecord:
    """Compact record of a player turn for history."""

    room: str
    player_command: str
    actions: list[str]  # e.g., ["took @carton", "moved north"]
    narrative: str  # LLM's final response

    def to_summary(self) -> str:
        """Generate a one-line summary of this turn."""
        actions_str = ", ".join(self.actions) if self.actions else "no actions"
        return f"[{self.room}] {self.player_command} → {actions_str}"


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

    def _build_messages(self, current_state: GameState, player_command: str) -> list[dict[str, Any]]:
        """
        Build fresh message list for LLM from history + current state.

        Structure:
        1. System prompt
        2. Recent turn history (as user/assistant pairs)
        3. Current game state + player command
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        # Add recent turn history
        for turn in self.turn_history[-self.max_history_turns:]:
            # User message: summary of what happened
            messages.append({
                "role": "user",
                "content": f"[Previous turn in {turn.room}]\nPlayer: {turn.player_command}"
            })
            # Assistant response
            messages.append({
                "role": "assistant",
                "content": turn.narrative
            })

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

    def get_state_context(self) -> str:
        """Get current game state as context string for agent."""
        return self.get_state().to_context_string()

    def process_input(self, user_input: str, max_iterations: int = 10) -> tuple[str, list[str]]:
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

        Returns:
            Tuple of (response text, action results list)
        """
        # Get initial state and build base messages from history
        initial_state = self.get_state()
        initial_room = initial_state.room

        if self.debug:
            _debug_log("Game State (structured)", self._format_state_debug(initial_state), style="cyan")

        # Build fresh messages: history + current state + command
        working_messages = self._build_messages(initial_state, user_input)

        all_results: list[str] = []
        all_actions: list[str] = []  # Track actions for TurnRecord
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
                result = self._execute_tool(tool_call)
                iteration_results.append((tool_call.id, result))
                all_results.append(result)

                # Track action for history
                action_summary = self._summarize_tool_call(tool_call)
                all_actions.append(action_summary)

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
                _debug_log("Updated Game State", self._format_state_debug(state), style="cyan")

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
        """Format game state for debug display."""
        lines = [
            f"room: {state.room!r}",
            f"room_description: {state.room_description[:80]!r}..."
            if len(state.room_description) > 80
            else f"room_description: {state.room_description!r}",
            f"exits: {state.exits!r}",
            f"vehicle: {state.vehicle!r}",
            "",
            "visible_objects:",
        ]
        for obj in state.visible_objects:
            lines.append(f"  - {obj.id}: {obj.description!r}")
            lines.append(f"    behaviors: {obj.behaviors}")
        if not state.visible_objects:
            lines.append("  (none)")

        lines.append("")
        lines.append("inventory:")
        for obj in state.inventory:
            lines.append(f"  - {obj.id}: {obj.description!r}")
        if not state.inventory:
            lines.append("  (empty)")

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


def play_game(game_path: str, debug: bool = False) -> None:
    """Run an interactive game session with rich terminal UI."""
    console.print(f"[bold]Loading game:[/] {game_path}")
    if debug:
        console.print("[dim yellow]Debug mode enabled[/]")

    session = GameSession.from_game_file(game_path, debug=debug)

    console.print()
    console.rule("[bold cyan]Game Start[/]")
    console.print()

    # Show initial state
    initial_state = session.get_state()
    if debug:
        _debug_log("Game State (structured)", session._format_state_debug(initial_state), style="cyan")
    render_game_state(initial_state, debug=debug)

    console.print("[dim]Type your commands in natural language. Type 'quit' to exit.[/]\n")

    while True:
        try:
            console.print("[bold green]>[/] ", end="")
            user_input = input()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold]Goodbye![/]")
            break

        if not user_input.strip():
            continue

        if user_input.strip().lower() in ("quit", "exit", "q"):
            console.print("[bold]Goodbye![/]")
            break

        console.print()

        if debug:
            # Don't use status spinner in debug mode - it interferes with output
            response_text, results = session.process_input(user_input.strip())
        else:
            with console.status("[bold blue]Thinking...[/]"):
                response_text, results = session.process_input(user_input.strip())

        render_response(response_text, results)
        console.print()
        render_game_state(session.get_state(), debug=debug)
