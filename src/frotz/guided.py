"""
Heuristic-guided state space exploration for Grue games.

Replaces exhaustive BFS with:
1. Greedy best-first search toward terminal states (victory/defeat)
2. Backward constraint propagation for black hole detection

Key insight: We only need to find *a* path, not the optimal path.
This allows aggressive pruning and greedy strategies.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from heapq import heappush, heappop
from typing import Any

from grue import GrueWorld
from grue.runtime import GrueRuntime
from grue.sexpr import SList, Symbol, Keyword

from .effects import StateRef, PropertyRef, LocationRef, QueueRef, EffectAnalysis
from .relevance import RelevanceAnalysis
from .explorer import Action, GameState


@dataclass
class TerminalCondition:
    """A terminal condition (victory or defeat) with its goal state.

    The goal is represented as a set of constraints that must be satisfied.
    Each constraint is (StateRef, target_value).
    """
    name: str
    is_victory: bool
    when: Any  # The Grue expression
    constraints: dict[StateRef, Any] = field(default_factory=dict)

    def distance(self, state: GameState) -> float:
        """Compute distance from state to this terminal condition.

        Returns a score where 0 = at terminal, higher = further away.
        """
        if not self.constraints:
            return float('inf')  # Can't compute distance without constraints

        state_dict = dict(state.values)
        matched = 0
        total = len(self.constraints)

        for ref, target in self.constraints.items():
            ref_str = str(ref)
            if ref_str in state_dict:
                current = state_dict[ref_str]
                # Handle comparison constraints (operator, threshold)
                if isinstance(target, tuple) and len(target) == 2:
                    op, threshold = target
                    if self._check_comparison(current, op, threshold):
                        matched += 1
                # Handle equality constraints
                elif self._values_equal(current, target):
                    matched += 1
                # Could add partial scoring for "closer" values later

        # Distance is fraction of unsatisfied constraints
        return (total - matched) / total if total > 0 else 0.0

    @staticmethod
    def _values_equal(current: Any, target: Any) -> bool:
        """Check if two values are equal, handling nil/None equivalence."""
        if current == target:
            return True
        # Handle nil/None equivalence
        nil_values = (None, "nil")
        if current in nil_values and target in nil_values:
            return True
        return False

    @staticmethod
    def _check_comparison(current: Any, op: str, threshold: Any) -> bool:
        """Check if current value satisfies comparison constraint."""
        if not isinstance(current, (int, float)) or not isinstance(threshold, (int, float)):
            return False
        if op == ">=":
            return current >= threshold
        elif op == ">":
            return current > threshold
        elif op == "<=":
            return current <= threshold
        elif op == "<":
            return current < threshold
        return False


def compute_relevance_distance(
    state: GameState,
    relevance: RelevanceAnalysis,
    effects: EffectAnalysis,
) -> float:
    """Compute a heuristic distance based on how much relevant state has changed.

    This captures "progress toward victory" by looking at:
    1. How many precondition states are in their "enablement" position
    2. Blockers that have been cleared (locked doors unlocked, etc.)

    The intuition: relevant state that has been modified from initial values
    suggests progress is being made.
    """
    state_dict = dict(state.values)

    # Count relevant states that are in "good" positions
    # For booleans: unlocked/open/etc are "progress" states
    # For locations: items held by player or in player's room
    progress_count = 0
    total_relevant = len(relevance.relevant)

    for ref in relevance.relevant:
        ref_str = str(ref)
        if ref_str not in state_dict:
            continue

        val = state_dict[ref_str]

        if isinstance(ref, PropertyRef):
            # Heuristic: False for "blocking" properties is good
            # (locked=False, closed->open, etc.)
            # True for "progress" properties
            if ref.property in ("locked", "lost", "dead"):
                if val is False:
                    progress_count += 1
            elif ref.property in ("open",):
                if val is True:
                    progress_count += 1
            # Numeric properties: higher might be progress (lever pulls)
            elif isinstance(val, int) and val > 0:
                progress_count += 0.5  # Partial credit

        elif isinstance(ref, LocationRef):
            # Items held by player are progress (usually)
            if val == "@player":
                progress_count += 1

    # Return inverse of progress (lower = better)
    if total_relevant == 0:
        return 0.0
    return 1.0 - (progress_count / total_relevant)


def extract_terminal_constraints(
    expr: Any,
    world: GrueWorld,
) -> dict[StateRef, Any]:
    """Extract goal constraints from a terminal condition expression.

    For example, from (= (loc @frob) nil), extract:
        {LocationRef("@frob"): None}

    From (and (= (loc @player) @outside) (= (loc @gem) @player)), extract:
        {LocationRef("@player"): "@outside", LocationRef("@gem"): "@player"}
    """
    constraints: dict[StateRef, Any] = {}
    _extract_constraints_recursive(expr, constraints)
    return constraints


def _extract_constraints_recursive(expr: Any, constraints: dict[StateRef, Any]):
    """Recursively extract constraints from an expression."""
    if not isinstance(expr, SList) or not expr.items:
        return

    items = expr.items
    head = items[0]

    if not isinstance(head, Symbol):
        return

    name = head.name

    # (= left right) - equality constraint
    if name == "=" and len(items) == 3:
        left, right = items[1], items[2]

        # (= (loc @obj) value)
        if isinstance(left, SList) and left.items:
            left_head = left.items[0]
            if isinstance(left_head, Symbol) and left_head.name == "loc":
                if len(left.items) >= 2:
                    obj = left.items[1]
                    if isinstance(obj, Symbol) and obj.name.startswith("@"):
                        ref = LocationRef(obj.name)
                        # Extract target value
                        if isinstance(right, Symbol):
                            if right.name == "nil":
                                constraints[ref] = None
                            else:
                                constraints[ref] = right.name
                        elif right is None:
                            constraints[ref] = None
                        return

            # (:prop @obj) = value
            if isinstance(left_head, Keyword):
                if len(left.items) >= 2:
                    obj = left.items[1]
                    if isinstance(obj, Symbol) and obj.name.startswith("@"):
                        ref = PropertyRef(obj.name, left_head.name)
                        if isinstance(right, Symbol):
                            if right.name in ("true", "false"):
                                constraints[ref] = right.name == "true"
                            elif right.name == "nil":
                                constraints[ref] = None
                            else:
                                constraints[ref] = right.name
                        elif isinstance(right, bool):
                            constraints[ref] = right
                        elif isinstance(right, (int, float, str)):
                            constraints[ref] = right
                        return

        # Also handle right side being the function call
        if isinstance(right, SList) and right.items:
            # Swap and recurse - (= value (loc @obj)) is same as (= (loc @obj) value)
            swapped = SList([head, right, left])
            _extract_constraints_recursive(swapped, constraints)
            return

    # (and ...) - conjunction
    if name == "and":
        for item in items[1:]:
            _extract_constraints_recursive(item, constraints)
        return

    # (>= left right), (> left right), (<= left right), (< left right) - comparison constraints
    # For these, we extract the property ref but the "target" is a threshold, not exact value
    # For now, we treat (>= (:prop @obj) N) as "prop should be at least N"
    if name in (">=", ">", "<=", "<") and len(items) == 3:
        left, right = items[1], items[2]

        # (:prop @obj) compared to value
        if isinstance(left, SList) and left.items:
            left_head = left.items[0]
            if isinstance(left_head, Keyword):
                if len(left.items) >= 2:
                    obj = left.items[1]
                    if isinstance(obj, Symbol) and obj.name.startswith("@"):
                        ref = PropertyRef(obj.name, left_head.name)
                        # Store with comparison operator for distance calculation
                        # For now, just store the threshold value
                        if isinstance(right, (int, float)):
                            # Store as (operator, value) tuple
                            constraints[ref] = (name, right)
                        return
        return

    # (:prop @obj) - property read (interpreted as "should be truthy")
    # This is a weak constraint, skip for now

    # (held? @obj) - means loc(@obj) = @player (but we don't know player name here)
    # Skip for now, could be enhanced later


@dataclass
class SearchNode:
    """A node in the search tree."""
    priority: float  # Lower = better (distance to terminal)
    state: GameState
    path: list[Action]
    depth: int

    def __lt__(self, other: "SearchNode"):
        return self.priority < other.priority


@dataclass
class SearchResult:
    """Result of guided search."""
    found_terminal: bool
    terminal_type: str | None  # "victory" or "defeat"
    terminal_name: str | None
    path: list[Action]
    states_explored: int
    max_depth_reached: int


class GuidedExplorer:
    """Heuristic-guided state space explorer.

    Uses greedy best-first search with distance-to-terminal as heuristic.
    """

    def __init__(
        self,
        world: GrueWorld,
        relevance: RelevanceAnalysis,
        effects: EffectAnalysis | None = None,
        max_depth: int = 100,
        patience: int = 10,
    ):
        self.world = world
        self.relevance = relevance
        self.effects = effects
        self.max_depth = max_depth
        self.patience = patience  # Steps without improvement before giving up
        self._runtime = GrueRuntime(world)

        # Extract terminal conditions
        self.terminals: list[TerminalCondition] = []
        self._extract_terminals()

    def _extract_terminals(self):
        """Extract victory and defeat conditions with their constraints."""
        if self.world.victory:
            constraints = extract_terminal_constraints(
                self.world.victory.when, self.world
            )
            self.terminals.append(TerminalCondition(
                name="victory",
                is_victory=True,
                when=self.world.victory.when,
                constraints=constraints,
            ))

        if self.world.defeat:
            for defeat_name, defeat in self.world.defeat.items():
                constraints = extract_terminal_constraints(defeat.when, self.world)
                self.terminals.append(TerminalCondition(
                    name=defeat_name,
                    is_victory=False,
                    when=defeat.when,
                    constraints=constraints,
                ))

    def find_path_to_victory(self) -> SearchResult:
        """Find a path to any victory state using best-first search."""
        victory_terminals = [t for t in self.terminals if t.is_victory]
        if not victory_terminals:
            return SearchResult(
                found_terminal=False,
                terminal_type=None,
                terminal_name=None,
                path=[],
                states_explored=0,
                max_depth_reached=0,
            )

        return self._search(victory_terminals)

    def find_path_to_defeat(self) -> SearchResult:
        """Find a path to any defeat state using best-first search."""
        defeat_terminals = [t for t in self.terminals if not t.is_victory]
        if not defeat_terminals:
            return SearchResult(
                found_terminal=False,
                terminal_type=None,
                terminal_name=None,
                path=[],
                states_explored=0,
                max_depth_reached=0,
            )

        return self._search(defeat_terminals)

    def find_any_terminal(self) -> SearchResult:
        """Find a path to any terminal state (victory or defeat)."""
        if not self.terminals:
            return SearchResult(
                found_terminal=False,
                terminal_type=None,
                terminal_name=None,
                path=[],
                states_explored=0,
                max_depth_reached=0,
            )

        return self._search(self.terminals)

    def _search(self, targets: list[TerminalCondition]) -> SearchResult:
        """Run best-first search toward any of the target terminals."""
        self._runtime.reset()

        initial_state = GameState.from_runtime(self._runtime, self.relevance.relevant)

        # Check if already at a terminal
        if self._runtime.check_victory():
            return SearchResult(
                found_terminal=True,
                terminal_type="victory",
                terminal_name="victory",
                path=[],
                states_explored=1,
                max_depth_reached=0,
            )
        if self._runtime.check_defeat():
            return SearchResult(
                found_terminal=True,
                terminal_type="defeat",
                terminal_name=self._get_defeat_name(),
                path=[],
                states_explored=1,
                max_depth_reached=0,
            )

        # Priority queue: (distance, node)
        initial_dist = self._min_distance(initial_state, targets)
        heap: list[SearchNode] = []
        heappush(heap, SearchNode(
            priority=initial_dist,
            state=initial_state,
            path=[],
            depth=0,
        ))

        visited: set[GameState] = {initial_state}
        states_explored = 1
        max_depth = 0

        # Track best distances for plateau detection
        best_distance = initial_dist
        steps_without_improvement = 0

        while heap:
            node = heappop(heap)

            if node.depth > max_depth:
                max_depth = node.depth

            # Depth limit
            if node.depth >= self.max_depth:
                continue

            # Restore state by replaying path
            self._replay_path(node.path)

            # Get all actions from this state
            actions = self._enumerate_actions()

            for action in actions:
                saved = self._save_state()

                result = self._runtime.do(action.target, action.verb, *action.args)

                if result.outcome == "success":
                    self._runtime.process_events()

                    # Check for terminal
                    if self._runtime.check_victory():
                        return SearchResult(
                            found_terminal=True,
                            terminal_type="victory",
                            terminal_name="victory",
                            path=node.path + [action],
                            states_explored=states_explored,
                            max_depth_reached=max_depth,
                        )
                    if self._runtime.check_defeat():
                        # Only return defeat if we're searching for it
                        if any(not t.is_victory for t in targets):
                            return SearchResult(
                                found_terminal=True,
                                terminal_type="defeat",
                                terminal_name=self._get_defeat_name(),
                                path=node.path + [action],
                                states_explored=states_explored,
                                max_depth_reached=max_depth,
                            )

                    new_state = GameState.from_runtime(
                        self._runtime, self.relevance.relevant
                    )

                    if new_state not in visited:
                        visited.add(new_state)
                        states_explored += 1

                        dist = self._min_distance(new_state, targets)
                        new_path = node.path + [action]

                        heappush(heap, SearchNode(
                            priority=dist,
                            state=new_state,
                            path=new_path,
                            depth=node.depth + 1,
                        ))

                        # Track improvement
                        if dist < best_distance:
                            best_distance = dist
                            steps_without_improvement = 0
                        else:
                            steps_without_improvement += 1

                self._restore_state(saved)

            # Plateau detection - give up on this search if no progress
            # (This is checked per-expansion, not per-node)
            if steps_without_improvement > self.patience * len(actions):
                break

        return SearchResult(
            found_terminal=False,
            terminal_type=None,
            terminal_name=None,
            path=[],
            states_explored=states_explored,
            max_depth_reached=max_depth,
        )

    def _min_distance(self, state: GameState, targets: list[TerminalCondition]) -> float:
        """Compute minimum distance to any target terminal.

        Combines:
        1. Direct terminal constraint distance (exact goal match)
        2. Relevance-based progress heuristic (intermediate progress)

        The combined score guides search toward both the goal and
        intermediate states that enable reaching the goal.
        """
        if not targets:
            return float('inf')

        # Direct terminal distance
        terminal_dist = min(t.distance(state) for t in targets)

        # Relevance-based progress (inverse of progress made)
        if self.effects is not None:
            progress_dist = compute_relevance_distance(
                state, self.relevance, self.effects
            )
            # Combine: weight terminal distance more heavily, but use progress
            # as a tiebreaker when terminal distance is flat
            return terminal_dist * 2 + progress_dist
        else:
            return terminal_dist

    def _get_defeat_name(self) -> str:
        """Get the name of the current defeat condition (if any)."""
        # Check which defeat condition matches
        if self.world.defeat:
            for name, defeat in self.world.defeat.items():
                # Would need to evaluate defeat.when - for now just return first
                return name
        return "unknown"

    def _replay_path(self, path: list[Action]):
        """Restore runtime to a state by replaying actions from initial."""
        self._runtime.reset()
        for action in path:
            self._runtime.do(action.target, action.verb, *action.args)
            self._runtime.process_events()

    def _enumerate_actions(self) -> list[Action]:
        """Enumerate all valid actions from current state."""
        actions = []

        visible = self._runtime.get_visible_objects()
        inventory = self._runtime.get_inventory()
        player_room = self._runtime.get_player_room()

        for obj_name in visible:
            if obj_name not in self.world.objects:
                continue

            obj = self.world.objects[obj_name]
            if not hasattr(obj, 'behaviors') or not obj.behaviors:
                continue

            for behavior in obj.behaviors:
                verb = behavior.verb

                # Skip internal verbs
                if verb in ("through", "describe", "fdesc"):
                    continue

                if not behavior.params:
                    actions.append(Action(target=obj_name, verb=verb))
                else:
                    # Has parameters - enumerate argument combinations
                    arg_candidates = list(set(visible) | set(inventory))

                    if len(behavior.params) == 1:
                        for arg in arg_candidates:
                            actions.append(Action(target=obj_name, verb=verb, args=(arg,)))
                    elif len(behavior.params) == 2:
                        for arg1 in arg_candidates:
                            for arg2 in arg_candidates:
                                actions.append(Action(target=obj_name, verb=verb, args=(arg1, arg2)))

        # Movement actions
        if player_room and player_room in self.world.rooms:
            room_def = self.world.rooms[player_room]
            for exit_info in room_def.exits:
                actions.append(Action(
                    target=player_room,
                    verb="go",
                    args=(exit_info.direction,)
                ))

        return actions

    def _save_state(self) -> dict:
        """Save runtime state for later restoration."""
        return {
            "objects": deepcopy(self._runtime.state.objects),
            "queues": deepcopy(self._runtime.state.queues),
        }

    def _restore_state(self, saved: dict):
        """Restore runtime state from a saved snapshot."""
        self._runtime.state.objects = saved["objects"]
        self._runtime.state.queues = saved["queues"]


def find_victory_path(
    world: GrueWorld,
    relevance: RelevanceAnalysis,
    effects: EffectAnalysis | None = None,
    max_depth: int = 100,
    patience: int = 10,
) -> SearchResult:
    """Convenience function to find a victory path."""
    explorer = GuidedExplorer(world, relevance, effects, max_depth, patience)
    return explorer.find_path_to_victory()


def find_defeat_path(
    world: GrueWorld,
    relevance: RelevanceAnalysis,
    effects: EffectAnalysis | None = None,
    max_depth: int = 100,
    patience: int = 10,
) -> SearchResult:
    """Convenience function to find a defeat path."""
    explorer = GuidedExplorer(world, relevance, effects, max_depth, patience)
    return explorer.find_path_to_defeat()
