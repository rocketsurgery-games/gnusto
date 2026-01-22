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
        all_modifiers = self.effects.modifies.get(ref, set())
        if not all_modifiers:
            # No way to modify - treat as constant
            node.is_constant = True
            return

        # Filter to behaviors that set the correct target value
        modifiers = self._filter_modifiers_by_target(ref, constraint.value, all_modifiers)
        if not modifiers:
            # No behavior sets this specific value - treat as unachievable
            # (This can happen if the constraint value is wrong or unreachable)
            node.is_constant = True
            return

        # For each modifier, extract preconditions (may have multiple alternative paths)
        for behavior in modifiers:
            precondition_paths = self._extract_preconditions(behavior)

            if not precondition_paths:
                # No preconditions - single achiever with empty requirements
                node.achievers.append(Achiever(behavior=behavior, preconditions=[]))
            else:
                # Each path is an alternative achiever
                for path in precondition_paths:
                    achiever = Achiever(behavior=behavior, preconditions=path)
                    node.achievers.append(achiever)

                    # Recursively expand preconditions
                    for precond in path:
                        if precond not in tree.all_nodes:
                            child_node = ConstraintNode(constraint=precond)
                            tree.all_nodes[precond] = child_node
                            node.children[precond] = child_node
                            self._expand_node(child_node, tree, depth + 1, max_depth)
                        else:
                            # Reuse existing node (DAG, not tree)
                            node.children[precond] = tree.all_nodes[precond]

    def _filter_modifiers_by_target(
        self, ref: StateRef, target_value: Any, modifiers: set[BehaviorRef]
    ) -> set[BehaviorRef]:
        """Filter modifiers to only those that set the target value.

        Uses modifies_to from effect analysis to determine what value each
        behavior sets. If a behavior's target values are unknown (None in set),
        we include it conservatively.

        Args:
            ref: The state reference being modified
            target_value: The value we want the state to have
            modifiers: All behaviors that can modify this state

        Returns:
            Filtered set of behaviors that can achieve the target value
        """
        if ref not in self.effects.modifies_to:
            # No target value info - return all (conservative)
            return modifiers

        result = set()
        for behavior in modifiers:
            if behavior not in self.effects.modifies_to[ref]:
                # No info for this behavior - include conservatively
                result.add(behavior)
                continue

            target_values = self.effects.modifies_to[ref][behavior]

            # If None is in the set, the value is unknown/variable - include conservatively
            if None in target_values:
                result.add(behavior)
                continue

            # Check if any of the target values match what we want
            for val in target_values:
                if self._values_match(val, target_value):
                    result.add(behavior)
                    break

        return result

    def _values_match(self, actual: Any, expected: Any) -> bool:
        """Check if two values match, with special handling for symbols."""
        if actual == expected:
            return True
        # Handle @symbol strings matching Symbol objects
        if isinstance(expected, str) and expected.startswith("@"):
            if isinstance(actual, str) and actual == expected:
                return True
        return False

    def _extract_preconditions(self, behavior: BehaviorRef) -> list[list[Constraint]]:
        """Extract preconditions for a behavior by analyzing its body.

        Returns list of alternative paths (OR of ANDs).
        Each path is a list of constraints that must be satisfied together.

        Uses two strategies:
        1. Blocking-based: Find conditions leading to (blocked ...) and negate them
        2. Success-based: Find conditions leading to effects (for OR-conditions)

        The blocking approach works for simple gates (one path to success).
        The success approach finds alternative paths (OR-conditions).
        """
        # Special case: runtime:go gets preconditions from door :through behaviors
        if behavior.object == "runtime" and behavior.verb == "go":
            preconds = self._extract_go_preconditions()
            return [preconds] if preconds else []

        # Special case: event behaviors have implicit precondition that event is queued
        # Events are named "event:X" and the event must be in the queue to fire
        if behavior.object.startswith("event:"):
            event_name = behavior.object.split(":", 1)[1]
            # The event being queued is a precondition
            # We model this as: some behavior must have called (queue event_name ...)
            # Those behaviors become the "achievers" for this implicit constraint
            queue_ref = QueueRef(event_name)
            queue_constraint = Constraint(queue_ref, "=", True)
            # Return as single precondition - the queue must be active
            return [[queue_constraint]]

        # Find the behavior body
        body = self._get_behavior_body(behavior)
        if body is None:
            return []

        # Strategy 1: Extract from blocking conditions
        blocking_conditions = self._extract_blocking_conditions(body)
        blocking_preconds: list[Constraint] = []
        for condition, was_negated in blocking_conditions:
            must_be_true = was_negated
            constraint = self._condition_to_constraint(condition, must_be_true)
            if constraint is not None:
                blocking_preconds.append(constraint)

        # Strategy 2: Extract success paths (for OR-conditions)
        success_paths = self._extract_success_conditions(body)

        # Combine strategies:
        # - If we have blocking conditions, they apply to ALL paths
        # - If we have success paths, each path is an alternative
        if success_paths:
            # Each success path is an alternative, combined with blocking preconds
            result: list[list[Constraint]] = []
            for path in success_paths:
                # Combine and deduplicate
                combined = blocking_preconds + path
                seen: set[str] = set()
                deduped: list[Constraint] = []
                for c in combined:
                    key = str(c)
                    if key not in seen:
                        seen.add(key)
                        deduped.append(c)
                result.append(deduped)
            return result
        elif blocking_preconds:
            # Only blocking conditions, single path
            return [blocking_preconds]
        else:
            # No conditions found
            return []

    def _extract_go_preconditions(self) -> list[Constraint]:
        """Extract preconditions for movement from all door :through behaviors.

        When player moves through a door (via :via in room exits), the door's
        :through behavior is checked. We collect preconditions from all doors.
        """
        preconditions: list[Constraint] = []

        # Find all doors used in room exits
        doors_used: set[str] = set()
        for room in self.world.rooms.values():
            for exit_info in room.exits:
                if hasattr(exit_info, 'via') and exit_info.via:
                    doors_used.add(exit_info.via)

        # Get preconditions from each door's :through behavior
        for door_name in doors_used:
            if door_name in self.world.objects:
                door = self.world.objects[door_name]
                if hasattr(door, 'behaviors') and door.behaviors:
                    for behavior in door.behaviors:
                        if behavior.verb == "through":
                            # Extract blocking conditions from :through
                            blocking = self._extract_blocking_conditions(behavior.body)
                            for condition, was_negated in blocking:
                                must_be_true = was_negated
                                constraint = self._condition_to_constraint(condition, must_be_true)
                                if constraint is not None:
                                    preconditions.append(constraint)

        return preconditions

    def _get_behavior_body(self, behavior: BehaviorRef) -> Any:
        """Get the body expression for a behavior."""
        obj_name = behavior.object
        verb = behavior.verb

        # Handle event behaviors
        if obj_name.startswith("event:"):
            event_name = obj_name[6:]  # Strip "event:" prefix
            if event_name in self.world.events:
                return self.world.events[event_name].body
            return None

        # Handle room behaviors
        if obj_name.startswith("@") and obj_name in self.world.rooms:
            room = self.world.rooms[obj_name]
            if hasattr(room, 'behaviors') and room.behaviors:
                for b in room.behaviors:
                    if b.verb == verb:
                        return b.body
            return None

        # Handle object behaviors
        if obj_name in self.world.objects:
            obj = self.world.objects[obj_name]
            if hasattr(obj, 'behaviors') and obj.behaviors:
                for b in obj.behaviors:
                    if b.verb == verb:
                        return b.body

        return None

    def _extract_blocking_conditions(self, expr: Any) -> list[tuple[Any, bool]]:
        """Extract conditions that lead to (blocked ...) outcomes.

        Returns list of (condition, is_negated) tuples.
        is_negated=True means the condition was already negated (e.g., (not X)).
        """
        results: list[tuple[Any, bool]] = []
        self._walk_for_blockers(expr, results, [])
        return results

    def _extract_success_conditions(self, expr: Any) -> list[list[Constraint]]:
        """Extract conditions that lead to effects (set/move).

        Returns list of alternative paths (OR of ANDs).
        Each path is a list of constraints that must be satisfied together.

        This handles OR-conditions where multiple cond branches can succeed.
        """
        paths: list[list[tuple[Any, bool]]] = []
        self._walk_for_effects(expr, [], paths)

        # Convert condition tuples to constraints
        result: list[list[Constraint]] = []
        for path in paths:
            constraints: list[Constraint] = []
            for condition, is_negated in path:
                # For success paths, the condition must be TRUE (not negated for success)
                must_be_true = not is_negated
                constraint = self._condition_to_constraint(condition, must_be_true)
                if constraint is not None:
                    constraints.append(constraint)
            if constraints:  # Only add non-empty paths
                result.append(constraints)

        return result

    def _walk_for_effects(
        self,
        expr: Any,
        condition_stack: list[tuple[Any, bool]],
        paths: list[list[tuple[Any, bool]]],
    ):
        """Walk expression tree looking for effects (set/move) with condition context."""
        if not isinstance(expr, SList) or not expr.items:
            return

        items = expr.items
        head = items[0]

        if not isinstance(head, Symbol):
            # Could be a keyword-as-function, recurse into children
            for item in items:
                self._walk_for_effects(item, condition_stack, paths)
            return

        name = head.name

        # (set ...) or (move ...) - we found an effect
        if name in ("set", "move"):
            # Record this path's conditions
            if condition_stack:
                paths.append(list(condition_stack))
            return

        # (quote (...)) - quoted effect list, check inside
        if name == "quote" and len(items) >= 2:
            quoted = items[1]
            if isinstance(quoted, SList):
                # Check if this contains effects
                for item in quoted.items:
                    if isinstance(item, SList) and item.items:
                        inner_head = item.items[0]
                        if isinstance(inner_head, Symbol) and inner_head.name in ("set", "move"):
                            # Found effect in quoted list
                            if condition_stack:
                                paths.append(list(condition_stack))
                            return
            return

        # (cond (test1 result1) (test2 result2) ...)
        if name == "cond":
            for clause in items[1:]:
                if isinstance(clause, SList) and len(clause.items) >= 2:
                    test = clause.items[0]
                    body = clause.items[1:]

                    # Check for else clause (Symbol 'true' OR Python True)
                    if self._is_else_clause(test):
                        # Else clause - process without adding condition
                        for b in body:
                            self._walk_for_effects(b, condition_stack, paths)
                    else:
                        # Regular clause - decompose condition and add to stack
                        is_negated = self._is_negated_condition(test)
                        inner_cond = self._unwrap_negation(test) if is_negated else test
                        decomposed = self._decompose_condition(inner_cond, is_negated)
                        new_stack = condition_stack + decomposed
                        for b in body:
                            self._walk_for_effects(b, new_stack, paths)
            return

        # (if test then else?)
        if name == "if" and len(items) >= 3:
            test = items[1]
            then_branch = items[2]
            else_branch = items[3] if len(items) > 3 else None

            is_negated = self._is_negated_condition(test)
            inner_cond = self._unwrap_negation(test) if is_negated else test

            # Then branch: decompose condition
            decomposed = self._decompose_condition(inner_cond, is_negated)
            then_stack = condition_stack + decomposed
            self._walk_for_effects(then_branch, then_stack, paths)

            # Else branch: condition is false (flip negation for each part)
            if else_branch:
                flipped = [(c, not n) for c, n in decomposed]
                else_stack = condition_stack + flipped
                self._walk_for_effects(else_branch, else_stack, paths)
            return

        # Default: recurse into children
        for item in items:
            self._walk_for_effects(item, condition_stack, paths)

    def _is_else_clause(self, test: Any) -> bool:
        """Check if a cond test is an else clause (literal true)."""
        # Python True (from parser)
        if test is True:
            return True
        # Symbol 'true'
        if isinstance(test, Symbol) and test.name == "true":
            return True
        return False

    def _decompose_condition(self, test: Any, is_negated: bool) -> list[tuple[Any, bool]]:
        """Decompose a condition into atomic parts.

        Handles (and A B ...) by returning each part separately.
        The is_negated flag tracks whether the overall condition was negated.

        Returns list of (condition, is_negated) tuples.
        """
        # Check for (and ...)
        if isinstance(test, SList) and test.items:
            head = test.items[0]
            if isinstance(head, Symbol) and head.name == "and":
                # (and A B ...) - decompose into parts
                # Each part must be true (if not negated) or false (if negated)
                parts: list[tuple[Any, bool]] = []
                for part in test.items[1:]:
                    # Check if part is itself negated
                    part_negated = self._is_negated_condition(part)
                    inner = self._unwrap_negation(part) if part_negated else part
                    # Combine negations: if outer is negated and inner is negated, result is not negated
                    final_negated = is_negated != part_negated  # XOR
                    parts.extend(self._decompose_condition(inner, final_negated))
                return parts

        # Atomic condition
        return [(test, is_negated)]

    def _walk_for_blockers(
        self,
        expr: Any,
        results: list[tuple[Any, bool]],
        condition_stack: list[tuple[Any, bool]],
    ):
        """Walk expression tree looking for (blocked ...) with condition context."""
        if not isinstance(expr, SList) or not expr.items:
            return

        items = expr.items
        head = items[0]

        if not isinstance(head, Symbol):
            # Could be a keyword-as-function, recurse into children
            for item in items:
                self._walk_for_blockers(item, results, condition_stack)
            return

        name = head.name

        # (blocked ...) - we found a blocking outcome
        if name == "blocked":
            # All conditions in the stack must be negated for success
            for condition, is_negated in condition_stack:
                results.append((condition, is_negated))
            return

        # (cond (test1 result1) (test2 result2) ...)
        if name == "cond":
            for clause in items[1:]:
                if isinstance(clause, SList) and len(clause.items) >= 2:
                    test = clause.items[0]
                    body = clause.items[1:]

                    # Check for else clause (Symbol 'true' OR Python True)
                    if self._is_else_clause(test):
                        # Else clause - process without adding condition
                        for b in body:
                            self._walk_for_blockers(b, results, condition_stack)
                    else:
                        # Regular clause - decompose condition and add to stack
                        is_negated = self._is_negated_condition(test)
                        inner_cond = self._unwrap_negation(test) if is_negated else test
                        decomposed = self._decompose_condition(inner_cond, is_negated)
                        new_stack = condition_stack + decomposed
                        for b in body:
                            self._walk_for_blockers(b, results, new_stack)
            return

        # (if test then else?)
        if name == "if" and len(items) >= 3:
            test = items[1]
            then_branch = items[2]
            else_branch = items[3] if len(items) > 3 else None

            is_negated = self._is_negated_condition(test)
            inner_cond = self._unwrap_negation(test) if is_negated else test

            # Then branch: condition is true (or negated is true)
            then_stack = condition_stack + [(inner_cond, is_negated)]
            self._walk_for_blockers(then_branch, results, then_stack)

            # Else branch: condition is false (flip negation)
            if else_branch:
                else_stack = condition_stack + [(inner_cond, not is_negated)]
                self._walk_for_blockers(else_branch, results, else_stack)
            return

        # Function call inlining: (function-name args...)
        if name in self.world.functions:
            fn = self.world.functions[name]
            # Track to avoid infinite recursion
            if not hasattr(self, '_inline_stack'):
                self._inline_stack = set()
            if name not in self._inline_stack:
                self._inline_stack.add(name)
                try:
                    self._walk_for_blockers(fn.body, results, condition_stack)
                finally:
                    self._inline_stack.discard(name)
            return

        # Default: recurse into children
        for item in items:
            self._walk_for_blockers(item, results, condition_stack)

    def _is_negated_condition(self, expr: Any) -> bool:
        """Check if expression is (not ...)."""
        if isinstance(expr, SList) and expr.items:
            head = expr.items[0]
            if isinstance(head, Symbol) and head.name == "not":
                return True
        return False

    def _unwrap_negation(self, expr: Any) -> Any:
        """Unwrap (not X) to X."""
        if isinstance(expr, SList) and len(expr.items) >= 2:
            return expr.items[1]
        return expr

    def _condition_to_constraint(self, condition: Any, must_be_true: bool) -> Constraint | None:
        """Convert a condition expression to a Constraint.

        must_be_true: if True, the condition must be true for success;
                      if False, the condition must be false for success.
        """
        if not isinstance(condition, SList) or not condition.items:
            return None

        items = condition.items
        head = items[0]

        # (:prop @obj) - property read, must be truthy/falsy
        if isinstance(head, Keyword) and len(items) >= 2:
            obj = items[1]
            if isinstance(obj, Symbol) and obj.name.startswith("@"):
                ref = PropertyRef(obj.name, head.name)
                # Property must be truthy (True) or falsy (False)
                return Constraint(ref, "=", must_be_true)

        if not isinstance(head, Symbol):
            return None

        name = head.name

        # (held? @obj) - object must be held by player
        if name == "held?" and len(items) >= 2:
            obj = items[1]
            if isinstance(obj, Symbol) and obj.name.startswith("@"):
                ref = LocationRef(obj.name)
                if must_be_true:
                    return Constraint(ref, "=", "@player")
                else:
                    return Constraint(ref, "!=", "@player")

        # (= left right) - equality check
        if name == "=" and len(items) == 3:
            # For now, skip complex equality - would need more analysis
            pass

        # (not X) - recurse with flipped must_be_true
        if name == "not" and len(items) >= 2:
            return self._condition_to_constraint(items[1], not must_be_true)

        return None


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


def build_defeat_constraints(
    world: GrueWorld,
    effects: EffectAnalysis,
    relevance: RelevanceAnalysis,
) -> list[ConstraintTree]:
    """Build constraint trees for all defeat conditions."""
    if not world.defeat:
        return []

    analyzer = BackwardAnalyzer(world, effects, relevance)
    trees = []

    for name, defeat in world.defeat.items():
        constraints = _extract_constraints_from_expr(defeat.when)
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

    # (:keyword @object) - boolean property check (implicitly = true)
    if isinstance(head, Keyword) and len(items) == 2:
        obj = items[1]
        if isinstance(obj, Symbol) and obj.name.startswith("@"):
            prop_name = head.name  # Keyword.name doesn't have ':'
            ref = PropertyRef(obj.name, prop_name)
            constraints.append(Constraint(ref, "=", True))
        return

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
