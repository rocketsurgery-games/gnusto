"""
Backward constraint propagation for Grue games.

Builds abstract constraint trees from terminal conditions by working backwards:
1. Start with terminal constraints (victory/defeat requirements)
2. Find behaviors that can achieve each constraint
3. Extract preconditions for those behaviors
4. Recursively expand until we reach "primitive" states (initial conditions or constants)

This enables:
- Guided forward search toward intermediate subgoals
- Black hole detection (states where required constraints are unsatisfiable)
"""

from dataclasses import dataclass, field
from typing import Any

from grue import GrueWorld
from grue.sexpr import SList, Symbol, Keyword

from .effects import (
    EffectAnalysis,
    StateRef,
    PropertyRef,
    LocationRef,
    QueueRef,
    BehaviorRef,
)
from .relevance import RelevanceAnalysis


@dataclass
class Constraint:
    """A constraint that must be satisfied.

    Constraints can be:
    - Equality: ref = value
    - Comparison: ref >= value, ref < value, etc.
    - Existence: ref exists (for objects being somewhere)
    """
    ref: StateRef
    operator: str  # "=", ">=", ">", "<=", "<", "!="
    value: Any

    def __hash__(self):
        return hash((self.ref, self.operator, str(self.value)))

    def __str__(self):
        return f"{self.ref} {self.operator} {self.value}"

    def is_satisfied(self, current_value: Any) -> bool:
        """Check if the constraint is satisfied by a value."""
        if self.operator == "=":
            return self._values_equal(current_value, self.value)
        elif self.operator == "!=":
            return not self._values_equal(current_value, self.value)
        elif self.operator == ">=":
            return isinstance(current_value, (int, float)) and current_value >= self.value
        elif self.operator == ">":
            return isinstance(current_value, (int, float)) and current_value > self.value
        elif self.operator == "<=":
            return isinstance(current_value, (int, float)) and current_value <= self.value
        elif self.operator == "<":
            return isinstance(current_value, (int, float)) and current_value < self.value
        return False

    @staticmethod
    def _values_equal(a: Any, b: Any) -> bool:
        """Check equality with nil/None handling."""
        if a == b:
            return True
        nil_values = (None, "nil")
        if a in nil_values and b in nil_values:
            return True
        return False


@dataclass
class Achiever:
    """A way to achieve a constraint.

    An achiever is a behavior that can modify the constraint's state reference
    to satisfy the constraint. Each achiever has preconditions that must be
    satisfied before it can be executed.
    """
    behavior: BehaviorRef
    preconditions: list[Constraint] = field(default_factory=list)

    def __str__(self):
        preconds = ", ".join(str(p) for p in self.preconditions)
        return f"{self.behavior} requires [{preconds}]"


@dataclass
class ConstraintNode:
    """A node in the backward constraint tree.

    Each node represents a constraint that must be satisfied, along with
    the possible ways to achieve it (achievers) and their preconditions.
    """
    constraint: Constraint
    achievers: list[Achiever] = field(default_factory=list)
    is_initial: bool = False  # True if satisfied in initial state
    is_constant: bool = False  # True if cannot be modified
    children: dict[Constraint, "ConstraintNode"] = field(default_factory=dict)

    def __str__(self):
        if self.is_initial:
            return f"{self.constraint} [INITIAL]"
        elif self.is_constant:
            return f"{self.constraint} [CONSTANT]"
        else:
            achiever_strs = [str(a) for a in self.achievers]
            return f"{self.constraint} <- {achiever_strs}"


@dataclass
class ConstraintTree:
    """A tree of constraints rooted at a terminal condition.

    The tree represents all the ways to achieve the terminal condition,
    with intermediate subgoals as internal nodes.
    """
    root: ConstraintNode
    all_nodes: dict[Constraint, ConstraintNode] = field(default_factory=dict)

    def get_unsatisfied_leaves(self, state_values: dict[str, Any]) -> list[Constraint]:
        """Find leaf constraints that are not satisfied in the current state.

        These represent the immediate subgoals we should work toward.
        """
        unsatisfied: list[Constraint] = []
        visited: set[Constraint] = set()
        self._collect_unsatisfied(self.root, state_values, unsatisfied, visited)
        return unsatisfied

    def _collect_unsatisfied(
        self,
        node: ConstraintNode,
        state_values: dict[str, Any],
        result: list[Constraint],
        visited: set[Constraint],
    ):
        """Recursively collect unsatisfied leaf constraints."""
        # Cycle detection
        if node.constraint in visited:
            return
        visited.add(node.constraint)

        ref_str = str(node.constraint.ref)
        current_value = state_values.get(ref_str)

        if node.constraint.is_satisfied(current_value):
            # This constraint is satisfied, don't recurse
            return

        if node.is_initial or node.is_constant or not node.achievers:
            # Leaf node that's not satisfied - this is a subgoal
            result.append(node.constraint)
            return

        # Check children (preconditions of achievers)
        for child in node.children.values():
            self._collect_unsatisfied(child, state_values, result, visited)

    def is_satisfiable(self, state_values: dict[str, Any]) -> bool:
        """Check if the constraint tree can still be satisfied from current state.

        Returns False if any required constraint is permanently unsatisfiable
        (e.g., a constant that doesn't match, or a state that was irreversibly changed).
        """
        visited: set[Constraint] = set()
        return self._check_satisfiable(self.root, state_values, visited)

    def _check_satisfiable(
        self,
        node: ConstraintNode,
        state_values: dict[str, Any],
        visited: set[Constraint],
    ) -> bool:
        """Recursively check if a node's constraint is satisfiable."""
        # Cycle detection - assume cycles are satisfiable (conservative)
        if node.constraint in visited:
            return True
        visited.add(node.constraint)

        ref_str = str(node.constraint.ref)
        current_value = state_values.get(ref_str)

        # Already satisfied
        if node.constraint.is_satisfied(current_value):
            return True

        # Constant that doesn't match - unsatisfiable
        if node.is_constant:
            return False

        # Initial state that doesn't match but could be modified
        # Check if any achiever path is satisfiable
        if not node.achievers:
            # No way to achieve this - check if it's already satisfied
            return node.constraint.is_satisfied(current_value)

        # At least one achiever path must be satisfiable
        for achiever in node.achievers:
            achiever_satisfiable = True
            for precond in achiever.preconditions:
                if precond in node.children:
                    if not self._check_satisfiable(node.children[precond], state_values, visited):
                        achiever_satisfiable = False
                        break
            if achiever_satisfiable:
                return True

        return False


class BackwardAnalyzer:
    """Builds constraint trees by backward propagation from terminal conditions."""

    def __init__(
        self,
        world: GrueWorld,
        effects: EffectAnalysis,
        relevance: RelevanceAnalysis,
    ):
        self.world = world
        self.effects = effects
        self.relevance = relevance
        self._initial_state: dict[str, Any] = {}
        self._collect_initial_state()

    def _collect_initial_state(self):
        """Collect initial values for all relevant state."""
        for obj_name, obj in self.world.objects.items():
            # Location
            loc_ref = str(LocationRef(obj_name))
            self._initial_state[loc_ref] = obj.location

            # Properties
            for prop, val in obj.properties.items():
                prop_ref = str(PropertyRef(obj_name, prop))
                self._initial_state[prop_ref] = val

        for room_name, room in self.world.rooms.items():
            for prop, val in room.properties.items():
                prop_ref = str(PropertyRef(room_name, prop))
                self._initial_state[prop_ref] = val

    def build_tree(self, constraint: Constraint, max_depth: int = 10) -> ConstraintTree:
        """Build a constraint tree rooted at the given constraint."""
        tree = ConstraintTree(root=ConstraintNode(constraint=constraint))
        tree.all_nodes[constraint] = tree.root

        self._expand_node(tree.root, tree, depth=0, max_depth=max_depth)

        return tree

    def _expand_node(
        self,
        node: ConstraintNode,
        tree: ConstraintTree,
        depth: int,
        max_depth: int
    ):
        """Expand a constraint node by finding achievers and their preconditions."""
        if depth >= max_depth:
            return

        constraint = node.constraint
        ref = constraint.ref

        # Check if this is satisfied in initial state
        ref_str = str(ref)
        initial_value = self._initial_state.get(ref_str)
        if constraint.is_satisfied(initial_value):
            node.is_initial = True
            return

        # Check if this is a constant (can't be modified)
        if ref in self.effects.constants:
            node.is_constant = True
            return

        # Find behaviors that can modify this state
        modifiers = self.effects.modifies.get(ref, set())
        if not modifiers:
            # No way to modify - treat as constant
            node.is_constant = True
            return

        # For each modifier, extract preconditions
        for behavior in modifiers:
            preconditions = self._extract_preconditions(behavior)
            achiever = Achiever(behavior=behavior, preconditions=preconditions)
            node.achievers.append(achiever)

            # Recursively expand preconditions
            for precond in preconditions:
                if precond not in tree.all_nodes:
                    child_node = ConstraintNode(constraint=precond)
                    tree.all_nodes[precond] = child_node
                    node.children[precond] = child_node
                    self._expand_node(child_node, tree, depth + 1, max_depth)
                else:
                    # Reuse existing node (DAG, not tree)
                    node.children[precond] = tree.all_nodes[precond]

    def _extract_preconditions(self, behavior: BehaviorRef) -> list[Constraint]:
        """Extract preconditions for a behavior from its reads.

        This is a heuristic approach - we don't do full symbolic execution,
        but we can infer likely preconditions from:
        1. Known patterns (locked, open, etc.)
        2. Location requirements
        3. Boolean flags
        """
        preconditions = []

        # Find what this behavior reads
        for ref, readers in self.effects.reads.items():
            if behavior in readers:
                ref_str = str(ref)
                initial_value = self._initial_state.get(ref_str)

                if isinstance(ref, PropertyRef):
                    # Known blocking patterns
                    if ref.property in ("locked", "lost", "dead", "broken"):
                        preconditions.append(Constraint(ref, "=", False))
                    elif ref.property in ("open", "freed", "rmung"):
                        preconditions.append(Constraint(ref, "=", True))
                    elif isinstance(initial_value, bool):
                        # Boolean - guess opposite of initial (action usually changes state)
                        preconditions.append(Constraint(ref, "=", not initial_value))
                    elif isinstance(initial_value, int):
                        # Numeric - might need a minimum value
                        # For now, add as "changed from initial" constraint
                        preconditions.append(Constraint(ref, "!=", initial_value))

                elif isinstance(ref, LocationRef):
                    # Location dependency - the object must be accessible
                    # For player-centric games, objects usually need to be:
                    # - Held by player (@player)
                    # - In same room as player
                    # For now, mark as "not initial" if initial is a specific location
                    if initial_value and initial_value != "@player":
                        # Object needs to be moved from initial location
                        preconditions.append(Constraint(ref, "!=", initial_value))

                elif isinstance(ref, QueueRef):
                    # Queue dependency - event must be queued
                    # We can represent this but it's complex
                    pass

        return preconditions


def build_victory_constraints(
    world: GrueWorld,
    effects: EffectAnalysis,
    relevance: RelevanceAnalysis,
) -> list[ConstraintTree]:
    """Build constraint trees for all victory conditions."""
    if not world.victory:
        return []

    analyzer = BackwardAnalyzer(world, effects, relevance)
    constraints = _extract_constraints_from_expr(world.victory.when)

    trees = []
    for constraint in constraints:
        tree = analyzer.build_tree(constraint)
        trees.append(tree)

    return trees


def _extract_constraints_from_expr(expr: Any) -> list[Constraint]:
    """Extract Constraint objects from a Grue expression."""
    constraints = []
    _extract_recursive(expr, constraints)
    return constraints


def _extract_recursive(expr: Any, constraints: list[Constraint]):
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
        constraint = _parse_comparison(left, right, "=")
        if constraint:
            constraints.append(constraint)
        return

    # Comparison operators
    if name in (">=", ">", "<=", "<", "!=") and len(items) == 3:
        left, right = items[1], items[2]
        constraint = _parse_comparison(left, right, name)
        if constraint:
            constraints.append(constraint)
        return

    # (and ...) - conjunction
    if name == "and":
        for item in items[1:]:
            _extract_recursive(item, constraints)
        return


def _parse_comparison(left: Any, right: Any, operator: str) -> Constraint | None:
    """Parse a comparison into a Constraint."""
    # (loc @obj) compared to value
    if isinstance(left, SList) and left.items:
        left_head = left.items[0]

        if isinstance(left_head, Symbol) and left_head.name == "loc":
            if len(left.items) >= 2:
                obj = left.items[1]
                if isinstance(obj, Symbol) and obj.name.startswith("@"):
                    ref = LocationRef(obj.name)
                    value = _extract_value(right)
                    return Constraint(ref, operator, value)

        # (:prop @obj) compared to value
        if isinstance(left_head, Keyword):
            if len(left.items) >= 2:
                obj = left.items[1]
                if isinstance(obj, Symbol) and obj.name.startswith("@"):
                    ref = PropertyRef(obj.name, left_head.name)
                    value = _extract_value(right)
                    return Constraint(ref, operator, value)

    # Handle swapped order: value compared to (loc @obj)
    if isinstance(right, SList) and right.items:
        # Swap and recurse, flipping the operator
        flipped_op = {">=": "<=", ">": "<", "<=": ">=", "<": ">", "=": "=", "!=": "!="}.get(operator, operator)
        return _parse_comparison(right, left, flipped_op)

    return None


def _extract_value(expr: Any) -> Any:
    """Extract a value from an expression."""
    if isinstance(expr, Symbol):
        if expr.name == "nil":
            return None
        elif expr.name in ("true", "false"):
            return expr.name == "true"
        else:
            return expr.name
    elif isinstance(expr, (int, float, bool, str)):
        return expr
    return None
