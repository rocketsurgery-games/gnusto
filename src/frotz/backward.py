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
    HeldRef,
    BehaviorRef,
)


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
        """Check equality with nil/None and falsy value handling.

        In Grue, nil and False are both falsy values, and truthy checks
        like (:prop @obj) evaluate to the property value, treating nil/False
        as falsy. So for constraint matching, we treat falsy values as equivalent.
        """
        if a == b:
            return True
        # Falsy values: None, "nil", False are all equivalent
        falsy_values = (None, "nil", False)
        if a in falsy_values and b in falsy_values:
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

    def get_all_state_refs(self) -> set[StateRef]:
        """Get all state refs referenced by constraints in this tree.

        This returns the precise set of state that must be tracked to
        detect progress toward this tree's victory condition.
        """
        refs: set[StateRef] = set()
        for constraint in self.all_nodes.keys():
            refs.add(constraint.ref)
        return refs


def _abstract_constraint_ref(constraint: Constraint) -> StateRef:
    """Convert a constraint's ref to an abstract predicate where applicable.

    LocationRef constraints that compare against @player are converted to HeldRef:
    - LocationRef(obj) = @player  →  HeldRef(obj) (tracks: is it held?)
    - LocationRef(obj) != @player →  HeldRef(obj) (tracks: is it held?)

    This dramatically reduces state space for "held item" constraints:
    instead of tracking N possible locations, we track 1 boolean.

    Player location is NOT abstracted - we need the actual room for navigation.
    """
    ref = constraint.ref

    # Convert LocationRef to HeldRef when the constraint is about being held
    if isinstance(ref, LocationRef):
        # Don't abstract player location - we need actual room for navigation
        if ref.object == "@player":
            return ref

        # If constraint compares location to @player, use HeldRef
        if constraint.operator in ("=", "!=") and constraint.value == "@player":
            return HeldRef(ref.object)

    return ref


def collect_constraint_refs(trees: list["ConstraintTree"], abstract_held: bool = True) -> set[StateRef]:
    """Collect all state refs from a list of constraint trees.

    Use this to get the precise set of state refs needed for winnability
    analysis, derived from backward constraint propagation.

    Args:
        trees: The constraint trees to collect refs from
        abstract_held: If True (default), convert LocationRef constraints that
                      compare to @player into HeldRef predicates. This reduces
                      state explosion from O(rooms) to O(2) for held items.
    """
    refs: set[StateRef] = set()
    for tree in trees:
        for constraint in tree.all_nodes.keys():
            if abstract_held:
                refs.add(_abstract_constraint_ref(constraint))
            else:
                refs.add(constraint.ref)
    return refs


def collect_navigation_refs(effects: EffectAnalysis) -> set[StateRef]:
    """Collect state refs that affect navigation (from barrier :through behaviors).

    Navigation barriers (:via in room exits) can conditionally block movement
    based on game state. Effect analysis tracks what runtime:go reads from
    these barriers. This function extracts those refs so exploration can
    distinguish states where movement is blocked vs allowed.

    This is necessary because constraint back-propagation doesn't automatically
    discover navigation dependencies - a barrier might read @floor-waxer:location
    to decide whether to block, but this isn't a "precondition" in the traditional
    sense (there's no achiever that sets it to allow passage).

    Note: This includes LocationRefs for objects whose location is checked by
    navigation barriers. While LocationRefs can cause state explosion in general,
    the set of objects checked by barriers is typically small (e.g., mobile NPCs
    that block passages), so including them is necessary for correct reachability.

    Args:
        effects: The effect analysis results

    Returns:
        Set of state refs read by navigation barriers
    """
    refs: set[StateRef] = set()
    runtime_go = BehaviorRef("runtime", "go")

    for state_ref, behaviors in effects.reads.items():
        if runtime_go in behaviors:
            refs.add(state_ref)

    return refs


class BackwardAnalyzer:
    """Builds constraint trees by backward propagation from terminal conditions."""

    def __init__(
        self,
        world: GrueWorld,
        effects: EffectAnalysis,
    ):
        self.world = world
        self.effects = effects
        self._initial_state: dict[str, Any] = {}
        self._current_self: str | None = None  # Object name for ?self resolution
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
            precondition_paths = self._extract_preconditions(behavior, ref)

            if not precondition_paths:
                # No preconditions - single achiever with empty requirements
                node.achievers.append(Achiever(behavior=behavior, preconditions=[]))
            else:
                # Each path is an alternative achiever
                for path in precondition_paths:
                    # Filter out self-referential preconditions (same constraint we're trying to achieve)
                    # e.g., runtime:drop requires @obj:location = @player to achieve @obj:location = @room
                    # but if we're achieving @obj:location = @player, this is circular
                    filtered_path = [p for p in path if p != constraint]

                    # Skip achievers whose only precondition was self-referential
                    # (they don't help achieve the constraint)
                    if not path or filtered_path:
                        achiever = Achiever(behavior=behavior, preconditions=filtered_path)
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
        """Check if two values match, with special handling for symbols and nil."""
        if actual == expected:
            return True
        # Handle @symbol strings matching Symbol objects
        if isinstance(expected, str) and expected.startswith("@"):
            if isinstance(actual, str) and actual == expected:
                return True
        # Handle nil/None equivalence
        # Effect analysis stores Python None for 'nil', but constraints may use string 'nil'
        nil_values = (None, "nil")
        if actual in nil_values and expected in nil_values:
            return True
        return False

    def _extract_preconditions(
        self, behavior: BehaviorRef, target_ref: StateRef | None = None
    ) -> list[list[Constraint]]:
        """Extract preconditions for a behavior by analyzing its body.

        Returns list of alternative paths (OR of ANDs).
        Each path is a list of constraints that must be satisfied together.

        Args:
            behavior: The behavior to extract preconditions from
            target_ref: If provided, only extract conditions leading to effects on this ref.
                       This enables effect-path analysis for complex conditionals.

        Uses two strategies:
        1. Blocking-based: Find conditions leading to (blocked ...) and negate them
        2. Effect-path: Find conditions leading to effects on target_ref

        The blocking approach works for simple gates (one path to success).
        The effect-path approach finds conditions to reach specific effects.
        """
        # Special case: runtime:go gets preconditions from door :through behaviors
        if behavior.object == "runtime" and behavior.verb == "go":
            preconds = self._extract_go_preconditions()
            return [preconds] if preconds else []

        # Special case: runtime:take needs the object to be takeable
        # The target_ref tells us which object is being taken
        if behavior.object == "runtime" and behavior.verb == "take":
            if target_ref and isinstance(target_ref, LocationRef):
                obj_name = target_ref.object
                # To take an object, it must have :takeable = true
                # The location accessibility check (player in same room) is handled by runtime
                # and can't be easily modeled statically without room context
                takeable_ref = PropertyRef(obj_name, "takeable")
                return [[Constraint(takeable_ref, "=", True)]]
            return []

        # Special case: runtime:drop needs the object to be held by player first
        # The target_ref tells us which object is being dropped
        if behavior.object == "runtime" and behavior.verb == "drop":
            if target_ref and isinstance(target_ref, LocationRef):
                obj_name = target_ref.object
                # To drop an object, player must be holding it
                obj_loc_ref = LocationRef(obj_name)
                return [[Constraint(obj_loc_ref, "=", "@player")]]
            return []

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

        # Set _current_self for ?self resolution in condition analysis
        # Object behaviors use the object name, room behaviors use the room name
        obj_name = behavior.object
        if obj_name.startswith("@"):
            self._current_self = obj_name

        try:
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

            # Strategy 2: Extract effect-path conditions (for target ref)
            effect_paths = self._extract_success_conditions(body, target_ref)

            # Combine strategies:
            # - If we have blocking conditions, they apply to ALL paths
            # - If we have effect paths, each path is an alternative
            if effect_paths:
                # Each effect path is an alternative, combined with blocking preconds
                result: list[list[Constraint]] = []
                for path in effect_paths:
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
        finally:
            self._current_self = None

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

    def _extract_success_conditions(
        self, expr: Any, target_ref: StateRef | None = None
    ) -> list[list[Constraint]]:
        """Extract conditions that lead to effects on target_ref.

        Returns list of alternative paths (OR of ANDs).
        Each path is a list of constraints that must be satisfied together.

        Args:
            expr: The expression to analyze
            target_ref: If provided, only record paths to effects that modify this ref.
                       If None, record paths to all effects (legacy behavior).

        This handles OR-conditions where multiple cond branches can succeed.
        """
        paths: list[list[tuple[Any, bool]]] = []
        self._walk_for_effects(expr, [], paths, target_ref)

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
                # Filter out redundant/contradictory constraints
                filtered = self._filter_contradictory_constraints(constraints, target_ref)
                if filtered:
                    result.append(filtered)

        return result

    def _filter_contradictory_constraints(
        self, constraints: list[Constraint], target_ref: StateRef | None
    ) -> list[Constraint]:
        """Filter out constraints that contradict each other or are redundant.

        Specifically handles De Morgan artifacts where negated AND produces both:
        - NOT A (location != X)
        - NOT B (property = Y)

        If target_ref is a LocationRef, and we have both a location constraint and
        another constraint, we prefer the non-location constraint since the location
        check is often just "where is this object now" rather than "what must change".

        Also removes constraints that are directly contradictory (same ref, opposite values).
        """
        if not target_ref or len(constraints) <= 1:
            return constraints

        # Separate location constraints from others
        location_constraints: list[Constraint] = []
        other_constraints: list[Constraint] = []

        for c in constraints:
            if isinstance(c.ref, LocationRef):
                location_constraints.append(c)
            else:
                other_constraints.append(c)

        # If we're achieving a location change and have both location and property constraints,
        # the location constraints like "obj != X" are often artifacts of De Morgan on
        # conditions like "(and (= (loc obj) X) (not (:prop obj)))".
        # The useful constraint is usually the property one.
        if isinstance(target_ref, LocationRef) and other_constraints and location_constraints:
            # Check if location constraints are about the same object as target
            target_obj = target_ref.object
            redundant_loc = [
                c for c in location_constraints
                if isinstance(c.ref, LocationRef) and c.ref.object == target_obj and c.operator in ("!=",)
            ]
            if redundant_loc:
                # Keep only non-redundant location constraints
                location_constraints = [c for c in location_constraints if c not in redundant_loc]

        return other_constraints + location_constraints

    def _walk_for_effects(
        self,
        expr: Any,
        condition_stack: list[tuple[Any, bool]],
        paths: list[list[tuple[Any, bool]]],
        target_ref: StateRef | None = None,
    ):
        """Walk expression tree looking for effects with condition context.

        Args:
            expr: The expression to walk
            condition_stack: Current stack of conditions to reach this point
            paths: List to append successful paths to
            target_ref: If provided, only record paths to effects that modify this ref
        """
        if not isinstance(expr, SList) or not expr.items:
            return

        items = expr.items
        head = items[0]

        if not isinstance(head, Symbol):
            # Could be a keyword-as-function, recurse into children
            for item in items:
                self._walk_for_effects(item, condition_stack, paths, target_ref)
            return

        name = head.name

        # Effect detection: (set @obj :prop value)
        if name == "set" and len(items) >= 4:
            obj = items[1]
            prop = items[2]
            if isinstance(obj, Symbol) and obj.name.startswith("@") and isinstance(prop, Keyword):
                effect_ref = PropertyRef(obj.name, prop.name)
                if target_ref is None or effect_ref == target_ref:
                    paths.append(list(condition_stack))
            return

        # Effect detection: (move @obj dest)
        if name == "move" and len(items) >= 3:
            obj = items[1]
            if isinstance(obj, Symbol) and obj.name.startswith("@"):
                effect_ref = LocationRef(obj.name)
                if target_ref is None or effect_ref == target_ref:
                    paths.append(list(condition_stack))
            return

        # Effect detection: (queue event-name) or (queue event-name countdown)
        if name == "queue" and len(items) >= 2:
            event = items[1]
            event_name = event.name if isinstance(event, Symbol) else str(event)
            effect_ref = QueueRef(event_name)
            if target_ref is None or effect_ref == target_ref:
                paths.append(list(condition_stack))
            return

        # Effect detection: (dequeue event-name)
        if name == "dequeue" and len(items) >= 2:
            event = items[1]
            event_name = event.name if isinstance(event, Symbol) else str(event)
            effect_ref = QueueRef(event_name)
            if target_ref is None or effect_ref == target_ref:
                paths.append(list(condition_stack))
            return

        # (quote (...)) or quasiquote (`) - quoted effect list, check inside
        if name in ("quote", "quasiquote") and len(items) >= 2:
            quoted = items[1]
            if isinstance(quoted, SList):
                # Check each item in quoted list for effects
                for item in quoted.items:
                    if isinstance(item, SList) and item.items:
                        inner_head = item.items[0]
                        if isinstance(inner_head, Symbol):
                            inner_name = inner_head.name
                            # Check for set/move/queue/dequeue in quoted list
                            if inner_name == "set" and len(item.items) >= 4:
                                obj = item.items[1]
                                prop = item.items[2]
                                # Resolve ?self to actual object name
                                obj_name = self._resolve_object_ref(obj)
                                if obj_name and isinstance(prop, Keyword):
                                    effect_ref = PropertyRef(obj_name, prop.name)
                                    if target_ref is None or effect_ref == target_ref:
                                        paths.append(list(condition_stack))
                                        return
                            elif inner_name == "move" and len(item.items) >= 3:
                                obj = item.items[1]
                                # Resolve ?self to actual object name
                                obj_name = self._resolve_object_ref(obj)
                                if obj_name:
                                    effect_ref = LocationRef(obj_name)
                                    if target_ref is None or effect_ref == target_ref:
                                        paths.append(list(condition_stack))
                                        return
                            elif inner_name == "queue" and len(item.items) >= 2:
                                event = item.items[1]
                                event_name = event.name if isinstance(event, Symbol) else str(event)
                                effect_ref = QueueRef(event_name)
                                if target_ref is None or effect_ref == target_ref:
                                    paths.append(list(condition_stack))
                                    return
                            elif inner_name == "dequeue" and len(item.items) >= 2:
                                event = item.items[1]
                                event_name = event.name if isinstance(event, Symbol) else str(event)
                                effect_ref = QueueRef(event_name)
                                if target_ref is None or effect_ref == target_ref:
                                    paths.append(list(condition_stack))
                                    return
            return

        # (cond (test1 result1) (test2 result2) ...)
        # To reach branch N, all previous branches must have failed (their tests were false)
        if name == "cond":
            accumulated_skip: list[tuple[Any, bool]] = []  # Conditions that must be FALSE to skip earlier branches
            for clause in items[1:]:
                if isinstance(clause, SList) and len(clause.items) >= 2:
                    test = clause.items[0]
                    body = clause.items[1:]

                    # Check for else clause (Symbol 'true' OR Python True)
                    if self._is_else_clause(test):
                        # Else clause - all previous conditions must have been false
                        new_stack = condition_stack + accumulated_skip
                        for b in body:
                            self._walk_for_effects(b, new_stack, paths, target_ref)
                    else:
                        # Regular clause: to reach this branch, we need:
                        # 1. All previous branch tests to be FALSE (accumulated_skip)
                        # 2. This branch's test to be TRUE
                        is_negated = self._is_negated_condition(test)
                        inner_cond = self._unwrap_negation(test) if is_negated else test
                        decomposed = self._decompose_condition(inner_cond, is_negated)

                        new_stack = condition_stack + accumulated_skip + decomposed
                        for b in body:
                            self._walk_for_effects(b, new_stack, paths, target_ref)

                        # Add this test (negated) to accumulated_skip for subsequent branches
                        # To skip this branch, this test must be FALSE
                        # If test is (not X), then to skip we need X to be TRUE
                        # If test is X, then to skip we need X to be FALSE
                        skip_decomposed = self._decompose_condition(inner_cond, not is_negated)
                        accumulated_skip.extend(skip_decomposed)
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
            self._walk_for_effects(then_branch, then_stack, paths, target_ref)

            # Else branch: condition is false (flip negation for each part)
            if else_branch:
                flipped = [(c, not n) for c, n in decomposed]
                else_stack = condition_stack + flipped
                self._walk_for_effects(else_branch, else_stack, paths, target_ref)
            return

        # Function call inlining: (function-name args...)
        if name in self.world.functions:
            fn = self.world.functions[name]
            # Track to avoid infinite recursion
            if not hasattr(self, '_inline_stack_effects'):
                self._inline_stack_effects = set()
            if name not in self._inline_stack_effects:
                self._inline_stack_effects.add(name)
                try:
                    self._walk_for_effects(fn.body, condition_stack, paths, target_ref)
                finally:
                    self._inline_stack_effects.discard(name)
            return

        # Default: recurse into children
        for item in items:
            self._walk_for_effects(item, condition_stack, paths, target_ref)

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

        NOTE: For negated ANDs (De Morgan), this returns ALL parts negated, which
        means "all must be false" rather than the correct "at least one false".
        This is conservative - it over-constrains. For proper OR handling, use
        _decompose_condition_alternatives() which returns separate paths.
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

    def _decompose_condition_alternatives(
        self, test: Any, is_negated: bool
    ) -> list[list[tuple[Any, bool]]]:
        """Decompose a condition into alternative paths (for proper De Morgan handling).

        Unlike _decompose_condition which returns one combined list, this returns
        multiple alternative paths when De Morgan's law applies:
        - NOT (A AND B) = (NOT A) OR (NOT B) -> two paths
        - (A AND B) -> one path with both conditions

        Returns list of paths, where each path is a list of (condition, is_negated) tuples.
        """
        if isinstance(test, SList) and test.items:
            head = test.items[0]
            if isinstance(head, Symbol) and head.name == "and":
                parts = test.items[1:]
                if is_negated:
                    # De Morgan: NOT (A AND B AND ...) = (NOT A) OR (NOT B) OR ...
                    # Each part being false is an alternative path
                    alternatives: list[list[tuple[Any, bool]]] = []
                    for part in parts:
                        part_negated = self._is_negated_condition(part)
                        inner = self._unwrap_negation(part) if part_negated else part
                        final_negated = not part_negated  # Negate the part
                        # Recursively get alternatives for this part
                        sub_alts = self._decompose_condition_alternatives(inner, final_negated)
                        alternatives.extend(sub_alts)
                    return alternatives
                else:
                    # (A AND B AND ...) = all must be true, single path
                    combined: list[tuple[Any, bool]] = []
                    for part in parts:
                        part_negated = self._is_negated_condition(part)
                        inner = self._unwrap_negation(part) if part_negated else part
                        final_negated = part_negated  # Keep part's negation
                        sub_alts = self._decompose_condition_alternatives(inner, final_negated)
                        # For AND, we need all sub-conditions, so flatten all alternatives
                        # (This assumes sub-conditions don't have ORs, which is usually true)
                        for alt in sub_alts:
                            combined.extend(alt)
                    return [combined] if combined else [[]]

        # Atomic condition - single path with single condition
        return [[(test, is_negated)]]

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

    def _resolve_object_ref(self, expr: Any) -> str | None:
        """Resolve an expression to an object name.

        Handles:
        - @object symbols -> "@object"
        - ?self -> current behavior's object (if set)

        Returns None if the expression can't be resolved to a static object name.
        """
        if isinstance(expr, Symbol):
            if expr.name.startswith("@"):
                return expr.name
            if expr.name == "?self" and self._current_self:
                return self._current_self
        return None

    def _condition_to_constraint(self, condition: Any, must_be_true: bool) -> Constraint | None:
        """Convert a condition expression to a Constraint.

        must_be_true: if True, the condition must be true for success;
                      if False, the condition must be false for success.
        """
        if not isinstance(condition, SList) or not condition.items:
            return None

        items = condition.items
        head = items[0]

        # (:prop @obj) or (:prop ?self) - property read, must be truthy/falsy
        if isinstance(head, Keyword) and len(items) >= 2:
            obj = items[1]
            obj_name = self._resolve_object_ref(obj)
            if obj_name:
                ref = PropertyRef(obj_name, head.name)
                # Property must be truthy (True) or falsy (False)
                return Constraint(ref, "=", must_be_true)

        if not isinstance(head, Symbol):
            return None

        name = head.name

        # (held? @obj) or (held? ?self) - object must be held by player
        if name == "held?" and len(items) >= 2:
            obj = items[1]
            obj_name = self._resolve_object_ref(obj)
            if obj_name:
                ref = LocationRef(obj_name)
                if must_be_true:
                    return Constraint(ref, "=", "@player")
                else:
                    return Constraint(ref, "!=", "@player")

        # (queued? event) - event must be in queue
        if name == "queued?" and len(items) >= 2:
            event = items[1]
            event_name = event.name if isinstance(event, Symbol) else str(event)
            ref = QueueRef(event_name)
            return Constraint(ref, "=", must_be_true)

        # (= left right) - equality check
        if name == "=" and len(items) == 3:
            left, right = items[1], items[2]

            # Case 1: (= ?param @object) - parameter must equal object
            # This means the object must be accessible (typically held for takeable items)
            # For non-takeable items (scenery), we skip this constraint
            if isinstance(left, Symbol) and left.name.startswith("?"):
                obj_name = self._resolve_object_ref(right)
                if obj_name and must_be_true:
                    # Only require holding if the object is takeable
                    obj_def = self.world.objects.get(obj_name)
                    if obj_def and obj_def.properties.get("takeable"):
                        ref = LocationRef(obj_name)
                        return Constraint(ref, "=", "@player")
                    # For non-takeable objects, the equality check is just validation
                    # that the player is interacting with the right thing - skip it

            # Case 2: (= @object ?param) - symmetric case
            if isinstance(right, Symbol) and right.name.startswith("?"):
                obj_name = self._resolve_object_ref(left)
                if obj_name and must_be_true:
                    obj_def = self.world.objects.get(obj_name)
                    if obj_def and obj_def.properties.get("takeable"):
                        ref = LocationRef(obj_name)
                        return Constraint(ref, "=", "@player")

            # Case 3: (= (loc @obj) X) - location comparison
            if isinstance(left, SList) and left.items:
                head = left.items[0]
                if isinstance(head, Symbol) and head.name == "loc" and len(left.items) >= 2:
                    obj_name = self._resolve_object_ref(left.items[1])
                    if obj_name:
                        # Extract the expected location value
                        loc_value = self._resolve_object_ref(right)
                        if loc_value is None and isinstance(right, Symbol):
                            loc_value = right.name  # Handle nil
                        if loc_value is not None:
                            ref = LocationRef(obj_name)
                            if must_be_true:
                                return Constraint(ref, "=", loc_value)
                            else:
                                return Constraint(ref, "!=", loc_value)

        # (not X) - recurse with flipped must_be_true
        if name == "not" and len(items) >= 2:
            return self._condition_to_constraint(items[1], not must_be_true)

        return None


def build_victory_constraints(
    world: GrueWorld,
    effects: EffectAnalysis,
) -> list[ConstraintTree]:
    """Build constraint trees for all victory conditions."""
    if not world.victory:
        return []

    analyzer = BackwardAnalyzer(world, effects)
    constraints = _extract_constraints_from_expr(world.victory.when)

    trees = []
    for constraint in constraints:
        tree = analyzer.build_tree(constraint)
        trees.append(tree)

    return trees


def build_defeat_constraints(
    world: GrueWorld,
    effects: EffectAnalysis,
) -> list[ConstraintTree]:
    """Build constraint trees for all defeat conditions."""
    if not world.defeat:
        return []

    analyzer = BackwardAnalyzer(world, effects)
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

    # (held? @obj) - object is held by player (location = @player)
    if name == "held?" and len(items) >= 2:
        obj = items[1]
        if isinstance(obj, Symbol) and obj.name.startswith("@"):
            ref = LocationRef(obj.name)
            constraints.append(Constraint(ref, "=", "@player"))
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
