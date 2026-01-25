"""
Automatic subproblem decomposition via backward chaining.

Given a goal state, traces back through effect analysis to find:
1. What behaviors can achieve the goal
2. What preconditions those behaviors require
3. Recursively, what behaviors achieve those preconditions

Produces a dependency graph of subproblems.
"""

from dataclasses import dataclass, field
from typing import Any

from grue import GrueWorld
from .effects import (
    EffectAnalysis, StateRef, BehaviorRef,
    PropertyRef, LocationRef, HeldRef, QueueRef,
    analyze_effects
)


@dataclass
class Goal:
    """A goal state to achieve."""
    ref: StateRef
    value: Any

    def __str__(self):
        return f"{self.ref} = {self.value}"

    def __hash__(self):
        return hash((self.ref, self.value))

    def __eq__(self, other):
        return isinstance(other, Goal) and self.ref == other.ref and self.value == other.value


@dataclass
class Subproblem:
    """A subproblem identified during decomposition."""
    name: str
    goal: Goal
    achievers: list[BehaviorRef]  # Behaviors that can achieve this goal
    preconditions: set[Goal]  # Goals that must be achieved first
    is_initial: bool = False  # True if goal is satisfied in initial state

    def __str__(self):
        if self.is_initial:
            return f"{self.name}: {self.goal} [INITIAL]"
        achiever_str = ", ".join(str(a) for a in self.achievers)
        return f"{self.name}: {self.goal} <- [{achiever_str}]"


@dataclass
class DecompositionResult:
    """Result of decomposing a goal into subproblems."""
    root_goal: Goal
    subproblems: dict[Goal, Subproblem]
    edges: list[tuple[Goal, Goal]]  # (from_goal, to_goal) = from depends on to

    def summary(self) -> str:
        lines = [f"=== Decomposition: {self.root_goal} ===", ""]

        # Group by depth (BFS order)
        visited = set()
        queue = [self.root_goal]
        depth = {self.root_goal: 0}

        while queue:
            goal = queue.pop(0)
            if goal in visited:
                continue
            visited.add(goal)

            sp = self.subproblems.get(goal)
            if sp:
                indent = "  " * depth[goal]
                lines.append(f"{indent}{sp}")
                for precond in sp.preconditions:
                    if precond not in depth:
                        depth[precond] = depth[goal] + 1
                        queue.append(precond)

        lines.append("")
        lines.append(f"Total subproblems: {len(self.subproblems)}")
        initial_count = sum(1 for sp in self.subproblems.values() if sp.is_initial)
        lines.append(f"Initial (leaf) nodes: {initial_count}")

        return "\n".join(lines)

    def to_dot(self) -> str:
        """Generate DOT graph of subproblem dependencies."""
        lines = [
            "digraph decomposition {",
            '  rankdir=BT;',  # Bottom to top (goals at top)
            '  node [shape=box fontsize=10 fontname="Helvetica"];',
            "",
        ]

        # Node definitions
        for goal, sp in self.subproblems.items():
            label = str(goal).replace("@", "").replace(":", "\\n")
            node_id = self._goal_id(goal)

            if goal == self.root_goal:
                style = 'style=filled fillcolor=palegreen'
            elif sp.is_initial:
                style = 'style=filled fillcolor=lightblue'
            else:
                style = ''

            lines.append(f'  {node_id} [label="{label}" {style}];')

        lines.append("")

        # Edges (from depends on to)
        for from_goal, to_goal in self.edges:
            from_id = self._goal_id(from_goal)
            to_id = self._goal_id(to_goal)
            lines.append(f'  {from_id} -> {to_id};')

        lines.append("}")
        return "\n".join(lines)

    def _goal_id(self, goal: Goal) -> str:
        """Generate a valid DOT node ID for a goal."""
        s = str(goal.ref).replace("@", "").replace(":", "_").replace("-", "_")
        v = str(goal.value).replace("@", "").replace("-", "_")
        return f"g_{s}_{v}"


class Decomposer:
    """Decomposes goals into subproblems via backward chaining."""

    def __init__(self, world: GrueWorld, effects: EffectAnalysis | None = None):
        self.world = world
        self.effects = effects or analyze_effects(world)
        self.subproblems: dict[Goal, Subproblem] = {}
        self.edges: list[tuple[Goal, Goal]] = []
        self._counter = 0
        # Build room connectivity map: dest_room -> list of barriers
        self._room_barriers: dict[str, list[str]] = self._build_room_barriers()

    def _build_room_barriers(self) -> dict[str, list[str]]:
        """Build map from destination rooms to barriers that gate entry."""
        result: dict[str, list[str]] = {}
        for room_name, room in self.world.rooms.items():
            for exit in room.exits:
                if exit.via:  # Has a barrier
                    dest = exit.to
                    if dest not in result:
                        result[dest] = []
                    if exit.via not in result[dest]:
                        result[dest].append(exit.via)
        return result

    def _barrier_preconditions(self, dest_room: str) -> set[Goal]:
        """Get preconditions from barriers gating entry to a room.

        Analyzes the :through behavior of each barrier to find what state
        it reads, then converts those reads to goal preconditions.
        """
        goals: set[Goal] = set()
        barriers = self._room_barriers.get(dest_room, [])

        for barrier_name in barriers:
            through_ref = BehaviorRef(barrier_name, 'through')

            # Find what the barrier's :through behavior reads
            for ref, readers in self.effects.reads.items():
                if through_ref not in readers:
                    continue

                # Convert reads to preconditions based on property type
                if isinstance(ref, PropertyRef):
                    # Boolean properties: rmung, broken, freed, mounted, severed, etc.
                    # Assume they need to be True (barrier is passable when condition met)
                    if ref.property in ('rmung', 'broken', 'freed', 'mounted', 'severed', 'open'):
                        goals.add(Goal(ref, True))
                    # Skip other properties we can't infer values for
                    # (e.g., 'person' - just checking if something is a person)

                # LocationRef - barrier checks if something is at a location
                # Skip these - they're usually checking NPC positions which are
                # either initial state or need deeper analysis
                # (e.g., @maintenance-man:location, @floor-waxer:location)

        return goals

    def decompose(self, goal: Goal, max_depth: int = 10) -> DecompositionResult:
        """Decompose a goal into subproblems."""
        self.subproblems = {}
        self.edges = []
        self._counter = 0

        self._decompose_recursive(goal, depth=0, max_depth=max_depth)

        return DecompositionResult(
            root_goal=goal,
            subproblems=self.subproblems,
            edges=self.edges,
        )

    def _decompose_recursive(self, goal: Goal, depth: int, max_depth: int) -> Subproblem:
        """Recursively decompose a goal."""
        # Already processed?
        if goal in self.subproblems:
            return self.subproblems[goal]

        # Check if goal is satisfied in initial state
        initial_value = self._get_initial_value(goal.ref)
        if initial_value == goal.value:
            sp = Subproblem(
                name=f"sp{self._counter}",
                goal=goal,
                achievers=[],
                preconditions=set(),
                is_initial=True,
            )
            self._counter += 1
            self.subproblems[goal] = sp
            return sp

        # Find behaviors that can achieve this goal
        achievers = self._what_achieves(goal.ref, goal.value)

        # Find preconditions for each achiever
        all_preconditions: set[Goal] = set()
        for behavior in achievers:
            preconds = self._preconditions_for(behavior, achieving=goal)
            all_preconditions.update(preconds)

        sp = Subproblem(
            name=f"sp{self._counter}",
            goal=goal,
            achievers=achievers,
            preconditions=all_preconditions,
        )
        self._counter += 1
        self.subproblems[goal] = sp

        # Recursively decompose preconditions
        if depth < max_depth:
            for precond in all_preconditions:
                self.edges.append((goal, precond))
                self._decompose_recursive(precond, depth + 1, max_depth)

        return sp

    def _what_achieves(self, ref: StateRef, target_value: Any) -> list[BehaviorRef]:
        """Find behaviors that can set ref to target_value."""
        if ref not in self.effects.modifies_to:
            return []

        result = []
        for behavior, values in self.effects.modifies_to[ref].items():
            # Direct match - behavior explicitly sets to target value
            if target_value in values:
                result.append(behavior)
            # None means variable/unknown value - need careful handling
            elif None in values:
                # Special case: runtime:go can achieve any room for @player:location
                if (isinstance(ref, LocationRef) and ref.object == '@player' and
                    behavior.object == 'runtime' and behavior.verb == 'go'):
                    # Check if target is a valid room
                    if target_value in self.world.rooms:
                        result.append(behavior)
                    continue

                # For other LocationRef targets, only match None if target is @player
                # (runtime:take/drop put things at player's location, not specific rooms)
                if isinstance(ref, LocationRef) and target_value != '@player':
                    continue  # Skip - drop/take can't achieve specific non-player locations
                result.append(behavior)
        return result

    def _preconditions_for(self, behavior: BehaviorRef, achieving: Goal | None = None) -> set[Goal]:
        """Find goals that must be satisfied for a behavior to succeed.

        This is a simplified version - we know what state is READ but not
        what VALUE is required. For now, we make educated guesses based on
        common patterns.

        Args:
            behavior: The behavior to find preconditions for
            achieving: The goal this behavior is achieving (filtered from results
                       to avoid circular dependencies)
        """
        goals = set()

        # Any behavior achieving @X:location = @player (pickup) requires player
        # to be in the same room as the object. This applies to runtime:take,
        # object-specific :take behaviors, and other transfer effects.
        if (achieving is not None and isinstance(achieving.ref, LocationRef) and
            achieving.value == '@player' and achieving.ref.object != '@player'):
            obj_name = achieving.ref.object
            obj_loc = self._get_object_room(obj_name)
            if obj_loc and obj_loc != '@player':
                # Player needs to be in the room where the object is
                goals.add(Goal(LocationRef('@player'), obj_loc))

        # Special case: runtime:go achieving @player:location = <room>
        # Add preconditions from barriers gating entry to that room
        is_runtime_go = (behavior.object == 'runtime' and behavior.verb == 'go')
        if (is_runtime_go and achieving is not None and
            isinstance(achieving.ref, LocationRef) and achieving.ref.object == '@player'):
            dest_room = achieving.value
            if dest_room in self.world.rooms:
                goals.update(self._barrier_preconditions(dest_room))

        for ref, readers in self.effects.reads.items():
            if behavior not in readers:
                continue

            # For LocationRef, assume we need the object held (for most actions)
            if isinstance(ref, LocationRef):
                # Special case: player location just means "be somewhere"
                if ref.object == '@player':
                    continue
                # Skip location reads for runtime:go - they check NPC/obstacle positions
                if is_runtime_go:
                    continue
                # Skip objects that can't be taken (vehicles, scenery, rooms, etc.)
                if not self._is_takeable(ref.object):
                    continue
                # Assume we need to hold the object
                goals.add(Goal(ref, '@player'))

            # For PropertyRef, guess based on common patterns
            elif isinstance(ref, PropertyRef):
                # Skip property preconditions for runtime:go - they're room-specific
                if is_runtime_go:
                    continue
                # rmung usually needs to be True (thing is destroyed/open)
                if ref.property == 'rmung':
                    goals.add(Goal(ref, True))
                # wearable usually needs to be True
                elif ref.property == 'wearable':
                    goals.add(Goal(ref, True))
                # For others, we'd need deeper analysis of the conditionals

        # Add preconditions from required action arguments
        # E.g., @high-voltage:cut requires @axe, so player must hold the axe
        if behavior in self.effects.required_args:
            for obj_name in self.effects.required_args[behavior]:
                # Only add as precondition if it's a takeable object
                if self._is_takeable(obj_name):
                    goals.add(Goal(LocationRef(obj_name), '@player'))

        # Filter out the goal we're trying to achieve - behaviors often read
        # the state they modify (e.g., to check "not already done")
        if achieving is not None:
            goals.discard(achieving)

        return goals

    def _get_object_room(self, obj_name: str) -> str | None:
        """Get the room where an object is located (traversing containers)."""
        obj = self.world.objects.get(obj_name)
        if not obj:
            return None

        loc = obj.location
        # Traverse up through containers to find the room
        visited = set()
        while loc and loc not in visited:
            visited.add(loc)
            if loc in self.world.rooms:
                return loc
            # Check if it's an object (container)
            container = self.world.objects.get(loc)
            if container:
                loc = container.location
            else:
                break
        return loc

    def _is_takeable(self, obj_name: str) -> bool:
        """Check if an object can be taken by the player."""
        # Rooms, events, and special objects can't be taken
        if obj_name in self.world.rooms:
            return False

        obj = self.world.objects.get(obj_name)
        if not obj:
            return False

        # Objects in @global are abstract (body parts, etc.) - not takeable
        if obj.location == '@global':
            return False

        # Objects with these properties typically can't be taken
        non_takeable_props = {'vehicle', 'scenery', 'static', 'person', 'creature',
                              'nodesc'}  # nodesc=abstract/hidden things
        for prop in non_takeable_props:
            if obj.properties.get(prop):
                return False

        # Check if there's a take behavior that prevents taking
        # (we can't easily tell, so assume takeable if not blocked)
        return True

    def _get_initial_value(self, ref: StateRef) -> Any:
        """Get the initial value of a state reference."""
        if isinstance(ref, LocationRef):
            obj = self.world.objects.get(ref.object)
            if obj:
                return obj.location
            room = self.world.rooms.get(ref.object)
            if room:
                return None  # Rooms don't have locations

        elif isinstance(ref, PropertyRef):
            obj = self.world.objects.get(ref.object)
            if obj:
                return obj.properties.get(ref.property)
            room = self.world.rooms.get(ref.object)
            if room:
                return room.properties.get(ref.property)

        elif isinstance(ref, QueueRef):
            # Events start unqueued
            return None

        return None


def decompose_goal(
    world: GrueWorld,
    ref: StateRef,
    value: Any,
    effects: EffectAnalysis | None = None,
    max_depth: int = 10,
) -> DecompositionResult:
    """Convenience function to decompose a goal."""
    decomposer = Decomposer(world, effects)
    return decomposer.decompose(Goal(ref, value), max_depth)


# CLI entry point
def main():
    """Command-line interface for decomposition."""
    import sys
    from pathlib import Path
    from grue import load_grue

    if len(sys.argv) < 2:
        print("Usage: python -m frotz.decompose <game_path> [--dot output.dot]")
        print()
        print("Decomposes the victory condition into subproblems.")
        sys.exit(1)

    game_path = Path(sys.argv[1])
    dot_output = None

    if "--dot" in sys.argv:
        dot_idx = sys.argv.index("--dot")
        if dot_idx + 1 < len(sys.argv):
            dot_output = sys.argv[dot_idx + 1]

    world = load_grue(str(game_path))
    effects = analyze_effects(world)

    print(f"Decomposing: {world.name or game_path}")
    print()

    # For now, use a hardcoded goal for testing
    # TODO: Extract from victory condition
    goal_ref = LocationRef('@high-voltage')
    goal_value = '@input-socket'

    result = decompose_goal(world, goal_ref, goal_value, effects, max_depth=5)
    print(result.summary())

    if dot_output:
        Path(dot_output).write_text(result.to_dot())
        print(f"\nDOT graph written to: {dot_output}")


if __name__ == "__main__":
    main()
