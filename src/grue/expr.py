"""
Expression evaluator.

This module provides:
- Predicate evaluation (boolean expressions)
- Effect execution (state mutations)
- User-defined functions via (defn name (args) body)
- Type checking for expressions

Built-in Predicates:
    (= A B)                   - Equality
    (> A B), (< A B), etc     - Numeric comparisons
    (and EXPR ...)            - Logical and
    (or EXPR ...)             - Logical or
    (not EXPR)                - Logical not
    (player)                  - Get player entity name
    (loc OBJ)                 - Get object location
    (prop OBJ PROP)           - Get object property value
    (visible? OBJ)            - Is object visible to player
    (inside? OBJ CONTAINER)   - Is object recursively inside container
    (room? LOC)               - Is location a room
    ; Defined in builtins.grue: held?, here?, in?, held-by?, at?, loc?
    (in-room? OBJ ROOM ...)   - Is object in any of listed rooms
    (some PRED COLL)          - First truthy predicate result, or nil
    (every? PRED COLL)        - True if all elements satisfy predicate
    (exit? ACTOR DIR)         - Check if exit exists from actor's room
    (exit-to ACTOR DIR)       - Get destination room for exit
    (exit-via ACTOR DIR)      - Get door object for exit (if any)
    (queued? EVENT)           - Check if event is currently queued

Built-in Effects (for test :setup and REPL debugging):
    (move OBJ DEST)           - Move object to destination
    (set OBJ :PROP VAL)       - Set property on object
    (inc OBJ :PROP)           - Increment property by 1
    (inc OBJ :PROP AMT)       - Increment property by amount
    (seq EFFECT ...)          - Execute effects in order
    (when COND EFFECT)        - Conditional effect
    (defn NAME (PARAMS) BODY) - Define user function
    (queue EVENT)             - Queue an event (indefinite)
    (queue EVENT N)           - Queue an event with countdown
    (dequeue EVENT)           - Remove event from queue
    (take OBJ)                - Move object to player inventory
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, Optional

from .sexpr import SExpr, Symbol, Keyword, SList, parse


def quote_to_data(expr: SExpr) -> Any:
    """Convert quoted AST to Python data structures.

    This is used to convert quoted expressions to runtime values:
    - SList → list (recursively)
    - Symbol → str (the symbol name)
    - Keyword → Keyword (preserved for (:key map) lookup)
    - Primitives → as-is

    Examples:
        '(a b c) → ["a", "b", "c"]
        'foo → "foo"
        '(:foo "bar") → [Keyword("foo"), "bar"]
    """
    if isinstance(expr, SList):
        return [quote_to_data(item) for item in expr.items]
    if isinstance(expr, Symbol):
        return expr.name
    # Keyword preserved for (:key map) lookup
    # Primitives (int, str, bool, None) pass through
    return expr


@dataclass
class GrueFn:
    """A first-class function (lambda/closure).

    Functions capture their parameter names, body expression, and the lexical
    environment at the point of definition. When called, parameters are bound
    to arguments in a new environment extending the captured environment.

    Examples:
        (fn () (success))                    ; No params
        (fn (?x) (+ ?x 1))                   ; One param
        (fn (?a ?b) (and (held? ?a) ?b))     ; Multiple params

    Note: Parameter names conventionally start with ? but this is not required.
    The ? is stripped when stored (e.g., ?item -> "item").
    """
    params: list[str]
    body: SExpr
    # Captured lexical environment (for proper closures)
    # Note: This is Optional because Environment is defined later in the file.
    # At runtime, closures created via (fn ...) will always have an environment.
    captured_env: Any = None  # Actually Optional[Environment], but forward reference

    def __repr__(self) -> str:
        param_str = " ".join(f"?{p}" for p in self.params)
        return f"(fn ({param_str}) ...)"


# === Behavior Result Types ===
# These are returned by behavior expressions like (success), (blocked), etc.

@dataclass
class BehaviorSuccess:
    """Result indicating the behavior succeeded.

    Usage in behaviors:
        (success)                           ; Simple success
        (success :message "Done!")          ; With message context
        (success :context ((key value)))    ; With structured context

    For behaviors with effects, use quoted effect lists instead:
        '((move @key @player) (success :message "Got it!"))
    """
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorBlocked:
    """Result indicating the behavior was blocked.

    Usage in behaviors:
        (blocked :reason locked)
        (blocked :reason no-key :message "The door is locked.")
    """
    reason: str = "unknown"
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorRedirect:
    """Result indicating the action should be redirected.

    Usage in behaviors:
        (redirect (do @other-door :open))
    """
    action: SExpr
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorDefault:
    """Result indicating the default action should be used.

    Usage in behaviors:
        (default)                           ; Use default
        (default (do @container :open))     ; With explicit action
    """
    action: SExpr | None = None
    context: dict[str, Any] = field(default_factory=dict)


class WorldState(Protocol):
    """Protocol for world state access."""

    def get_object_location(self, obj: str) -> str | None:
        """Get object's current location."""
        ...

    def get_object_property(self, obj: str, prop: str) -> Any:
        """Get object property value."""
        ...

    def get_global(self, name: str) -> Any:
        """Get global variable value."""
        ...

    def get_player_location(self) -> str:
        """Get player's current room."""
        ...

    def get_player_name(self) -> str:
        """Get the player entity name (e.g., '@player' or 'PLAYER')."""
        ...

    def get_inventory(self) -> list[str]:
        """Get player's inventory."""
        ...

    def is_visible(self, obj: str) -> bool:
        """Check if object is visible to player."""
        ...

    def is_room(self, loc: str) -> bool:
        """Check if location is a room."""
        ...

    def is_object(self, name: str) -> bool:
        """Check if name refers to a known object."""
        ...

    def get_contents(self, container: str) -> list[str]:
        """Get contents of container/room."""
        ...

    def get_exit(self, actor: str, direction: str) -> tuple[str, str | None] | None:
        """Get exit info for direction from actor's room. Returns (destination, via) or None."""
        ...

    def is_queued(self, event: str) -> bool:
        """Check if an event is currently queued."""
        ...

    def get_ldesc(self, entity: str) -> Any:
        """Get entity's raw ldesc (string or fn expression)."""
        ...

    def get_description(self, entity: str) -> Any:
        """Get entity's raw description (string or fn expression)."""
        ...


class MutableWorldState(WorldState, Protocol):
    """Protocol for mutable world state (effects)."""

    def set_object_property(self, obj: str, prop: str, value: Any) -> None:
        """Set object property value."""
        ...

    def set_global(self, name: str, value: Any) -> None:
        """Set global variable value."""
        ...

    def move_object(self, obj: str, dest: str) -> None:
        """Move object to new location."""
        ...

    def queue_event(self, event: str, countdown: int | None = None) -> None:
        """Queue an event. countdown=None means indefinite."""
        ...

    def dequeue_event(self, event: str) -> None:
        """Remove an event from the queue."""
        ...


# === Effect Interpretation (Applicative Effect System) ===
#
# In the pure effect model, behaviors return quoted lists of effect descriptors:
#
#     :examine (fn ()
#       '((move @key @player)
#         (success :message "Found a key!")))
#
# EffectInterpreter processes these lists:
# 1. Validates structure (exactly one terminator)
# 2. Applies mutation effects (move, set-flag, etc.)
# 3. Returns an EffectOutcome with the terminator info
#
# This enables static analysis: behaviors are pure functions State → EffectList,
# and effects can be inspected before execution.


@dataclass
class EffectOutcome:
    """Result of interpreting an effect list.

    This is the output of EffectInterpreter, containing:
    - outcome: "success", "blocked", "redirect", or "default"
    - reason: For blocked outcomes
    - context: Key-value pairs (message, description, etc.)
    - redirect_action: For redirect outcomes, the (do ...) form
    - effects_applied: List of effect descriptions for debugging
    - output: List of structured output effects [(type, entity, text), ...]
    """
    outcome: str  # "success", "blocked", "redirect", "default"
    reason: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    redirect_action: list | None = None  # The (do ...) for redirects
    effects_applied: list[str] = field(default_factory=list)
    output: list[tuple[str, str | None, str]] = field(default_factory=list)  # [(type, entity, text), ...]


class EffectInterpreter:
    """Interpret effect lists from pure behaviors.

    Effect lists are Python lists (from quoted expressions) like:
        [["move", "@key", "@player"], ["success", Keyword("message"), "Found it!"]]

    Effect vocabulary:
        Mutations:
            (move obj dest)           - Move object
            (set-flag obj flag)       - Set flag
            (clear-flag obj flag)     - Clear flag
            (set-prop obj prop val)   - Set property
            (set @obj :prop val)      - Set object property
            (set global val)          - Set global variable
            (set-in @obj path val)    - Set nested property (path is list of keys)
            (inc @obj :prop [amt])    - Increment object property
            (inc global [amt])        - Increment global
            (dec @obj :prop [amt])    - Decrement object property
            (dec global [amt])        - Decrement global
            (queue event [countdown]) - Queue event
            (dequeue event)           - Remove event from queue

        Terminators (exactly one required):
            (success [:message ...] [:context ...])
            (blocked :reason ... [:message ...])
            (redirect (do @target :verb ...))
            (default)
    """

    # Effect names that mutate state
    MUTATIONS = frozenset({
        "move", "set-prop", "set", "set-in", "inc", "dec", "queue", "dequeue", "take"
    })

    # Effect names that terminate the effect list
    TERMINATORS = frozenset({"success", "blocked", "redirect", "default", "victory"})

    # Effect names that produce structured output (player-facing content)
    OUTPUT_EFFECTS = frozenset({"narrate", "say"})

    def __init__(self, state: MutableWorldState, bindings: dict[str, Any] | None = None,
                 functions: dict[str, Any] | None = None):
        self.state = state
        self.bindings = bindings or {}
        self.functions = functions or {}
        self._effects_applied: list[str] = []

    def _resolve_arg(self, arg: Any) -> Any:
        """Resolve an argument, substituting ?variables and evaluating expressions.

        Args:
            arg: The argument value (string, number, list expression, etc.)

        Returns:
            The resolved value, with ?xxx variables substituted and expressions evaluated
        """
        if isinstance(arg, str):
            if arg.startswith("?"):
                binding_name = arg[1:]  # Remove ?
                if binding_name in self.bindings:
                    return self.bindings[binding_name]
            elif arg == "nil":
                return None
        elif isinstance(arg, list):
            # Check if this is an expression (function call) vs a data list
            # Expression lists have a string (function name) as first element
            # Data lists have other types (booleans, numbers, etc.)
            if len(arg) > 0 and isinstance(arg[0], str):
                # This looks like an expression - evaluate it
                # Nested expression like (loc @chair) or (door-at-elevator)
                from .sexpr import SList, Symbol, Keyword
                slist = self._list_to_slist(arg)
                # Create evaluator with bindings and functions available
                evaluator = ExprEvaluator(self.state, self.functions, allow_mutations=False)
                evaluator._env = Environment(bindings=dict(self.bindings))
                return evaluator.eval(slist)
            # Otherwise it's a data list, return as-is
        return arg

    def _list_to_slist(self, lst: list) -> SList:
        """Convert a Python list (from quoted expression) back to SList for evaluation."""
        from .sexpr import SList, Symbol, Keyword
        items = []
        for item in lst:
            if isinstance(item, str):
                if item.startswith("@") or item.startswith("?"):
                    items.append(Symbol(item))
                else:
                    items.append(Symbol(item))
            elif isinstance(item, list):
                items.append(self._list_to_slist(item))
            elif isinstance(item, Keyword):
                items.append(item)
            else:
                items.append(item)
        return SList(items)

    def interpret(self, effects: list) -> EffectOutcome:
        """Process an effect list and return the outcome.

        Args:
            effects: List of effect descriptors (from quoted expression)

        Returns:
            EffectOutcome with outcome type, context, and applied effects

        Raises:
            EvalError: If validation fails (no terminator, multiple terminators, etc.)
        """
        self._effects_applied = []
        self._output: list[tuple[str, str | None, str]] = []

        # Validate and find terminator
        terminator = self._validate_and_find_terminator(effects)

        # Apply all mutation and output effects
        for effect in effects:
            if not isinstance(effect, list) or len(effect) == 0:
                continue
            effect_name = effect[0]
            if effect_name in self.MUTATIONS:
                self._apply_mutation(effect)
            elif effect_name in self.OUTPUT_EFFECTS:
                self._collect_output(effect)

        # Convert terminator to outcome
        return self._terminator_to_outcome(terminator)

    def interpret_setup(self, effects: list) -> list[str]:
        """Process an effect list for test :setup (no terminator required).

        Args:
            effects: List of effect descriptors

        Returns:
            List of applied effect descriptions

        Raises:
            EvalError: If an effect is invalid
        """
        self._effects_applied = []

        for effect in effects:
            if not isinstance(effect, list) or len(effect) == 0:
                continue
            effect_name = effect[0]
            if effect_name in self.TERMINATORS:
                raise EvalError(f"Terminator '{effect_name}' not allowed in :setup")
            if effect_name in self.MUTATIONS:
                self._apply_mutation(effect)
            else:
                raise EvalError(f"Unknown effect in :setup: {effect_name}")

        return self._effects_applied

    def _validate_and_find_terminator(self, effects: list) -> list:
        """Find and validate the terminator in an effect list.

        Args:
            effects: The effect list

        Returns:
            The terminator effect (e.g., ["success", ...])

        Raises:
            EvalError: If no terminator, multiple terminators, or unknown effects
        """
        terminator = None
        for effect in effects:
            if not isinstance(effect, list) or len(effect) == 0:
                raise EvalError(f"Invalid effect (must be non-empty list): {effect}")
            effect_name = effect[0]
            if effect_name in self.TERMINATORS:
                if terminator is not None:
                    raise EvalError(
                        f"Multiple terminators in effect list: "
                        f"{terminator[0]} and {effect_name}"
                    )
                terminator = effect
            elif effect_name not in self.MUTATIONS and effect_name not in self.OUTPUT_EFFECTS:
                raise EvalError(f"Unknown effect: {effect_name}")

        if terminator is None:
            raise EvalError(
                "Effect list must contain exactly one terminator "
                "(success, blocked, redirect, default, or victory)"
            )

        return terminator

    def _apply_mutation(self, effect: list) -> None:
        """Apply a mutation effect to the state."""
        name = effect[0]
        # Resolve all arguments, substituting ?variables from bindings
        args = [self._resolve_arg(arg) for arg in effect[1:]]

        if name == "move":
            if len(args) != 2:
                raise EvalError(f"'move' expects 2 arguments, got {len(args)}")
            obj, dest = args[0], args[1]
            self.state.move_object(obj, dest)
            self._effects_applied.append(f"move {obj} to {dest}")

        elif name == "set-prop":
            if len(args) != 3:
                raise EvalError(f"'set-prop' expects 3 arguments, got {len(args)}")
            obj, prop, val = args[0], args[1], args[2]
            # Handle Keyword for property name
            if hasattr(prop, 'name'):
                prop = prop.name
            self.state.set_object_property(obj, prop, val)
            self._effects_applied.append(f"set-prop {obj} {prop} = {val}")

        elif name == "set":
            # Two forms:
            # (set @obj :prop value) - set object property (3 args)
            # (set global-name value) - set global (2 args, legacy)
            if len(args) == 3:
                obj, prop, val = args[0], args[1], args[2]
                # Handle Keyword for property name
                if hasattr(prop, 'name'):
                    prop = prop.name
                self.state.set_object_property(obj, prop, val)
                self._effects_applied.append(f"set {obj} {prop} = {val}")
            elif len(args) == 2:
                global_name, val = args[0], args[1]
                self.state.set_global(global_name, val)
                self._effects_applied.append(f"set {global_name} = {val}")
            else:
                raise EvalError(f"'set' expects 2-3 arguments, got {len(args)}")

        elif name == "inc":
            # Two forms:
            # (inc @obj :prop [amount]) - increment object property (2-3 args)
            # (inc global-name [amount]) - increment global (1-2 args, legacy)
            if len(args) == 3 or (len(args) == 2 and hasattr(args[1], 'name')):
                # Object property form: (inc @obj :prop) or (inc @obj :prop amt)
                obj, prop = args[0], args[1]
                if hasattr(prop, 'name'):
                    prop = prop.name
                amount = args[2] if len(args) > 2 else 1
                current = self.state.get_object_property(obj, prop) or 0
                self.state.set_object_property(obj, prop, current + amount)
                self._effects_applied.append(f"inc {obj} {prop} by {amount}")
            elif len(args) >= 1 and len(args) <= 2:
                # Global form: (inc global-name) or (inc global-name amt)
                global_name = args[0]
                amount = args[1] if len(args) > 1 else 1
                current = self.state.get_global(global_name)
                self.state.set_global(global_name, current + amount)
                self._effects_applied.append(f"inc {global_name} by {amount}")
            else:
                raise EvalError(f"'inc' expects 1-3 arguments, got {len(args)}")

        elif name == "dec":
            # Two forms:
            # (dec @obj :prop [amount]) - decrement object property (2-3 args)
            # (dec global-name [amount]) - decrement global (1-2 args, legacy)
            if len(args) == 3 or (len(args) == 2 and hasattr(args[1], 'name')):
                # Object property form: (dec @obj :prop) or (dec @obj :prop amt)
                obj, prop = args[0], args[1]
                if hasattr(prop, 'name'):
                    prop = prop.name
                amount = args[2] if len(args) > 2 else 1
                current = self.state.get_object_property(obj, prop) or 0
                self.state.set_object_property(obj, prop, current - amount)
                self._effects_applied.append(f"dec {obj} {prop} by {amount}")
            elif len(args) >= 1 and len(args) <= 2:
                # Global form: (dec global-name) or (dec global-name amt)
                global_name = args[0]
                amount = args[1] if len(args) > 1 else 1
                current = self.state.get_global(global_name)
                self.state.set_global(global_name, current - amount)
                self._effects_applied.append(f"dec {global_name} by {amount}")
            else:
                raise EvalError(f"'dec' expects 1-3 arguments, got {len(args)}")

        elif name == "set-in":
            # (set-in @obj '(:path :keys) value) - set nested property
            if len(args) != 3:
                raise EvalError(f"'set-in' expects 3 arguments, got {len(args)}")
            obj, path, value = args[0], args[1], args[2]
            if not isinstance(path, (list, tuple)) or len(path) == 0:
                raise EvalError("'set-in' path must be a non-empty list")
            self._set_in(obj, path, value)
            path_str = ".".join(str(k.name if hasattr(k, 'name') else k) for k in path)
            self._effects_applied.append(f"set-in {obj} {path_str} = {value}")

        elif name == "queue":
            if len(args) < 1 or len(args) > 2:
                raise EvalError(f"'queue' expects 1-2 arguments, got {len(args)}")
            event = args[0]
            countdown = args[1] if len(args) > 1 else None
            self.state.queue_event(event, countdown)
            self._effects_applied.append(
                f"queue {event}" + (f" (countdown={countdown})" if countdown else "")
            )

        elif name == "dequeue":
            if len(args) != 1:
                raise EvalError(f"'dequeue' expects 1 argument, got {len(args)}")
            event = args[0]
            self.state.dequeue_event(event)
            self._effects_applied.append(f"dequeue {event}")

        elif name == "take":
            if len(args) != 1:
                raise EvalError(f"'take' expects 1 argument, got {len(args)}")
            obj = args[0]
            self.state.move_object(obj, self.state.player_name)
            self._effects_applied.append(f"take {obj}")

        else:
            raise EvalError(f"Unknown mutation effect: {name}")

    def _set_in(self, obj: str, path: list, value: Any) -> None:
        """Set a nested property value on an object.

        For a single-key path like (:prop), directly sets the property.
        For multi-key paths like (:outer :inner), gets the outer property,
        updates it immutably, and sets the whole structure back.
        """
        if len(path) == 1:
            # Simple case: just set the property
            prop = path[0]
            if hasattr(prop, 'name'):
                prop = prop.name
            self.state.set_object_property(obj, prop, value)
            return

        # For nested paths, we need to get the existing structure,
        # create a modified copy, and set it back
        first_key = path[0]
        if hasattr(first_key, 'name'):
            first_key = first_key.name

        # Get the current value at the first key
        current = self.state.get_object_property(obj, first_key)
        if current is None:
            current = {}

        # Build the new nested value
        new_value = self._assoc_in(current, path[1:], value)
        self.state.set_object_property(obj, first_key, new_value)

    def _assoc_in(self, coll: Any, path: list, value: Any) -> Any:
        """Recursively associate a value at a nested path (like Clojure assoc-in)."""
        if not path:
            return value

        key = path[0]
        if hasattr(key, 'name'):
            key = key.name

        rest_path = path[1:]

        if isinstance(coll, dict):
            new_dict = dict(coll)
            new_dict[key] = self._assoc_in(coll.get(key), rest_path, value)
            return new_dict
        elif isinstance(coll, (list, tuple)):
            if isinstance(key, int):
                # Extend list if needed
                new_list = list(coll)
                while len(new_list) <= key:
                    new_list.append(None)
                new_list[key] = self._assoc_in(new_list[key] if key < len(coll) else None,
                                               rest_path, value)
                return new_list
            else:
                # Treat as keyword-value list
                from .sexpr import Keyword
                new_list = list(coll)
                for i in range(0, len(new_list) - 1, 2):
                    item_key = new_list[i]
                    key_name = item_key.name if isinstance(item_key, Keyword) else item_key
                    if key_name == key:
                        new_list[i + 1] = self._assoc_in(new_list[i + 1], rest_path, value)
                        return new_list
                # Key not found, append it
                new_list.extend([Keyword(key) if isinstance(key, str) else key,
                                self._assoc_in(None, rest_path, value)])
                return new_list
        else:
            # Create a new dict if current is None or not a collection
            return {key: self._assoc_in(None, rest_path, value)}

    def _collect_output(self, effect: list) -> None:
        """Collect an output effect (narrate, say).

        Output effects produce structured player-facing content:
        - (narrate "text") - general narrative
        - (say @speaker "text") - dialogue with speaker
        """
        name = effect[0]
        args = [self._resolve_arg(arg) for arg in effect[1:]]

        if name == "narrate":
            if len(args) != 1:
                raise EvalError(f"'narrate' expects 1 argument (text), got {len(args)}")
            text = args[0]
            self._output.append(("narrate", None, str(text)))

        elif name == "say":
            if len(args) != 2:
                raise EvalError(f"'say' expects 2 arguments (speaker, text), got {len(args)}")
            speaker, text = args[0], args[1]
            self._output.append(("say", str(speaker), str(text)))

    def _terminator_to_outcome(self, terminator: list) -> EffectOutcome:
        """Convert a terminator effect to an EffectOutcome."""
        name = terminator[0]
        args = terminator[1:]

        if name == "success":
            # New style: (success "reason text" [:context ...])
            # Old style: (success [:message ...] [:context ...])
            reason = None
            if args and isinstance(args[0], str):
                reason = args[0]
                args = args[1:]
            context = self._parse_terminator_kwargs(args)
            return EffectOutcome(
                outcome="success",
                reason=reason,
                context=context,
                effects_applied=self._effects_applied,
                output=self._output
            )

        elif name == "victory":
            # (victory) or (victory "message")
            # Victory is like success but sets victory=true in context
            reason = None
            context = {"victory": True}
            if args and isinstance(args[0], str):
                reason = args[0]
                args = args[1:]
            context.update(self._parse_terminator_kwargs(args))
            return EffectOutcome(
                outcome="success",
                reason=reason,
                context=context,
                effects_applied=self._effects_applied,
                output=self._output
            )

        elif name == "blocked":
            # New style: (blocked reason "message" [:key val ...]) where reason is a symbol/string
            # Or: (blocked "message") where message only, reason defaults to unknown
            # Old style: (blocked :reason keyword [:context ...])
            # NOTE: quasiquote converts Symbol to string, so reason may be string or Symbol
            reason = "unknown"
            context: dict[str, Any] = {}
            if args:
                first_arg = args[0]
                # Check for new positional style
                if isinstance(first_arg, Symbol) and not isinstance(first_arg, Keyword):
                    # (blocked reason "message" [:key val ...]) - reason is a symbol
                    reason = first_arg.name
                    if len(args) > 1:
                        context["message"] = args[1]
                    # Parse any remaining keyword args
                    if len(args) > 2:
                        context.update(self._parse_terminator_kwargs(args[2:]))
                elif isinstance(first_arg, str):
                    # Check if this is (blocked "reason" "message" ...) vs (blocked "message")
                    # If second arg is also a string, treat first as reason
                    if len(args) > 1 and isinstance(args[1], str):
                        # (blocked "reason" "message" [:key val ...]) - reason as string
                        reason = first_arg
                        context["message"] = args[1]
                        if len(args) > 2:
                            context.update(self._parse_terminator_kwargs(args[2:]))
                    else:
                        # (blocked "message" [:key val ...]) - just a message, no reason
                        context["message"] = first_arg
                        if len(args) > 1:
                            context.update(self._parse_terminator_kwargs(args[1:]))
                elif isinstance(first_arg, Keyword):
                    # Old style: (blocked :reason X :message "...")
                    context = self._parse_terminator_kwargs(args)
                    reason = context.pop("reason", "unknown")
                    if hasattr(reason, 'name'):
                        reason = reason.name
                    elif not isinstance(reason, str):
                        reason = str(reason)
            return EffectOutcome(
                outcome="blocked",
                reason=reason,
                context=context,
                effects_applied=self._effects_applied,
                output=self._output
            )

        elif name == "redirect":
            if len(args) < 1:
                raise EvalError("'redirect' requires an action argument")
            # First non-keyword arg is the action
            action = None
            context = {}
            i = 0
            while i < len(args):
                arg = args[i]
                if hasattr(arg, 'name') and isinstance(arg, Keyword):
                    # Keyword argument
                    if i + 1 < len(args):
                        context[arg.name] = args[i + 1]
                        i += 2
                    else:
                        i += 1
                else:
                    # The action
                    action = arg
                    i += 1
            if action is None:
                raise EvalError("'redirect' requires an action")
            return EffectOutcome(
                outcome="redirect",
                redirect_action=action,
                context=context,
                effects_applied=self._effects_applied,
                output=self._output
            )

        elif name == "default":
            context = self._parse_terminator_kwargs(args)
            return EffectOutcome(
                outcome="default",
                context=context,
                effects_applied=self._effects_applied,
                output=self._output
            )

        else:
            raise EvalError(f"Unknown terminator: {name}")

    def _parse_terminator_kwargs(self, args: list) -> dict[str, Any]:
        """Parse keyword arguments from terminator args.

        Args like [Keyword("message"), "Hello", Keyword("reason"), "locked"]
        become {"message": "Hello", "reason": "locked"}

        Special handling for :context - flattens ((key value) ...) pairs into result.
        """
        result: dict[str, Any] = {}
        i = 0
        while i < len(args):
            arg = args[i]
            # Check if it's a Keyword
            if hasattr(arg, 'name') and type(arg).__name__ == 'Keyword':
                key = arg.name
                if i + 1 < len(args):
                    val = args[i + 1]
                    if key == "context" and isinstance(val, list):
                        # Flatten ((key value) ...) into result dict
                        for pair in val:
                            if isinstance(pair, list) and len(pair) >= 2:
                                pair_key = pair[0]
                                pair_val = self._resolve_arg(pair[1])
                                result[pair_key] = pair_val
                    else:
                        result[key] = val
                    i += 2
                else:
                    i += 1
            else:
                i += 1
        return result


class EvalError(Exception):
    """Error during expression evaluation."""
    pass


class UnboundVariableError(EvalError):
    """Raised when referencing an unbound variable."""
    def __init__(self, name: str):
        super().__init__(f"Unbound variable: {name}")
        self.name = name


@dataclass
class Environment:
    """Lexical environment for variable bindings.

    Implements proper lexical scoping as in Scheme/Clojure. Each environment
    has a dictionary of bindings and an optional parent environment.

    Variable lookup walks up the parent chain until found or raises UnboundVariableError.
    """
    bindings: dict[str, Any] = field(default_factory=dict)
    parent: Optional["Environment"] = None

    def lookup(self, name: str) -> Any:
        """Look up a variable by name.

        Walks up the parent chain. Raises UnboundVariableError if not found.
        """
        if name in self.bindings:
            return self.bindings[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise UnboundVariableError(name)

    def has(self, name: str) -> bool:
        """Check if a variable is bound in this environment or any parent."""
        if name in self.bindings:
            return True
        if self.parent is not None:
            return self.parent.has(name)
        return False

    def extend(self, bindings: dict[str, Any]) -> "Environment":
        """Create a new environment extending this one with additional bindings."""
        return Environment(bindings=bindings, parent=self)


class ExprEvaluator:
    """
    Evaluate S-expressions against a world state.

    This evaluator handles both predicates (returning bool)
    and value expressions (returning any type).

    Supports user-defined functions via define_function():
        evaluator.define_function("double", ["x"], parse("(+ x x)"))
        evaluator.eval(parse("(double 5)"))  # Returns 10
    """

    def __init__(
        self,
        state: WorldState,
        functions: dict[str, GrueFn] | None = None,
        allow_mutations: bool = False,
        include_builtins: bool = True
    ):
        self.state = state
        self._allow_mutations = allow_mutations
        # User-defined functions: name -> GrueFn
        # If functions dict provided, use it directly (allows sharing between instances)
        # Otherwise, include built-in functions (held?, here?, first, empty?, etc.) by default
        if functions is not None:
            self._functions = functions  # Use the provided dict (shared)
            # Add builtins to the shared dict if requested
            if include_builtins:
                builtins = _get_cached_builtin_functions()
                for name, fn in builtins.items():
                    if name not in self._functions:
                        self._functions[name] = fn
        elif include_builtins:
            self._functions = dict(_get_cached_builtin_functions())
        else:
            self._functions = {}
        # Mutation handlers (only used when allow_mutations=True)
        self._mutation_handlers = self._init_mutation_handlers()
        # Map of special form names to handlers
        self._builtins: dict[str, Callable[..., Any]] = {
            # Arithmetic operators
            "+": self._eval_add,
            "-": self._eval_sub,
            "*": self._eval_mul,
            "/": self._eval_div,
            "mod": self._eval_mod,

            # Boolean operators
            "and": self._eval_and,
            "or": self._eval_or,
            "not": self._eval_not,
            "nil?": self._eval_nil,

            # Comparisons
            "=": self._eval_eq,
            ">": self._eval_gt,
            "<": self._eval_lt,
            ">=": self._eval_gte,
            "<=": self._eval_lte,

            # Object queries
            "player": self._eval_player,
            "loc": self._eval_loc,
            "prop": self._eval_prop,
            "desc": self._eval_desc,
            "ldesc": self._eval_ldesc,

            # Convenience predicates
            # NOTE: held?, here?, in?, held-by?, at?, loc? are now defined in builtins.grue
            "visible?": self._eval_visible,
            "inside?": self._eval_inside,  # recursive containment check
            "room?": self._eval_room,
            "in-room?": self._eval_in_room,

            # Collections/quantifiers
            "some": self._eval_some,
            "every?": self._eval_every,
            "contents": self._eval_contents,
            "visible": self._eval_visible_objects,
            "exits": self._eval_exits,
            "room-description": self._eval_room_description,

            # Exit queries (for movement)
            "exit?": self._eval_exit_exists,
            "exit-to": self._eval_exit_to,
            "exit-via": self._eval_exit_via,

            # Event queue
            "queued?": self._eval_queued,

            # First-class functions
            "fn": self._eval_fn,
            "defn": self._eval_defn,
            "if": self._eval_if,
            "let": self._eval_let,
            "cond": self._eval_cond,
            "when": self._eval_when,
            "match": self._eval_match,
            "condp": self._eval_condp,
            "->": self._eval_thread_first,
            "->>": self._eval_thread_last,
            "cond->": self._eval_cond_thread,
            "cond->>": self._eval_cond_thread_last,

            # Behavior results
            "success": self._eval_success,
            "blocked": self._eval_blocked,
            "redirect": self._eval_redirect,
            "default": self._eval_default,

            # Debug/REPL
            "print": self._eval_print,

            # Data constructors
            "quote": self._eval_quote,
            "quasiquote": self._eval_quasiquote,
            "list": self._eval_list,
            "range": self._eval_range,

            # Sequencing (like Clojure's do)
            "do": self._eval_do_seq,

            # String operations
            "str": self._eval_str,
            "join": self._eval_join,

            # Sequence operations (Clojure stdlib)
            # NOTE: first, empty? moved to builtins.grue
            "nth": self._eval_nth,
            "list-set": self._eval_list_set,
            "concat": self._eval_concat,
            "rest": self._eval_rest,
            "count": self._eval_count,
            "cons": self._eval_cons,
            "get-in": self._eval_get_in,

            # Higher-order collection functions
            "map": self._eval_map,
            "filter": self._eval_filter,
            "remove": self._eval_remove,
            "keep": self._eval_keep,
            "reduce": self._eval_reduce,
            "for": self._eval_for,
            "doseq": self._eval_doseq,

            # Side effects - controlled by allow_mutations flag
            # In behavior bodies (pure), these raise errors directing users to effect system
            # In EffectExecutor context (allow_mutations=True), these work normally
            "move": self._eval_mutation_dispatch,
            "set": self._eval_mutation_dispatch,
            "inc": self._eval_mutation_dispatch,
        }

    def eval(self, expr: SExpr, env: Optional[Environment] = None) -> Any:
        """Evaluate an S-expression.

        Args:
            expr: The expression to evaluate
            env: Optional lexical environment for local variable bindings.
                 If None, only globals are accessible. If provided, the
                 environment is searched first for symbol lookups.
        """
        if isinstance(expr, bool):
            return expr
        if isinstance(expr, int):
            return expr
        if isinstance(expr, str):
            return expr
        if isinstance(expr, (tuple, list)):
            # Data values (e.g., quoted lists) evaluate to themselves
            return expr
        if isinstance(expr, Symbol):
            # Handle boolean literals
            if expr.name.lower() == "true":
                return True
            if expr.name.lower() == "false":
                return False
            # Handle nil
            if expr.name.lower() == "nil":
                return None

            # Symbol lookup:
            # 1. Check lexical environment first (if present)
            # 2. Then check globals
            # 3. Fall back to string literal (for object/flag names)
            name = expr.name
            # Strip leading ? if present (used in user-facing params)
            lookup_name = name[1:] if name.startswith("?") else name

            if env is not None:
                # Check both with and without ? prefix
                if env.has(lookup_name):
                    return env.lookup(lookup_name)
                if name.startswith("?") and env.has(name):
                    return env.lookup(name)

            # Try global lookup
            try:
                return self.state.get_global(name)
            except (KeyError, AttributeError):
                # Special cases that return as string literals:
                # - Object references (@player, @door) - start with @
                # - Flag names (TAKEBIT, OPENBIT) - ALL-CAPS with optional prefix
                if name.startswith("@"):
                    return name  # Object reference
                if name.isupper() or (name.startswith("-") and name[1:].isupper()):
                    return name  # Flag name (e.g., TAKEBIT, -TAKEBIT)
                # Unknown symbol - raise error
                raise UnboundVariableError(name)
        if isinstance(expr, Keyword):
            # Keywords are self-evaluating (Clojure-style)
            return expr
        if isinstance(expr, SList):
            return self._eval_form(expr, env)
        if isinstance(expr, GrueFn):
            # Function values evaluate to themselves
            return expr

        raise EvalError(f"Cannot evaluate: {expr}")

    def _eval_form(self, form: SList, env: Optional[Environment] = None) -> Any:
        """Evaluate a list form (function call).

        Args:
            form: The list form to evaluate
            env: Current lexical environment
        """
        if len(form) == 0:
            raise EvalError("Cannot evaluate empty list () - use nil or '() for empty values")

        head = form[0]

        # If head is a symbol, look up builtins and user functions
        if isinstance(head, Symbol):
            name = head.name

            if name in self._builtins:
                return self._builtins[name](form, env)

            # Check user-defined functions
            if name in self._functions:
                return self._call_function(name, form, env)

            # Check if the symbol is bound to a function in the environment
            if env is not None:
                lookup_name = name[1:] if name.startswith("?") else name
                if env.has(lookup_name) or env.has(name):
                    fn_value = env.lookup(lookup_name) if env.has(lookup_name) else env.lookup(name)
                    if isinstance(fn_value, GrueFn):
                        args = [self.eval(arg, env) for arg in form.items[1:]]
                        return self.call_fn(fn_value, args)
                    # Not a function - fall through to error

            raise EvalError(f"Unknown function: {name}")

        # If head is a keyword, use it as a lookup function (Clojure-style)
        # (:key obj) => look up :key on obj
        # (:key obj default) => look up :key on obj, return default if not found
        if isinstance(head, Keyword):
            return self._eval_keyword_lookup(head, form, env)

        # If head is a list, evaluate it - might be a fn expression
        if isinstance(head, SList):
            fn_value = self.eval(head, env)
            if isinstance(fn_value, GrueFn):
                # Apply the function to remaining arguments
                args = [self.eval(arg, env) for arg in form.items[1:]]
                return self.call_fn(fn_value, args)
            raise EvalError(f"Cannot call non-function: {fn_value}")

        # If head is already a GrueFn (e.g., from environment lookup), apply it directly
        if isinstance(head, GrueFn):
            args = [self.eval(arg, env) for arg in form.items[1:]]
            return self.call_fn(head, args)

        raise EvalError(f"Expected function name or expression, got: {head}")

    def define_function(self, name: str, params: list[str], body: SExpr) -> None:
        """
        Define a user function.

        Args:
            name: Function name
            params: List of parameter names
            body: S-expression for function body
        """
        self._functions[name] = GrueFn(params=params, body=body)

    def _call_function(self, name: str, form: SList, env: Optional[Environment] = None) -> Any:
        """Call a user-defined function with argument binding."""
        fn = self._functions[name]
        args = form.items[1:]

        # Evaluate arguments in the current environment
        arg_values = [self.eval(arg, env) for arg in args]

        # Use call_fn which handles GrueFn properly
        return self.call_fn(fn, arg_values)

    # === Arithmetic operators ===

    def _eval_add(self, form: SList, env: Optional[Environment] = None) -> int | float:
        """(+ EXPR ...) - add numbers."""
        result = 0
        for item in form.items[1:]:
            result += self.eval(item, env)
        return result

    def _eval_sub(self, form: SList, env: Optional[Environment] = None) -> int | float:
        """(- EXPR ...) - subtract numbers.

        (- x) returns -x
        (- x y ...) returns x - y - ...
        """
        args = form.items[1:]
        if len(args) == 0:
            raise EvalError("'-' requires at least one argument")
        if len(args) == 1:
            return -self.eval(args[0], env)
        result = self.eval(args[0], env)
        for item in args[1:]:
            result -= self.eval(item, env)
        return result

    def _eval_mul(self, form: SList, env: Optional[Environment] = None) -> int | float:
        """(* EXPR ...) - multiply numbers."""
        result = 1
        for item in form.items[1:]:
            result *= self.eval(item, env)
        return result

    def _eval_div(self, form: SList, env: Optional[Environment] = None) -> int | float:
        """(/ EXPR EXPR) - divide numbers (integer division)."""
        args = form.items[1:]
        if len(args) < 2:
            raise EvalError("'/' requires at least two arguments")
        result = self.eval(args[0], env)
        for item in args[1:]:
            divisor = self.eval(item, env)
            if divisor == 0:
                raise EvalError("Division by zero")
            result //= divisor  # Integer division like ZIL
        return result

    def _eval_mod(self, form: SList, env: Optional[Environment] = None) -> int:
        """(mod X Y) - modulo."""
        if len(form) != 3:
            raise EvalError("'mod' requires exactly two arguments")
        x = self.eval(form[1], env)
        y = self.eval(form[2], env)
        if y == 0:
            raise EvalError("Modulo by zero")
        return x % y

    # === Boolean operators ===

    def _eval_and(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(and EXPR ...)"""
        for item in form.items[1:]:
            if not self.eval(item, env):
                return False
        return True

    def _eval_or(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(or EXPR ...)"""
        for item in form.items[1:]:
            if self.eval(item, env):
                return True
        return False

    def _eval_not(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(not EXPR)"""
        if len(form) != 2:
            raise EvalError(f"'not' expects 1 argument, got {len(form) - 1}")
        return not self.eval(form[1], env)

    def _eval_nil(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(nil? EXPR) - check if value is nil/None.

        Unlike (not x), this only returns true for nil/None,
        not for other falsy values like 0 or false.
        """
        if len(form) != 2:
            raise EvalError(f"'nil?' expects 1 argument, got {len(form) - 1}")
        return self.eval(form[1], env) is None

    # === Comparisons ===

    def _eval_eq(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(= A B)"""
        if len(form) != 3:
            raise EvalError(f"'=' expects 2 arguments, got {len(form) - 1}")
        a = self.eval(form[1], env)
        b = self.eval(form[2], env)
        return a == b

    def _eval_gt(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(> A B)"""
        if len(form) != 3:
            raise EvalError(f"'>' expects 2 arguments, got {len(form) - 1}")
        return self.eval(form[1], env) > self.eval(form[2], env)

    def _eval_lt(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(< A B)"""
        if len(form) != 3:
            raise EvalError(f"'<' expects 2 arguments, got {len(form) - 1}")
        return self.eval(form[1], env) < self.eval(form[2], env)

    def _eval_gte(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(>= A B)"""
        if len(form) != 3:
            raise EvalError(f"'>=' expects 2 arguments, got {len(form) - 1}")
        return self.eval(form[1], env) >= self.eval(form[2], env)

    def _eval_lte(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(<= A B)"""
        if len(form) != 3:
            raise EvalError(f"'<=' expects 2 arguments, got {len(form) - 1}")
        return self.eval(form[1], env) <= self.eval(form[2], env)

    # === Object queries ===

    def _eval_player(self, form: SList, env: Optional[Environment] = None) -> str:
        """(player) - returns the player entity name.

        Used for predicates that need to reference the player outside of
        behavior contexts where ?actor isn't bound.

        Example:
            (= (loc @key) (player))    ; is key held by player?
            (:outside (loc (player)))  ; is player in an outdoor room?
        """
        if len(form) != 1:
            raise EvalError(f"'player' expects 0 arguments, got {len(form) - 1}")
        return self.state.get_player_name()

    def _eval_loc(self, form: SList, env: Optional[Environment] = None) -> str | None:
        """(loc OBJ)"""
        if len(form) != 2:
            raise EvalError(f"'loc' expects 1 argument, got {len(form) - 1}")
        obj = self.eval(form[1], env)
        return self.state.get_object_location(obj)

    def _eval_prop(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(prop OBJ PROP)

        Property name is implicitly quoted if it's a symbol.
        Use (prop @obj property-name) or (prop @obj :property-name).
        """
        if len(form) != 3:
            raise EvalError(f"'prop' expects 2 arguments, got {len(form) - 1}")
        obj = self.eval(form[1], env)
        # Implicitly quote symbol property names
        prop_arg = form[2]
        if isinstance(prop_arg, Symbol):
            prop = prop_arg.name
        elif isinstance(prop_arg, Keyword):
            prop = prop_arg.name
        else:
            prop = self.eval(prop_arg, env)
        return self.state.get_object_property(obj, prop)

    def _eval_desc(self, form: SList, env: Optional[Environment] = None) -> str:
        """(desc ENTITY)

        Returns the evaluated :description of an entity (object or room).
        If description is a string, returns it directly.
        If description is a (fn () ...), evaluates it with ?self bound to the entity.
        """
        if len(form) != 2:
            raise EvalError(f"'desc' expects 1 argument, got {len(form) - 1}")
        entity = self.eval(form[1], env)
        desc = self.state.get_description(entity)

        if desc is None:
            return ""

        # If it's a string, return it directly
        if isinstance(desc, str):
            return desc

        # If it's an SList starting with 'fn', it's a function - evaluate it
        if isinstance(desc, SList) and len(desc) >= 1:
            first = desc[0]
            if isinstance(first, Symbol) and first.name == "fn":
                # Parse the fn and call it with ?self bound
                fn = self._parse_fn(desc)
                # Create environment with self bound
                new_env = Environment(
                    bindings={"self": entity},
                    parent=env
                )
                return self.eval(fn.body, new_env)

        # Otherwise, try to evaluate it as an expression with ?self bound
        new_env = Environment(bindings={"self": entity}, parent=env)
        result = self.eval(desc, new_env)
        return str(result) if result is not None else ""

    def _eval_ldesc(self, form: SList, env: Optional[Environment] = None) -> str:
        """(ldesc ENTITY)

        Returns the evaluated :ldesc (long description) of an entity.
        If ldesc is a string, returns it directly.
        If ldesc is a (fn () ...), evaluates it with ?self bound to the entity.
        """
        if len(form) != 2:
            raise EvalError(f"'ldesc' expects 1 argument, got {len(form) - 1}")
        entity = self.eval(form[1], env)
        ldesc = self.state.get_ldesc(entity)

        if ldesc is None:
            return ""

        # If it's a string, return it directly
        if isinstance(ldesc, str):
            return ldesc

        # If it's an SList starting with 'fn', it's a function - evaluate it
        if isinstance(ldesc, SList) and len(ldesc) >= 1:
            first = ldesc[0]
            if isinstance(first, Symbol) and first.name == "fn":
                # Parse the fn and call it with ?self bound
                fn = self._parse_fn(ldesc)
                # Create environment with self bound
                new_env = Environment(
                    bindings={"self": entity},
                    parent=env
                )
                return self.eval(fn.body, new_env)

        # Otherwise, try to evaluate it as an expression with ?self bound
        new_env = Environment(bindings={"self": entity}, parent=env)
        result = self.eval(ldesc, new_env)
        return str(result) if result is not None else ""

    def _parse_fn(self, form: SList) -> GrueFn:
        """Parse a (fn (params) body) form into a GrueFn."""
        if len(form) < 3:
            raise EvalError(f"'fn' requires params and body, got {form}")

        params_expr = form[1]
        body = form[2]

        params = []
        if isinstance(params_expr, SList):
            for p in params_expr.items:
                if isinstance(p, Symbol):
                    # Strip ? prefix if present
                    name = p.name[1:] if p.name.startswith("?") else p.name
                    params.append(name)
                else:
                    raise EvalError(f"fn parameter must be a symbol, got {p}")

        return GrueFn(params=params, body=body)

    # === Convenience predicates ===

    def _eval_visible(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(visible? OBJ)"""
        if len(form) != 2:
            raise EvalError(f"'visible?' expects 1 argument, got {len(form) - 1}")
        obj = self.eval(form[1], env)
        return self.state.is_visible(obj)

    # NOTE: held?, here?, loc?, in?, held-by?, at? moved to builtins.grue

    def _eval_inside(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(inside? OBJ CONTAINER) - recursive check if OBJ is inside CONTAINER.

        Returns true if:
        - OBJ's location is CONTAINER, OR
        - OBJ is inside something that is inside CONTAINER (recursively)

        Example: If @food is in @carton and @carton is in @microwave,
        (inside? @food @microwave) returns true.
        """
        if len(form) != 3:
            raise EvalError(f"'inside?' expects 2 arguments, got {len(form) - 1}")
        obj = self.eval(form[1], env)
        container = self.eval(form[2], env)

        # Walk up the containment chain
        current = obj
        max_depth = 10  # Prevent infinite loops
        for _ in range(max_depth):
            loc = self.state.get_object_location(current)
            if loc is None:
                return False
            if loc == container:
                return True
            # Check if loc is itself an object (not a room)
            if self.state.is_room(loc):
                return False
            current = loc
        return False

    def _eval_room(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(room? LOC)"""
        if len(form) != 2:
            raise EvalError(f"'room?' expects 1 argument, got {len(form) - 1}")
        loc = self.eval(form[1], env)
        return self.state.is_room(loc)

    def _eval_in_room(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(in-room? OBJ ROOM1 ROOM2 ...) - check if object is in any of the listed rooms.

        Typically used as (in-room? PLAYER MASS-AVE SMITH-ST) to check
        if the player is in one of several specific rooms.
        """
        if len(form) < 3:
            raise EvalError(f"'in-room?' expects at least 2 arguments, got {len(form) - 1}")

        obj = self.eval(form[1], env)
        obj_loc = self.state.get_object_location(obj)
        if obj_loc is None:
            return False

        # Check if object's location is any of the specified rooms
        for room_arg in form.items[2:]:
            room_name = self.eval(room_arg, env)
            if obj_loc == room_name:
                return True

        return False

    # === Collections/quantifiers ===

    def _eval_contents(self, form: SList, env: Optional[Environment] = None) -> list[str]:
        """(contents CONTAINER) - get contents of container"""
        if len(form) != 2:
            raise EvalError(f"'contents' expects 1 argument, got {len(form) - 1}")
        container = self.eval(form[1], env)
        return self.state.get_contents(container)

    def _eval_visible_objects(self, form: SList, env: Optional[Environment] = None) -> list[str]:
        """(visible) - get objects visible from current location"""
        if len(form) != 1:
            raise EvalError(f"'visible' expects 0 arguments, got {len(form) - 1}")
        return self.state.get_visible_objects()

    def _eval_exits(self, form: SList, env: Optional[Environment] = None) -> dict[str, str]:
        """(exits) - get available exits from current room as direction->destination map"""
        if len(form) != 1:
            raise EvalError(f"'exits' expects 0 arguments, got {len(form) - 1}")
        return self.state.get_exits()

    def _eval_room_description(self, form: SList, env: Optional[Environment] = None) -> str:
        """(room-description) or (room-description ROOM) - get room description"""
        if len(form) == 1:
            return self.state.get_room_description()
        elif len(form) == 2:
            room = self.eval(form[1], env)
            return self.state.get_room_description(room)
        else:
            raise EvalError(f"'room-description' expects 0-1 arguments, got {len(form) - 1}")

    # === Exit queries (for movement) ===

    def _eval_exit_exists(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(exit? ACTOR DIRECTION) - check if exit exists from actor's room."""
        if len(form) != 3:
            raise EvalError(f"'exit?' expects 2 arguments, got {len(form) - 1}")
        actor = self.eval(form[1], env)
        direction = self.eval(form[2], env)
        result = self.state.get_exit(actor, direction)
        return result is not None

    def _eval_exit_to(self, form: SList, env: Optional[Environment] = None) -> str | None:
        """(exit-to ACTOR DIRECTION) - get destination room for exit."""
        if len(form) != 3:
            raise EvalError(f"'exit-to' expects 2 arguments, got {len(form) - 1}")
        actor = self.eval(form[1], env)
        direction = self.eval(form[2], env)
        result = self.state.get_exit(actor, direction)
        return result[0] if result else None

    def _eval_exit_via(self, form: SList, env: Optional[Environment] = None) -> str | None:
        """(exit-via ACTOR DIRECTION) - get door object for exit (if any)."""
        if len(form) != 3:
            raise EvalError(f"'exit-via' expects 2 arguments, got {len(form) - 1}")
        actor = self.eval(form[1], env)
        direction = self.eval(form[2], env)
        result = self.state.get_exit(actor, direction)
        return result[1] if result else None

    # === Event queue ===

    def _eval_queued(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(queued? EVENT) - check if event is currently queued.

        Event name is implicitly quoted if it's a symbol.
        """
        if len(form) != 2:
            raise EvalError(f"'queued?' expects 1 argument, got {len(form) - 1}")
        # Implicitly quote symbol event names
        event_arg = form[1]
        if isinstance(event_arg, Symbol):
            event = event_arg.name
        else:
            event = self.eval(event_arg, env)
        return self.state.is_queued(event)

    # === First-class functions ===

    def _eval_fn(self, form: SList, env: Optional[Environment] = None) -> GrueFn:
        """(fn (params) body) - create a function value (closure).

        Captures the current lexical environment for proper closure semantics.

        Examples:
            (fn () (success))
            (fn (?x) (+ ?x 1))
            (fn (?a ?b) (if (> ?a ?b) ?a ?b))
        """
        if len(form) < 3:
            raise EvalError(f"'fn' expects (fn (params) body), got {len(form)} elements")

        params_expr = form[1]
        body = form[2]

        # Parse parameter list
        params: list[str] = []
        if isinstance(params_expr, SList):
            for p in params_expr.items:
                if isinstance(p, Symbol):
                    # Strip leading ? if present
                    name = p.name[1:] if p.name.startswith("?") else p.name
                    params.append(name)
                else:
                    raise EvalError(f"'fn' parameter must be a symbol, got {p}")
        elif params_expr is not None:
            raise EvalError(f"'fn' params must be a list, got {params_expr}")

        # Capture the current environment for proper closure semantics
        return GrueFn(params=params, body=body, captured_env=env)

    def _eval_defn(self, form: SList, env: Optional[Environment] = None) -> None:
        """(defn name (params) body) - define a named function.

        Examples:
            (defn double (x) (+ x x))
            (defn at-lobby? () (= (loc PLAYER) LOBBY))
            (defn greet (name) (str "Hello, " name))

        Note: Returns nil (None) after registering the function.
        Note: defn always creates top-level functions that don't capture env.
        """
        if len(form) != 4:
            raise EvalError(f"'defn' expects 3 arguments (name, params, body), got {len(form) - 1}")

        # Extract function name
        name_expr = form[1]
        if not isinstance(name_expr, Symbol):
            raise EvalError(f"'defn' name must be a symbol, got: {name_expr}")
        name = name_expr.name

        # Extract parameter list
        params_expr = form[2]
        if not isinstance(params_expr, SList):
            raise EvalError(f"'defn' params must be a list, got: {params_expr}")
        params: list[str] = []
        for p in params_expr.items:
            if isinstance(p, Symbol):
                # Strip leading ? if present (like in fn)
                param_name = p.name[1:] if p.name.startswith("?") else p.name
                params.append(param_name)
            else:
                raise EvalError(f"'defn' parameter must be a symbol, got: {p}")

        # Body is kept as-is (not evaluated until called)
        body = form[3]

        # Register the function (no captured environment for top-level defn)
        self._functions[name] = GrueFn(params=params, body=body)

        # defn returns nil
        return None

    def _eval_if(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(if condition then-expr else-expr) - conditional expression.

        Examples:
            (if (held? @key) (success) (blocked :reason no-key))
            (if (> score 10) "high" "low")
        """
        if len(form) < 3 or len(form) > 4:
            raise EvalError(f"'if' expects 2-3 arguments, got {len(form) - 1}")

        condition = self.eval(form[1], env)

        if condition:
            return self.eval(form[2], env)
        elif len(form) == 4:
            return self.eval(form[3], env)
        else:
            return None

    def _eval_when(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(when condition body...) - conditional with multiple body forms.

        Evaluates body forms only if condition is truthy. Returns last body result or None.

        Examples:
            (when (held? @key) (print "has key") (success))
            (when (> heat 20) (set @food :ruined true))
        """
        if len(form) < 3:
            raise EvalError(f"'when' expects at least 2 arguments, got {len(form) - 1}")

        condition = self.eval(form[1], env)
        if condition:
            result = None
            for expr in form.items[2:]:
                result = self.eval(expr, env)
            return result
        return None

    def _eval_let(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(let ((name value) ...) body ...) - local bindings.

        Uses let* semantics: each binding can reference earlier bindings.
        Supports multiple body expressions (like Scheme/Clojure).
        Returns the value of the last body expression.

        Examples:
            (let ((x 1)) (+ x 2))
            (let ((a (loc @player)) (b @room)) (= a b))
            (let ((?n 10)) (print ?n) (* ?n 2))  ; multiple body expressions
        """
        if len(form) < 3:
            raise EvalError(f"'let' expects at least 2 arguments, got {len(form) - 1}")

        bindings_expr = form[1]
        body_exprs = list(form.items[2:])  # All remaining expressions are body

        if not isinstance(bindings_expr, SList):
            raise EvalError(f"'let' bindings must be a list, got {bindings_expr}")

        # Wrap multiple body expressions in (do ...)
        if len(body_exprs) == 1:
            body = body_exprs[0]
        else:
            body = SList([Symbol("do")] + body_exprs)

        # Build up environment with let* semantics (each binding sees earlier bindings)
        current_env = env if env is not None else Environment()

        for binding in bindings_expr.items:
            if not isinstance(binding, SList) or len(binding) != 2:
                raise EvalError(f"'let' binding must be (name value), got {binding}")

            name_sym = binding[0]
            if not isinstance(name_sym, Symbol):
                raise EvalError(f"'let' binding name must be a symbol, got {name_sym}")

            name = name_sym.name
            # Strip leading ? if present
            base_name = name[1:] if name.startswith("?") else name

            # Evaluate value in current environment (sees earlier bindings)
            value = self.eval(binding[1], current_env)

            # Extend environment with this binding (both with and without ? prefix)
            new_bindings = {base_name: value, f"?{base_name}": value}
            current_env = current_env.extend(new_bindings)

        # Evaluate body in the final environment
        return self.eval(body, current_env)

    def _eval_cond(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(cond (test1 expr1 expr2 ...) (test2 result) ... (true default))

        Evaluates conditions in order and returns the result of the first
        matching branch. When a branch matches, ALL expressions after the test
        are evaluated in order, and the last one's value is returned.
        This follows standard Lisp/Scheme behavior.
        """
        for clause in form.items[1:]:
            if not isinstance(clause, SList) or len(clause) < 2:
                raise EvalError(f"Invalid cond clause: {clause}")

            test = clause[0]

            if self.eval(test, env):
                # Evaluate all expressions in the clause, return the last one
                result = None
                for expr in clause.items[1:]:
                    result = self.eval(expr, env)
                return result

        return None  # No clause matched

    def _eval_match(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(match (expr1 expr2 ...) (pattern1 result1) (pattern2 result2) ...)

        Pattern matching on a tuple of values.

        Example:
            (match ((has-flag? ?self LOCKED) (has-flag? ?self OPEN))
              ((true _)      (blocked :reason locked))
              ((_ true)      (blocked :reason already-open))
              ((false false) (success)))

        Pattern elements:
            - `_` or `?_` : wildcard, matches anything
            - `true`/`false` : literal boolean match
            - other literals : exact match
            - symbols starting with `?` : bind matched value to that name
        """
        if len(form) < 3:
            raise EvalError("'match' requires values and at least one clause")

        values_expr = form[1]
        if not isinstance(values_expr, SList):
            raise EvalError("'match' first argument must be a list of expressions")

        # Evaluate all values upfront in current environment
        values = [self.eval(v, env) for v in values_expr.items]

        # Try each clause
        for clause in form.items[2:]:
            if not isinstance(clause, SList) or len(clause) < 2:
                raise EvalError(f"Invalid match clause: {clause}")

            pattern = clause[0]
            result = clause[1]

            if not isinstance(pattern, SList):
                raise EvalError(f"Match pattern must be a list, got: {pattern}")

            if len(pattern) != len(values):
                raise EvalError(
                    f"Pattern length {len(pattern)} doesn't match values length {len(values)}"
                )

            # Try to match pattern
            bindings: dict[str, Any] = {}
            matched = True

            for pat_elem, val in zip(pattern.items, values):
                if isinstance(pat_elem, Symbol):
                    name = pat_elem.name
                    if name == "_" or name == "?_":
                        # Wildcard - matches anything
                        continue
                    elif name.startswith("?"):
                        # Binding - capture value
                        bindings[name[1:]] = val
                        bindings[name] = val  # Also bind with ?
                    elif name.lower() == "true":
                        if val is not True:
                            matched = False
                            break
                    elif name.lower() == "false":
                        if val is not False:
                            matched = False
                            break
                    else:
                        # Symbol literal - check equality
                        if val != name:
                            matched = False
                            break
                else:
                    # Literal value (number, string, etc.)
                    if self.eval(pat_elem, env) != val:
                        matched = False
                        break

            if matched:
                # Extend environment with match bindings and evaluate result
                if bindings:
                    match_env = (env or Environment()).extend(bindings)
                else:
                    match_env = env
                return self.eval(result, match_env)

        return None  # No pattern matched

    def _eval_condp(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(condp pred expr test1 result1 test2 result2 ...)

        Compare expr against test values using pred.

        Example:
            (condp = state
              :locked (blocked :reason locked)
              :open   (blocked :reason already-open)
              :closed (success))

            (condp > health
              0   (defeat)
              10  (warn)
              100 (success))

        Evaluates (pred test-val expr) for each test value.
        Returns result of first truthy test.
        """
        if len(form) < 4:
            raise EvalError("'condp' requires pred, expr, and at least one clause")

        pred = form[1]
        expr = form[2]
        expr_val = self.eval(expr, env)

        # Process clauses in pairs
        items = list(form.items[3:])
        i = 0
        while i < len(items) - 1:
            # Implicitly quote symbol test values (like case in other Lisps)
            test_item = items[i]
            if isinstance(test_item, Symbol):
                test_val = test_item.name
            else:
                test_val = self.eval(test_item, env)

            result = items[i + 1]

            # Evaluate predicate call: (pred test-val expr-val)
            # Build SList with evaluated values (wrapped for eval)
            pred_call = SList([pred, test_val, expr_val])
            if self.eval(pred_call, env):
                return self.eval(result, env)

            i += 2

        # Handle odd trailing element as default
        if i < len(items):
            return self.eval(items[i], env)

        return None

    def _eval_thread_first(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(-> initial expr1 expr2 ...)

        Thread-first macro. Threads value as first argument through expressions.

        Examples:
            (-> 5 (+ 3) (* 2))        => (* (+ 5 3) 2) => 16
            (-> @obj :prop)           => (:prop @obj)
            (-> @obj (:nested :key))  => (:key (:nested @obj))

        Each expression receives the previous result as its first argument.
        If expr is not a list, it's called with value as sole argument.
        """
        if len(form) < 2:
            raise EvalError("'->' requires an initial value")

        value = self.eval(form[1], env)

        for expr in form.items[2:]:
            if isinstance(expr, SList) and len(expr) > 0:
                # Insert value after the function name: (fn val arg1 arg2 ...)
                threaded = SList([expr[0], value] + list(expr.items[1:]))
                value = self.eval(threaded, env)
            else:
                # Just call with value as argument: (expr val)
                threaded = SList([expr, value])
                value = self.eval(threaded, env)

        return value

    def _eval_thread_last(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(->> initial expr1 expr2 ...)

        Thread-last macro. Threads value as last argument through expressions.

        Examples:
            (->> (range 5) (filter odd?) (map inc))
            => (map inc (filter odd? (range 5)))

        Each expression receives the previous result as its last argument.
        If expr is not a list, it's called with value as sole argument.
        """
        if len(form) < 2:
            raise EvalError("'->>' requires an initial value")

        value = self.eval(form[1], env)

        for expr in form.items[2:]:
            if isinstance(expr, SList) and len(expr) > 0:
                # Append value as last argument: (fn arg1 arg2 ... val)
                threaded = SList(list(expr.items) + [value])
                value = self.eval(threaded, env)
            else:
                # Just call with value as argument: (expr val)
                threaded = SList([expr, value])
                value = self.eval(threaded, env)

        return value

    def _eval_cond_thread(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(cond-> initial test1 expr1 test2 expr2 ...)

        Conditional threading - threads value through exprs when tests pass.
        Value is threaded as FIRST argument.

        Example:
            (cond-> {}
              true           (assoc :a 1)
              (has-flag? x)  (assoc :b 2))

        If test passes, evaluates (expr threaded-value).
        """
        if len(form) < 2:
            raise EvalError("'cond->' requires an initial value")

        value = self.eval(form[1], env)

        # Process clauses in pairs
        items = list(form.items[2:])
        i = 0
        while i < len(items) - 1:
            test = items[i]
            expr = items[i + 1]

            if self.eval(test, env):
                # Thread value as first argument
                if isinstance(expr, SList) and len(expr) > 0:
                    # Insert value after the function name
                    threaded = SList([expr[0], value] + list(expr.items[1:]))
                    value = self.eval(threaded, env)
                else:
                    # Just call with value as argument
                    threaded = SList([expr, value])
                    value = self.eval(threaded, env)

            i += 2

        return value

    def _eval_cond_thread_last(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(cond->> initial test1 expr1 test2 expr2 ...)

        Conditional threading - threads value through exprs when tests pass.
        Value is threaded as LAST argument.

        Example:
            (cond->> (list)
              (has-flag? ?self LOCKED) (cons :locked)
              (has-flag? ?self OPEN)   (cons :open))

        If test passes, evaluates (expr ... threaded-value).
        """
        if len(form) < 2:
            raise EvalError("'cond->>' requires an initial value")

        value = self.eval(form[1], env)

        # Process clauses in pairs
        items = list(form.items[2:])
        i = 0
        while i < len(items) - 1:
            test = items[i]
            expr = items[i + 1]

            if self.eval(test, env):
                # Thread value as last argument
                if isinstance(expr, SList) and len(expr) > 0:
                    # Append value to the end
                    threaded = SList(list(expr.items) + [value])
                    value = self.eval(threaded, env)
                else:
                    # Just call with value as argument
                    threaded = SList([expr, value])
                    value = self.eval(threaded, env)

            i += 2

        return value

    def call_fn(self, fn: GrueFn, args: list[Any]) -> Any:
        """Call a GrueFn with the given arguments.

        This is used by the behavior system and can also be used for
        general function application.

        Uses proper lexical scoping: the function body is evaluated in an
        environment that extends the function's captured environment with
        the parameter bindings.
        """
        if len(args) != len(fn.params):
            raise EvalError(
                f"Function expects {len(fn.params)} arguments, got {len(args)}"
            )

        # Build parameter bindings (both with and without ? prefix for convenience)
        param_bindings: dict[str, Any] = {}
        for param, value in zip(fn.params, args):
            param_bindings[param] = value
            # Also bind with ? prefix for user convenience
            param_bindings[f"?{param}"] = value

        # Create call environment extending the captured environment
        if fn.captured_env is not None:
            call_env = fn.captured_env.extend(param_bindings)
        else:
            # Function has no captured environment (e.g., top-level defn)
            call_env = Environment(bindings=param_bindings)

        # Evaluate body in the call environment
        return self.eval(fn.body, call_env)

    # === Behavior Results ===

    def _substitute_vars(self, expr: SExpr, env: Optional[Environment]) -> SExpr:
        """Substitute ?-prefixed symbols with their values from the environment.

        Used to resolve variables in redirect actions so they can be dispatched
        later when the environment is no longer available.
        """
        if isinstance(expr, Symbol):
            name = expr.name
            if name.startswith("?") and env is not None:
                lookup_name = name[1:]
                if env.has(lookup_name):
                    value = env.lookup(lookup_name)
                    # If value is a string, convert to Symbol
                    if isinstance(value, str):
                        return Symbol(value)
                    return value
            return expr
        elif isinstance(expr, SList):
            # Recursively substitute in list items
            new_items = [self._substitute_vars(item, env) for item in expr.items]
            return SList(new_items)
        else:
            return expr

    def _parse_kwargs(self, form: SList, start: int = 1) -> dict[str, Any]:
        """Parse keyword arguments from a form starting at given index."""
        kwargs: dict[str, Any] = {}
        items = list(form.items[start:])
        i = 0
        while i < len(items):
            if isinstance(items[i], Keyword):
                key = items[i].name
                if i + 1 < len(items):
                    # Don't evaluate the value - keep it as SExpr for effects
                    kwargs[key] = items[i + 1]
                    i += 2
                else:
                    raise EvalError(f"Keyword :{key} has no value")
            else:
                i += 1
        return kwargs

    def _parse_kwargs_from_list(self, items: list) -> dict[str, Any]:
        """Parse keyword arguments from a list of items."""
        kwargs: dict[str, Any] = {}
        i = 0
        while i < len(items):
            if isinstance(items[i], Keyword):
                key = items[i].name
                if i + 1 < len(items):
                    kwargs[key] = items[i + 1]
                    i += 2
                else:
                    raise EvalError(f"Keyword :{key} has no value")
            else:
                i += 1
        return kwargs

    def _parse_context_list(
        self, expr: SExpr, env: Optional[Environment] = None
    ) -> dict[str, Any]:
        """Parse context in format ((key value) (key value) ...).

        Keys are literal identifiers. Values are evaluated if they're expressions
        (SLists like (str ...) or (if ...)), otherwise treated as literals.
        """
        result: dict[str, Any] = {}
        if isinstance(expr, SList):
            for item in expr.items:
                if isinstance(item, SList) and len(item) >= 2:
                    key = item[0]
                    val = item[1]
                    key_str = key.name if isinstance(key, Symbol) else str(key)
                    # Evaluate expressions, keep simple values as literals
                    if isinstance(val, SList):
                        result[key_str] = self.eval(val, env)
                    elif isinstance(val, Symbol):
                        # Try to evaluate symbol in environment
                        # This handles defs like hacker-desc
                        # If not found, fall back to symbol name as literal
                        try:
                            result[key_str] = self.eval(val, env)
                        except EvalError:
                            result[key_str] = val.name
                    else:
                        result[key_str] = str(val)
        return result

    def _eval_success(self, form: SList, env: Optional[Environment] = None) -> BehaviorSuccess:
        """(success "message" [:key value ...]) or (success [:key value ...])

        Examples:
            (success)
            (success "Done!")                        ; New style with message
            (success :message "Done!")               ; Old keyword style
            (success :context ((mechanism push-bar)))
        """
        context: dict[str, Any] = {}

        # Check for new positional style: (success "message" [:key value ...])
        args = form.items[1:]  # Skip the 'success' symbol
        if args:
            first_arg = args[0]
            if isinstance(first_arg, str):
                # (success "message" [:key val ...]) - positional message
                context["message"] = first_arg
                # Parse any remaining keyword args
                if len(args) > 1:
                    remaining_kwargs = self._parse_kwargs_from_list(args[1:])
                    for key, val in remaining_kwargs.items():
                        if key == "context":
                            context.update(self._parse_context_list(val, env))
                        else:
                            context[key] = self.eval(val, env)
            elif isinstance(first_arg, SList):
                # Could be (success (str ...)) - evaluate as message
                context["message"] = self.eval(first_arg, env)
                # Parse any remaining keyword args
                if len(args) > 1:
                    remaining_kwargs = self._parse_kwargs_from_list(args[1:])
                    for key, val in remaining_kwargs.items():
                        if key == "context":
                            context.update(self._parse_context_list(val, env))
                        else:
                            context[key] = self.eval(val, env)
            elif isinstance(first_arg, Keyword):
                # Old keyword style: (success :message "..." [:key val ...])
                kwargs = self._parse_kwargs(form)
                for key, val in kwargs.items():
                    if key == "context":
                        context.update(self._parse_context_list(val, env))
                    elif key == "message":
                        context[key] = self.eval(val, env)
                    else:
                        context[key] = self.eval(val, env)

        return BehaviorSuccess(context=context)

    def _eval_blocked(self, form: SList, env: Optional[Environment] = None) -> BehaviorBlocked:
        """(blocked "message" [:context ((key val) ...)])

        The preferred form is simply (blocked "message"). Reason codes are deprecated
        and ignored. For backward compatibility, legacy forms are parsed but reason
        codes are not exposed.

        Examples:
            (blocked "Something went wrong.")                    ; Preferred
            (blocked :message "The door is locked.")             ; Keyword style (legacy)
            (blocked :reason ignored :message "The door is locked.")  ; Reason ignored
        """
        context: dict[str, Any] = {}

        args = form.items[1:]  # Skip the 'blocked' symbol
        if args:
            first_arg = args[0]
            if isinstance(first_arg, str):
                # (blocked "message") - preferred form
                context["message"] = str(first_arg)
            elif isinstance(first_arg, SList):
                # Could be (blocked (str ...)) - evaluate as message
                context["message"] = self.eval(first_arg, env)
            elif isinstance(first_arg, Keyword):
                # Keyword style: (blocked :reason X :message "..." :context ...)
                # Parse but ignore :reason
                kwargs = self._parse_kwargs(form)
                for key, val in kwargs.items():
                    if key == "reason":
                        # Ignore reason codes - they are deprecated
                        pass
                    elif key == "context":
                        context.update(self._parse_context_list(val))
                    else:
                        context[key] = self.eval(val, env)

        # Always use "unknown" as reason - reason codes are deprecated
        return BehaviorBlocked(reason="unknown", context=context)

    def _eval_redirect(self, form: SList, env: Optional[Environment] = None) -> BehaviorRedirect:
        """(redirect ACTION [:key value ...]) or (redirect :action ACTION) or (redirect :to ROOM)

        Examples:
            (redirect (do @other-door :open))
            (redirect :action (do @other-door :open))
            (redirect :to @room)  ; Redirect movement to a specific room
        """
        if len(form) < 2:
            raise EvalError("'redirect' requires an action or :to destination")

        action = None
        context: dict[str, Any] = {}

        # Check if first arg is action (SList) or keywords
        if isinstance(form[1], SList):
            action = form[1]
            kwargs = self._parse_kwargs(form, start=2)
        else:
            kwargs = self._parse_kwargs(form, start=1)

        for k, v in kwargs.items():
            if k == "action":
                # Substitute ?-prefixed symbols with their values from the environment
                action = self._substitute_vars(v, env)
            elif k == "to":
                # (redirect :to @room) - create a synthetic go action to the room
                # This is used in :through behaviors to redirect movement
                room = self.eval(v, env) if not isinstance(v, Symbol) else v.name
                # Store the destination in context, runtime will handle the move
                context["redirect_to"] = room
                # Create a placeholder action (runtime will use redirect_to instead)
                action = SList([Symbol("go"), Keyword("to"), Symbol(room) if isinstance(room, str) else v])
            elif k == "context":
                context.update(self._parse_context_list(v))
            else:
                if isinstance(v, Symbol):
                    context[k] = v.name
                else:
                    context[k] = self.eval(v, env)

        if action is None:
            raise EvalError("'redirect' requires an action or :to destination")

        return BehaviorRedirect(action=action, context=context)

    def _eval_default(self, form: SList, env: Optional[Environment] = None) -> BehaviorDefault:
        """(default [ACTION] [:key value ...])

        Examples:
            (default)
            (default (do @container :open))
            (default :action (do @container :open))
        """
        action = None
        context: dict[str, Any] = {}

        if len(form) > 1:
            # Check if first arg is an action (SList) or keyword
            if isinstance(form[1], SList):
                action = form[1]
                kwargs = self._parse_kwargs(form, start=2)
            else:
                kwargs = self._parse_kwargs(form, start=1)

            for k, v in kwargs.items():
                if k == "action":
                    # Don't evaluate action - keep as SExpr
                    action = v
                elif k == "context":
                    context.update(self._parse_context_list(v))
                else:
                    if isinstance(v, Symbol):
                        context[k] = v.name
                    else:
                        context[k] = self.eval(v, env)

        return BehaviorDefault(action=action, context=context)

    # === Debug/REPL ===

    def _eval_print(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(print EXPR ...) - Print values to stdout.

        Prints each argument on its own line with formatted output.
        For objects, shows location, flags, and properties.
        Returns the last value printed (or nil if none).
        """
        result: Any = None
        for item in form.items[1:]:
            result = self.eval(item, env)
            self._print_value(result)
        return result

    def _print_value(self, value: Any, indent: int = 0) -> None:
        """Format and print a value."""
        prefix = "  " * indent

        if value is None:
            print(f"{prefix}nil")
        elif isinstance(value, bool):
            print(f"{prefix}{str(value).lower()}")
        elif isinstance(value, (int, float)):
            print(f"{prefix}{value}")
        elif isinstance(value, str):
            # Check if it's a room or object
            if self.state.is_room(value):
                print(f"{prefix}@{value} (room)")
            elif self.state.is_object(value):
                loc = self.state.get_object_location(value)
                print(f"{prefix}@{value}")
                print(f"{prefix}  location: {loc or 'nil'}")
            else:
                # Plain string
                print(f"{prefix}{value}")
        elif isinstance(value, list):
            if not value:
                print(f"{prefix}()")
            else:
                print(f"{prefix}(")
                for item in value:
                    self._print_value(item, indent + 1)
                print(f"{prefix})")
        elif isinstance(value, dict):
            if not value:
                print(f"{prefix}{{}}")
            else:
                print(f"{prefix}{{")
                for k, v in value.items():
                    print(f"{prefix}  {k}:")
                    self._print_value(v, indent + 2)
                print(f"{prefix}}}")
        elif isinstance(value, GrueFn):
            params = " ".join(value.params)
            print(f"{prefix}<fn ({params}) ...>")
        else:
            print(f"{prefix}{value}")

    # === Keyword as function (Clojure-style) ===

    def _eval_keyword_lookup(self, key: Keyword, form: SList, env: Optional[Environment] = None) -> Any:
        """(:key obj [default]) - look up key on obj.

        Works on:
        - Objects: looks up runtime property
        - Quoted maps/lists with keyword-value pairs: (:foo '(:foo "bar")) => "bar"
        - Dicts: standard key lookup

        Returns None for missing keys (like Clojure's keyword lookup), or the default if provided.

        Examples:
            (:size @pc) => 30
            (:missing @pc) => None
            (:missing @pc "default") => "default"
            (:foo '(:foo "bar" :baz "qux")) => "bar"
        """
        if len(form) < 2 or len(form) > 3:
            raise EvalError(f"Keyword lookup requires 1-2 arguments: (:{key.name} obj [default])")

        target = self.eval(form[1], env)
        has_default = len(form) == 3
        default = self.eval(form[2], env) if has_default else None
        key_name = key.name

        # Handle dict
        if isinstance(target, dict):
            if key_name in target:
                return target[key_name]
            return default

        # Handle list (quoted keyword-value list like '(:foo "bar" :baz "qux"))
        if isinstance(target, (list, tuple)):
            items = target
            for i in range(0, len(items) - 1, 2):
                if isinstance(items[i], Keyword) and items[i].name == key_name:
                    return items[i + 1]
            return default

        # Handle object name (string) - look up property via state
        if isinstance(target, str):
            if self.state.has_object_property(target, key_name):
                return self.state.get_object_property(target, key_name)
            return default

        if has_default:
            return default
        raise EvalError(f"Cannot look up ':{key_name}' on {type(target).__name__}")

    # === Data constructors ===

    def _eval_quote(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(quote EXPR) or 'EXPR - return EXPR unevaluated, as Python data.

        Converts AST types to Python native types:
        - SList → list (recursively)
        - Symbol → str (the symbol name)
        - Keyword → Keyword (preserved for keyword lookup)
        - Primitives → as-is

        Examples:
            '(a b c) => ["a", "b", "c"]
            'foo => "foo"
            '(:foo "bar") => [Keyword("foo"), "bar"]
            '42 => 42
        """
        if len(form) != 2:
            raise EvalError("'quote' requires exactly one argument")
        return quote_to_data(form[1])

    def _eval_quasiquote(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(quasiquote EXPR) or `EXPR - like quote but allows unquote escapes.

        Within a quasiquoted expression:
        - ,EXPR (unquote) evaluates EXPR and inserts the result
        - ,@EXPR (unquote-splicing) evaluates EXPR (must return list) and splices elements

        Examples:
            `(a b c) => ["a", "b", "c"]  (same as quote when no unquotes)
            `(a ,(+ 1 2) c) => ["a", 3, "c"]  (unquote evaluates)
            `(a ,@(list 1 2 3) b) => ["a", 1, 2, 3, "b"]  (unquote-splicing splices)
            `((set x ,(compute-val)) (success)) => [["set", "x", <computed>], ["success"]]
        """
        if len(form) != 2:
            raise EvalError("'quasiquote' requires exactly one argument")
        return self._expand_quasiquote(form[1], env)

    def _expand_quasiquote(self, expr: SExpr, env: Optional[Environment] = None) -> Any:
        """Recursively expand a quasiquoted expression."""
        if isinstance(expr, SList):
            items = expr.items
            # Check for (unquote expr) form
            if (len(items) == 2 and
                isinstance(items[0], Symbol) and
                items[0].name == "unquote"):
                # Evaluate the unquoted expression
                return self.eval(items[1], env)

            # Check for (unquote-splicing expr) - error, must be inside a list
            if (len(items) >= 1 and
                isinstance(items[0], Symbol) and
                items[0].name == "unquote-splicing"):
                raise EvalError("unquote-splicing (,@) not valid outside of a list")

            # Process list elements, handling unquote-splicing
            result = []
            for item in items:
                if (isinstance(item, SList) and
                    len(item.items) == 2 and
                    isinstance(item.items[0], Symbol) and
                    item.items[0].name == "unquote-splicing"):
                    # Evaluate and splice the list
                    spliced = self.eval(item.items[1], env)
                    if not isinstance(spliced, (list, tuple)):
                        raise EvalError(
                            f"unquote-splicing (,@) requires a list, got {type(spliced).__name__}"
                        )
                    result.extend(spliced)
                else:
                    # Recursively expand
                    result.append(self._expand_quasiquote(item, env))
            return result

        # Non-list: convert to data (like quote)
        return quote_to_data(expr)

    def _eval_list(self, form: SList, env: Optional[Environment] = None) -> list[Any]:
        """(list EXPR ...) - construct a list from evaluated arguments.

        Examples:
            (list 1 2 3) => [1, 2, 3]
            (list "a" "b") => ["a", "b"]
        """
        return [self.eval(item, env) for item in form.items[1:]]

    def _eval_range(self, form: SList, env: Optional[Environment] = None) -> list[int]:
        """(range END) or (range START END) or (range START END STEP) - generate integer sequence.

        Clojure-style range:
            (range 5) => (0 1 2 3 4)
            (range 2 5) => (2 3 4)
            (range 0 10 2) => (0 2 4 6 8)
            (range 5 0 -1) => (5 4 3 2 1)
        """
        argc = len(form) - 1
        if argc == 0:
            raise EvalError("'range' expects 1-3 arguments, got 0")
        if argc > 3:
            raise EvalError(f"'range' expects 1-3 arguments, got {argc}")

        args = [self.eval(arg, env) for arg in form.items[1:]]
        for i, arg in enumerate(args):
            if not isinstance(arg, int):
                raise EvalError(f"'range' argument {i+1} must be int, got {type(arg).__name__}")

        if argc == 1:
            # (range end) -> 0..end-1
            return list(range(args[0]))
        elif argc == 2:
            # (range start end) -> start..end-1
            return list(range(args[0], args[1]))
        else:
            # (range start end step)
            return list(range(args[0], args[1], args[2]))

    def _eval_do_seq(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(do EXPR ...) - evaluate expressions in sequence, return last.

        Like Clojure's do. Useful for side effects.

        Examples:
            (do (print "step 1") (print "step 2") 42)
            (do (print "hello") 42)
        """
        result = None
        for item in form.items[1:]:
            result = self.eval(item, env)
        return result

    def _eval_str(self, form: SList, env: Optional[Environment] = None) -> str:
        """(str EXPR ...) - concatenate arguments as strings.

        Examples:
            (str "hello" " " "world") => "hello world"
            (str "count: " 42) => "count: 42"
        """
        parts = [str(self.eval(item, env)) for item in form.items[1:]]
        return "".join(parts)

    def _eval_join(self, form: SList, env: Optional[Environment] = None) -> str:
        """(join SEPARATOR COLL) - join collection elements with separator.

        Examples:
            (join ", " '("a" "b" "c")) => "a, b, c"
            (join "-" '(1 2 3)) => "1-2-3"
        """
        if len(form) != 3:
            raise EvalError(f"'join' expects 2 arguments, got {len(form) - 1}")
        separator = str(self.eval(form.items[1], env))
        coll = self.eval(form.items[2], env)

        if coll is None:
            return ""
        elif isinstance(coll, (list, tuple)):
            return separator.join(str(item) for item in coll)
        else:
            raise EvalError(f"'join' expects sequence, got {type(coll).__name__}")

    # === Sequence operations (Clojure stdlib) ===

    def _eval_nth(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(nth COLL INDEX [NOT-FOUND]) - get element at index.

        Examples:
            (nth '(a b c) 1) => 'b'
            (nth '(a b c) 5 nil) => nil
        """
        if len(form) < 3:
            raise EvalError(f"'nth' expects at least 2 arguments, got {len(form) - 1}")
        coll = self.eval(form.items[1], env)
        idx = self.eval(form.items[2], env)
        not_found = self.eval(form.items[3], env) if len(form) > 3 else None

        if not isinstance(idx, int):
            raise EvalError(f"'nth' index must be int, got {type(idx).__name__}")

        if isinstance(coll, (list, tuple)):
            if 0 <= idx < len(coll):
                return coll[idx]
            elif len(form) > 3:
                return not_found
            else:
                raise EvalError(f"Index {idx} out of bounds for collection of size {len(coll)}")
        elif isinstance(coll, str):
            if 0 <= idx < len(coll):
                return coll[idx]
            elif len(form) > 3:
                return not_found
            else:
                raise EvalError(f"Index {idx} out of bounds for string of length {len(coll)}")
        else:
            raise EvalError(f"'nth' expects sequence, got {type(coll).__name__}")

    def _eval_list_set(self, form: SList, env: Optional[Environment] = None) -> list:
        """(list-set COLL INDEX VALUE) - return new list with element at index replaced.

        Examples:
            (list-set '(a b c) 1 'x') => '(a x c)'
            (list-set '(1 2 3 4) 0 99) => '(99 2 3 4)'
        """
        if len(form) != 4:
            raise EvalError(f"'list-set' expects 3 arguments, got {len(form) - 1}")
        coll = self.eval(form.items[1], env)
        idx = self.eval(form.items[2], env)
        value = self.eval(form.items[3], env)

        if not isinstance(idx, int):
            raise EvalError(f"'list-set' index must be int, got {type(idx).__name__}")

        if isinstance(coll, (list, tuple)):
            items = list(coll)
            if 0 <= idx < len(items):
                result = items.copy()
                result[idx] = value
                return result
            else:
                raise EvalError(f"Index {idx} out of bounds for list of size {len(items)}")
        else:
            raise EvalError(f"'list-set' expects list, got {type(coll).__name__}")

    def _eval_concat(self, form: SList, env: Optional[Environment] = None) -> list:
        """(concat LIST ...) - concatenate lists.

        Examples:
            (concat '(1 2) '(3 4)) => [1, 2, 3, 4]
            (concat '(a b) '(c) '(d e)) => ["a", "b", "c", "d", "e"]
            (concat) => []
        """
        result = []
        for item in form.items[1:]:
            coll = self.eval(item, env)
            if coll is None:
                continue  # nil is treated as empty list
            if not isinstance(coll, (list, tuple)):
                raise EvalError(f"'concat' expects lists, got {type(coll).__name__}")
            result.extend(coll)
        return result

    # NOTE: first moved to builtins.grue

    def _eval_rest(self, form: SList, env: Optional[Environment] = None) -> list:
        """(rest COLL) - return all but first element as list."""
        if len(form) != 2:
            raise EvalError(f"'rest' expects 1 argument, got {len(form) - 1}")
        coll = self.eval(form.items[1], env)

        if isinstance(coll, (list, tuple)):
            return list(coll[1:]) if coll else []
        elif isinstance(coll, str):
            return list(coll[1:]) if coll else []
        else:
            raise EvalError(f"'rest' expects sequence, got {type(coll).__name__}")

    def _eval_count(self, form: SList, env: Optional[Environment] = None) -> int:
        """(count COLL) - return length of collection."""
        if len(form) != 2:
            raise EvalError(f"'count' expects 1 argument, got {len(form) - 1}")
        coll = self.eval(form.items[1], env)

        if coll is None:
            return 0
        elif isinstance(coll, (list, tuple)):
            return len(coll)
        elif isinstance(coll, str):
            return len(coll)
        else:
            raise EvalError(f"'count' expects sequence, got {type(coll).__name__}")

    def _eval_cons(self, form: SList, env: Optional[Environment] = None) -> list:
        """(cons ELEM COLL) - prepend element to collection.

        Returns a new list with ELEM as first element.

        Examples:
            (cons 1 '(2 3)) => (1 2 3)
            (cons "a" '()) => ("a")
        """
        if len(form) != 3:
            raise EvalError(f"'cons' expects 2 arguments, got {len(form) - 1}")
        elem = self.eval(form.items[1], env)
        coll = self.eval(form.items[2], env)

        if coll is None:
            return [elem]
        elif isinstance(coll, (list, tuple)):
            return [elem] + list(coll)
        else:
            raise EvalError(f"'cons' expects sequence as second argument, got {type(coll).__name__}")

    # NOTE: empty? moved to builtins.grue

    def _eval_get_in(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(get-in TARGET KEYS [DEFAULT]) - traverse nested structure via keys.

        Navigates into nested maps/objects using a sequence of keys.
        Returns DEFAULT (or nil) if path not found.

        TARGET can be:
        - An object reference (@obj) - traverses properties
        - A dict/map - traverses keys
        - A list of key-value pairs

        KEYS is a list of keys to traverse (can be keywords or indices).

        Examples:
            (get-in @elevator '(:buttons :go 2)) => true
            (get-in {:a {:b 1}} '(:a :b)) => 1
            (get-in @obj '(:nested :prop) "default") => "default" if not found
        """
        if len(form) < 3 or len(form) > 4:
            raise EvalError(f"'get-in' expects 2-3 arguments, got {len(form) - 1}")

        target = self.eval(form.items[1], env)
        keys = self.eval(form.items[2], env)
        default = self.eval(form.items[3], env) if len(form) > 3 else None

        if not isinstance(keys, (list, tuple)):
            raise EvalError(f"'get-in' keys must be a list, got {type(keys).__name__}")

        current = target
        for key in keys:
            if current is None:
                return default
            current = self._get_in_step(current, key)

        return current if current is not None else default

    def _get_in_step(self, target: Any, key: Any) -> Any:
        """Single step of get-in traversal."""
        from .sexpr import Keyword

        # Extract key name from Keyword if needed
        key_name = key.name if isinstance(key, Keyword) else key

        # Handle object name (string starting with @) - look up property
        if isinstance(target, str) and target.startswith("@"):
            if isinstance(key_name, str):
                return self.state.get_object_property(target, key_name)
            return None

        # Handle dict
        if isinstance(target, dict):
            return target.get(key_name)

        # Handle list with keyword-value pairs or by index
        if isinstance(target, (list, tuple)):
            if isinstance(key_name, int):
                return target[key_name] if 0 <= key_name < len(target) else None
            # Try keyword-value lookup
            for i in range(0, len(target) - 1, 2):
                item_key = target[i]
                if isinstance(item_key, Keyword) and item_key.name == key_name:
                    return target[i + 1]
                elif item_key == key_name:
                    return target[i + 1]
            return None

        return None

    # === Higher-order collection functions ===

    def _eval_map(self, form: SList, env: Optional[Environment] = None) -> list:
        """(map FN COLL) - apply function to each element.

        Examples:
            (map (fn (?x) (* ?x 2)) '(1 2 3)) => (2 4 6)
            (map first '((a b) (c d))) => ("a" "c")
        """
        if len(form) != 3:
            raise EvalError(f"'map' expects 2 arguments, got {len(form) - 1}")

        fn = self.eval(form.items[1], env)
        coll = self.eval(form.items[2], env)

        if not isinstance(fn, GrueFn):
            raise EvalError(f"'map' first argument must be a function, got {type(fn).__name__}")
        if not isinstance(coll, (list, tuple)):
            raise EvalError(f"'map' second argument must be a sequence, got {type(coll).__name__}")

        return [self.call_fn(fn, [item]) for item in coll]

    def _eval_filter(self, form: SList, env: Optional[Environment] = None) -> list:
        """(filter PRED COLL) - keep elements matching predicate.

        Examples:
            (filter (fn (?x) (> ?x 0)) '(-1 0 1 2)) => (1 2)
            (filter identity '(nil 1 false 2)) => (1 2)
        """
        if len(form) != 3:
            raise EvalError(f"'filter' expects 2 arguments, got {len(form) - 1}")

        pred = self.eval(form.items[1], env)
        coll = self.eval(form.items[2], env)

        if not isinstance(pred, GrueFn):
            raise EvalError(f"'filter' first argument must be a function, got {type(pred).__name__}")
        if not isinstance(coll, (list, tuple)):
            raise EvalError(f"'filter' second argument must be a sequence, got {type(coll).__name__}")

        return [item for item in coll if self.call_fn(pred, [item])]

    def _eval_remove(self, form: SList, env: Optional[Environment] = None) -> list:
        """(remove PRED COLL) - remove elements matching predicate (opposite of filter).

        Examples:
            (remove (fn (?x) (> ?x 0)) '(-1 0 1 2)) => (-1 0)
            (remove nil? '(nil 1 nil 2)) => (1 2)
        """
        if len(form) != 3:
            raise EvalError(f"'remove' expects 2 arguments, got {len(form) - 1}")

        pred = self.eval(form.items[1], env)
        coll = self.eval(form.items[2], env)

        if not isinstance(pred, GrueFn):
            raise EvalError(f"'remove' first argument must be a function, got {type(pred).__name__}")
        if not isinstance(coll, (list, tuple)):
            raise EvalError(f"'remove' second argument must be a sequence, got {type(coll).__name__}")

        return [item for item in coll if not self.call_fn(pred, [item])]

    def _eval_keep(self, form: SList, env: Optional[Environment] = None) -> list:
        """(keep FN COLL) - like map but removes nil results.

        Examples:
            (keep (fn (?x) (if (> ?x 0) ?x nil)) '(-1 0 1 2)) => (1 2)
        """
        if len(form) != 3:
            raise EvalError(f"'keep' expects 2 arguments, got {len(form) - 1}")

        fn = self.eval(form.items[1], env)
        coll = self.eval(form.items[2], env)

        if not isinstance(fn, GrueFn):
            raise EvalError(f"'keep' first argument must be a function, got {type(fn).__name__}")
        if not isinstance(coll, (list, tuple)):
            raise EvalError(f"'keep' second argument must be a sequence, got {type(coll).__name__}")

        result = []
        for item in coll:
            val = self.call_fn(fn, [item])
            if val is not None:
                result.append(val)
        return result

    def _eval_reduce(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(reduce FN INIT COLL) - fold collection with accumulator.

        FN takes two arguments: (fn (?acc ?item) ...) and returns new accumulator.

        Examples:
            (reduce (fn (?acc ?x) (+ ?acc ?x)) 0 '(1 2 3)) => 6
            (reduce (fn (?acc ?x) (cons ?x ?acc)) '() '(1 2 3)) => (3 2 1)
        """
        if len(form) != 4:
            raise EvalError(f"'reduce' expects 3 arguments, got {len(form) - 1}")

        fn = self.eval(form.items[1], env)
        init = self.eval(form.items[2], env)
        coll = self.eval(form.items[3], env)

        if not isinstance(fn, GrueFn):
            raise EvalError(f"'reduce' first argument must be a function, got {type(fn).__name__}")
        if not isinstance(coll, (list, tuple)):
            raise EvalError(f"'reduce' third argument must be a sequence, got {type(coll).__name__}")

        acc = init
        for item in coll:
            acc = self.call_fn(fn, [acc, item])
        return acc

    def _eval_for(self, form: SList, env: Optional[Environment] = None) -> list:
        """(for (BINDING SEQ ...) BODY) - sequence comprehension.

        Returns a list of body evaluation results, one for each element.
        Supports multiple binding pairs that nest (like nested for loops).

        Examples:
            (for (?x '(1 2 3)) (* ?x 2)) => (2 4 6)
            (for (?x '(1 2) ?y '(a b)) (list ?x ?y))
              => ((1 a) (1 b) (2 a) (2 b))
        """
        if len(form) != 3:
            raise EvalError(f"'for' expects 2 arguments (bindings body), got {len(form) - 1}")

        bindings_expr = form[1]
        body = form[2]

        if not isinstance(bindings_expr, SList):
            raise EvalError(f"'for' bindings must be a list, got {bindings_expr}")

        # Parse binding pairs: (?var seq ?var2 seq2 ...)
        bindings_list = list(bindings_expr.items)
        if len(bindings_list) % 2 != 0:
            raise EvalError("'for' bindings must have even number of elements (var seq pairs)")
        if len(bindings_list) == 0:
            raise EvalError("'for' requires at least one binding pair")

        pairs = []
        for i in range(0, len(bindings_list), 2):
            var = bindings_list[i]
            seq_expr = bindings_list[i + 1]
            if not isinstance(var, Symbol):
                raise EvalError(f"'for' binding variable must be a symbol, got {var}")
            pairs.append((var.name, seq_expr))

        # Helper to iterate through nested bindings recursively
        def iterate(pairs_idx: int, current_env: Environment) -> list:
            if pairs_idx >= len(pairs):
                # All bindings set, evaluate body
                return [self.eval(body, current_env)]

            var_name, seq_expr = pairs[pairs_idx]
            seq = self.eval(seq_expr, current_env)
            if not isinstance(seq, (list, tuple)):
                raise EvalError(f"'for' sequence must be a list, got {type(seq).__name__}")

            result = []
            base_name = var_name[1:] if var_name.startswith("?") else var_name
            for item in seq:
                # Bind the variable
                new_bindings = {base_name: item, f"?{base_name}": item}
                new_env = current_env.extend(new_bindings)
                # Recurse to next binding or body
                result.extend(iterate(pairs_idx + 1, new_env))
            return result

        base_env = env if env is not None else Environment()
        return iterate(0, base_env)

    def _eval_doseq(self, form: SList, env: Optional[Environment] = None) -> None:
        """(doseq (BINDING SEQ ...) BODY) - iterate for side effects.

        Like for, but doesn't collect results. Returns nil.
        Useful when body has side effects like print.

        Examples:
            (doseq (?obj (contents @player)) (print (desc ?obj)))
        """
        if len(form) != 3:
            raise EvalError(f"'doseq' expects 2 arguments (bindings body), got {len(form) - 1}")

        bindings_expr = form[1]
        body = form[2]

        if not isinstance(bindings_expr, SList):
            raise EvalError(f"'doseq' bindings must be a list, got {bindings_expr}")

        # Parse binding pairs: (?var seq ?var2 seq2 ...)
        bindings_list = list(bindings_expr.items)
        if len(bindings_list) % 2 != 0:
            raise EvalError("'doseq' bindings must have even number of elements (var seq pairs)")
        if len(bindings_list) == 0:
            raise EvalError("'doseq' requires at least one binding pair")

        pairs = []
        for i in range(0, len(bindings_list), 2):
            var = bindings_list[i]
            seq_expr = bindings_list[i + 1]
            if not isinstance(var, Symbol):
                raise EvalError(f"'doseq' binding variable must be a symbol, got {var}")
            pairs.append((var.name, seq_expr))

        # Helper to iterate through nested bindings recursively
        def iterate(pairs_idx: int, current_env: Environment) -> None:
            if pairs_idx >= len(pairs):
                # All bindings set, evaluate body for side effects
                self.eval(body, current_env)
                return

            var_name, seq_expr = pairs[pairs_idx]
            seq = self.eval(seq_expr, current_env)
            if not isinstance(seq, (list, tuple)):
                raise EvalError(f"'doseq' sequence must be a list, got {type(seq).__name__}")

            base_name = var_name[1:] if var_name.startswith("?") else var_name
            for item in seq:
                # Bind the variable
                new_bindings = {base_name: item, f"?{base_name}": item}
                new_env = current_env.extend(new_bindings)
                # Recurse to next binding or body
                iterate(pairs_idx + 1, new_env)

        base_env = env if env is not None else Environment()
        iterate(0, base_env)
        return None

    # === Side effects - Controlled by allow_mutations flag ===
    #
    # In the Applicative Effect System, behaviors must be pure functions that
    # return effect lists. Direct mutation in behavior bodies is not allowed.
    #
    # However, functions called from EffectExecutor (during effect application)
    # ARE allowed to use mutations - that's the runtime applying effects.
    #
    # Instead of direct mutation in behaviors:
    #     :examine (fn () (move @key @player) (success :message "Got it!"))
    #
    # Return effect lists:
    #     :examine (fn () '((move @key @player) (success :message "Got it!")))
    #
    # The runtime interprets the effect list and applies mutations.

    def _eval_mutation_dispatch(self, form: SList, env: Optional[Environment] = None) -> None:
        """Dispatch mutation primitives - allowed if allow_mutations=True, error otherwise."""
        if not self._allow_mutations:
            effect_name = form[0].name if isinstance(form[0], Symbol) else str(form[0])
            raise EvalError(
                f"'{effect_name}' is not allowed in behavior bodies (behaviors must be pure). "
                f"Use the effect system instead: return a quoted list with ({effect_name} ...) "
                f"followed by a terminator like (success ...). "
                f"Example: '(({effect_name} ...) (success :message \"...\"))"
            )

        # Dispatch to the actual mutation handler
        effect_name = form[0].name if isinstance(form[0], Symbol) else str(form[0])
        handler = self._mutation_handlers.get(effect_name)
        if handler:
            return handler(form, env)
        else:
            raise EvalError(f"Unknown mutation: {effect_name}")

    def _init_mutation_handlers(self) -> dict[str, Callable[..., Any]]:
        """Initialize mutation handlers (used when allow_mutations=True)."""
        return {
            "move": self._eval_move_impl,
            "set": self._eval_set_impl,
            "inc": self._eval_inc_impl,
        }

    def _eval_move_impl(self, form: SList, env: Optional[Environment] = None) -> None:
        """(move OBJ DEST) - Move object to destination."""
        if len(form) != 3:
            raise EvalError(f"'move' expects 2 arguments, got {len(form) - 1}")
        obj = self.eval(form[1], env)
        if isinstance(obj, Symbol):
            obj = obj.name
        dest = self.eval(form[2], env)
        if isinstance(dest, Symbol):
            dest = dest.name
        if not hasattr(self.state, "move_object"):
            raise EvalError("'move' requires mutable state")
        self.state.move_object(obj, dest)
        return None

    def _eval_set_impl(self, form: SList, env: Optional[Environment] = None) -> None:
        """(set @obj :prop value) - Set an object property."""
        if len(form) != 4:
            raise EvalError(f"'set' expects 3 arguments: (set @obj :prop value), got {len(form) - 1}")
        obj = self.eval(form[1], env)
        if isinstance(obj, Symbol):
            obj = obj.name
        prop_arg = form[2]
        if isinstance(prop_arg, Keyword):
            prop = prop_arg.name
        elif isinstance(prop_arg, Symbol):
            prop = prop_arg.name
        else:
            prop = self.eval(prop_arg, env)
        value = self.eval(form[3], env)
        if not hasattr(self.state, "set_object_property"):
            raise EvalError("'set' requires mutable state")
        self.state.set_object_property(obj, prop, value)
        return None

    def _eval_inc_impl(self, form: SList, env: Optional[Environment] = None) -> None:
        """(inc @obj :prop) or (inc @obj :prop amount) - Increment an entity property."""
        if len(form) < 3 or len(form) > 4:
            raise EvalError(f"'inc' expects 2-3 arguments: (inc @obj :prop [amount]), got {len(form) - 1}")
        obj = self.eval(form[1], env)
        if isinstance(obj, Symbol):
            obj = obj.name
        prop_arg = form[2]
        if isinstance(prop_arg, Keyword):
            prop = prop_arg.name
        elif isinstance(prop_arg, Symbol):
            prop = prop_arg.name
        else:
            prop = self.eval(prop_arg, env)
        amount = 1
        if len(form) == 4:
            amount = self.eval(form[3], env)
        current = self.state.get_object_property(obj, prop) or 0
        self.state.set_object_property(obj, prop, current + amount)
        return None

    # === Quantifiers ===

    def _eval_some(self, form: SList, env: Optional[Environment] = None) -> Any:
        """(some PRED COLL) - returns first truthy result of (pred x), or nil.

        Examples:
            (some (fn (?x) (> ?x 5)) '(1 3 7 9))  ; => true (from 7)
            (some (fn (?x) (> ?x 10)) '(1 3 7 9)) ; => nil
        """
        if len(form) != 3:
            raise EvalError(f"'some' expects 2 arguments, got {len(form) - 1}")

        pred = self.eval(form.items[1], env)
        collection = self.eval(form.items[2], env)

        if not isinstance(pred, GrueFn):
            raise EvalError(f"'some' first argument must be a function, got {type(pred).__name__}")
        if not isinstance(collection, (list, tuple)):
            raise EvalError(f"'some' second argument must be a sequence, got {type(collection).__name__}")

        for item in collection:
            result = self.call_fn(pred, [item])
            if result:
                return result
        return None

    def _eval_every(self, form: SList, env: Optional[Environment] = None) -> bool:
        """(every? PRED COLL) - returns true if (pred x) is truthy for all x.

        Examples:
            (every? (fn (?x) (> ?x 0)) '(1 3 7 9))  ; => true
            (every? (fn (?x) (> ?x 5)) '(1 3 7 9))  ; => false
        """
        if len(form) != 3:
            raise EvalError(f"'every?' expects 2 arguments, got {len(form) - 1}")

        pred = self.eval(form.items[1], env)
        collection = self.eval(form.items[2], env)

        if not isinstance(pred, GrueFn):
            raise EvalError(f"'every?' first argument must be a function, got {type(pred).__name__}")
        if not isinstance(collection, (list, tuple)):
            raise EvalError(f"'every?' second argument must be a sequence, got {type(collection).__name__}")

        for item in collection:
            result = self.call_fn(pred, [item])
            if not result:
                return False
        return True

    def _eval_with_binding(self, name: str, value: Any, expr: SExpr, env: Optional[Environment] = None) -> Any:
        """Evaluate expression with a temporary variable binding."""
        # Create a new environment with the binding
        bindings = {name: value}
        # Strip ? for convenience (allow ?x to match x in lookup)
        if name.startswith("?"):
            bindings[name[1:]] = value
        else:
            bindings[f"?{name}"] = value
        new_env = (env or Environment()).extend(bindings)
        return self.eval(expr, new_env)


class EffectExecutor:
    """
    Execute effects (state mutations) against a world state.

    Supports user-defined functions via (defn name (params) body):
        executor.execute(parse("(defn at-lobby? () (= (loc PLAYER) LOBBY))"))
        evaluator.eval(parse("(at-lobby?)"))  # Uses shared function registry
    """

    def __init__(
        self,
        state: MutableWorldState,
        functions: dict[str, GrueFn] | None = None,
        include_builtins: bool = True
    ):
        self.state = state
        # Shared function registry between evaluator and executor
        # If functions dict provided, use it directly (allows sharing between instances)
        # Otherwise, create a new dict with built-in functions
        if functions is not None:
            self._functions = functions  # Use the provided dict (shared)
            # Add builtins to the shared dict if requested
            if include_builtins:
                builtins = _get_cached_builtin_functions()
                for name, fn in builtins.items():
                    if name not in self._functions:
                        self._functions[name] = fn
        elif include_builtins:
            self._functions = dict(_get_cached_builtin_functions())
        else:
            self._functions = {}
        self._predicates = ExprEvaluator(state, self._functions, allow_mutations=True)
        self._effects: dict[str, Callable[..., None]] = {
            "move": self._exec_move,
            "set": self._exec_set,  # (set @obj :prop value)
            "inc": self._exec_inc,
            "seq": self._exec_seq,
            "when": self._exec_when,
            "defn": self._exec_defn,
            "queue": self._exec_queue,
            "dequeue": self._exec_dequeue,
            "take": self._exec_take,
        }
        # Current environment for variable lookups (set by execute())
        self._env: Optional[Environment] = None

    def execute(self, expr: SExpr, env: Optional[Environment] = None) -> None:
        """Execute an effect expression.

        Args:
            expr: The effect expression to execute
            env: Optional lexical environment for resolving local variables
        """
        self._env = env  # Store for use by effect handlers
        try:
            if not isinstance(expr, SList):
                raise EvalError(f"Effect must be a list, got: {expr}")
            if len(expr) == 0:
                raise EvalError("Empty effect")

            head = expr[0]
            if not isinstance(head, Symbol):
                raise EvalError(f"Expected effect name, got: {head}")

            name = head.name
            if name in self._effects:
                self._effects[name](expr)
            elif name in self._functions:
                # Call user-defined function (for side effects)
                self._predicates.eval(expr, env)
            else:
                raise EvalError(f"Unknown effect: {name}")
        finally:
            self._env = None

    def _eval(self, expr: SExpr) -> Any:
        """Evaluate a value expression using the current environment."""
        return self._predicates.eval(expr, self._env)

    def _exec_move(self, form: SList) -> None:
        """(move OBJ DEST)

        When moving the player to a room, this also triggers the room's
        :on-enter behavior (if any), mirroring the behavior of "go" movement.
        """
        if len(form) != 3:
            raise EvalError(f"'move' expects 2 arguments, got {len(form) - 1}")
        obj = self._eval(form[1])
        dest = self._eval(form[2])

        # Track from_room if we're moving the player to a room
        # self.state may be a GrueRuntime (which has these methods) or a plain state
        player_name = getattr(self.state, "player_name", "@player")
        from_room = None
        is_room = getattr(self.state, "is_room", None)
        get_loc = getattr(self.state, "get_object_location", None)
        check_enter = getattr(self.state, "_check_room_on_enter", None)

        if obj == player_name and dest and is_room and get_loc and check_enter:
            if is_room(dest):
                from_room = get_loc(player_name)

        self.state.move_object(obj, dest)

        # Trigger on-enter if we moved the player to a room
        if from_room is not None and check_enter:
            check_enter(dest, from_room, player_name)

    def _exec_set(self, form: SList) -> None:
        """(set @obj :prop value) - Set an object property.

        Clojure-style property setter. Property must be a keyword.

        Examples:
            (set @microwave :timer 120)
            (set @food :heat 5)
        """
        if len(form) != 4:
            raise EvalError(f"'set' expects 3 arguments: (set @obj :prop value), got {len(form) - 1}")
        obj = self._eval(form[1])
        prop_arg = form[2]
        if not isinstance(prop_arg, Keyword):
            raise EvalError(f"'set' property must be a keyword, got: {prop_arg}")
        prop = prop_arg.name
        value = self._eval(form[3])
        self.state.set_object_property(obj, prop, value)

    def _exec_inc(self, form: SList) -> None:
        """(inc @obj :prop) or (inc @obj :prop amount)

        Increment an entity property. Property must be a keyword.
        """
        if len(form) < 3 or len(form) > 4:
            raise EvalError(f"'inc' expects 2-3 arguments: (inc @obj :prop [amount]), got {len(form) - 1}")

        obj = self._eval(form[1])
        prop_arg = form[2]
        if not isinstance(prop_arg, Keyword):
            raise EvalError(f"'inc' property must be a keyword, got: {prop_arg}")
        prop = prop_arg.name

        amount = 1
        if len(form) == 4:
            amount = self._eval(form[3])

        current = self.state.get_object_property(obj, prop)
        self.state.set_object_property(obj, prop, current + amount)

    def _exec_seq(self, form: SList) -> None:
        """(seq EFFECT ...)"""
        for effect in form.items[1:]:
            self.execute(effect)

    def _exec_when(self, form: SList) -> None:
        """(when COND EFFECT)"""
        if len(form) != 3:
            raise EvalError(f"'when' expects 2 arguments, got {len(form) - 1}")

        condition = form[1]
        effect = form[2]

        if self._eval(condition):
            self.execute(effect)

    def _exec_defn(self, form: SList) -> None:
        """
        (defn NAME (PARAMS) BODY)

        Define a user function that can be called in expressions.

        Example:
            (defn at-lobby? () (= (loc PLAYER) LOBBY))
            (defn door-open? (door) (not (has-flag door LOCKED)))
        """
        if len(form) != 4:
            raise EvalError(f"'defn' expects 3 arguments (name, params, body), got {len(form) - 1}")

        # Extract function name
        name_expr = form[1]
        if not isinstance(name_expr, Symbol):
            raise EvalError(f"'defn' name must be a symbol, got: {name_expr}")
        name = name_expr.name

        # Extract parameter list
        params_expr = form[2]
        if not isinstance(params_expr, SList):
            raise EvalError(f"'defn' params must be a list, got: {params_expr}")
        params: list[str] = []
        for p in params_expr.items:
            if not isinstance(p, Symbol):
                raise EvalError(f"'defn' parameter must be a symbol, got: {p}")
            # Strip leading ? if present (like in fn)
            param_name = p.name[1:] if p.name.startswith("?") else p.name
            params.append(param_name)

        # Body is kept as-is (not evaluated until called)
        body = form[3]

        # Register in shared function dictionary as GrueFn
        self._functions[name] = GrueFn(params=params, body=body)

    def _exec_queue(self, form: SList) -> None:
        """(queue EVENT) or (queue EVENT COUNTDOWN)

        Event name is implicitly quoted if it's a symbol.
        """
        if len(form) < 2 or len(form) > 3:
            raise EvalError(f"'queue' expects 1-2 arguments, got {len(form) - 1}")

        # Implicitly quote symbol event names
        event_arg = form[1]
        if isinstance(event_arg, Symbol):
            event = event_arg.name
        else:
            event = self._eval(event_arg)

        countdown = None
        if len(form) == 3:
            countdown = self._eval(form[2])

        self.state.queue_event(event, countdown)

    def _exec_dequeue(self, form: SList) -> None:
        """(dequeue EVENT)

        Event name is implicitly quoted if it's a symbol.
        """
        if len(form) != 2:
            raise EvalError(f"'dequeue' expects 1 argument, got {len(form) - 1}")

        # Implicitly quote symbol event names
        event_arg = form[1]
        if isinstance(event_arg, Symbol):
            event = event_arg.name
        else:
            event = self._eval(event_arg)

        self.state.dequeue_event(event)

    def _exec_take(self, form: SList) -> None:
        """(take OBJ) - Move object to player's inventory."""
        if len(form) != 2:
            raise EvalError(f"'take' expects 1 argument, got {len(form) - 1}")

        obj = self._eval(form[1])
        # Move to player - state is the runtime which has player_name
        player = getattr(self.state, "player_name", "@player")
        self.state.move_object(obj, player)


def get_builtin_functions() -> dict[str, GrueFn]:
    """Load the built-in functions from builtins.grue.

    These functions (held?, here?, in?, etc.) are defined in Grue
    and provide convenience predicates built on primitives.
    """
    from pathlib import Path
    from .sexpr import parse_all

    builtins_path = Path(__file__).parent / "builtins.grue"
    if not builtins_path.exists():
        return {}

    source = builtins_path.read_text()
    exprs = parse_all(source)

    functions: dict[str, GrueFn] = {}
    for expr in exprs:
        if isinstance(expr, SList) and len(expr) >= 4:
            head = expr[0]
            if isinstance(head, Symbol) and head.name == "defn":
                # Parse: (defn name (params) body)
                name = expr[1].name if isinstance(expr[1], Symbol) else str(expr[1])
                params_expr = expr[2]
                body = expr[3]

                # Extract param names (strip ? prefix)
                params = []
                if isinstance(params_expr, SList):
                    for p in params_expr:
                        if isinstance(p, Symbol):
                            pname = p.name
                            if pname.startswith("?"):
                                pname = pname[1:]
                            params.append(pname)

                functions[name] = GrueFn(params=params, body=body)

    return functions


# Cache built-in functions
_BUILTIN_FUNCTIONS: dict[str, GrueFn] | None = None


def _get_cached_builtin_functions() -> dict[str, GrueFn]:
    """Get cached built-in functions (lazy-loaded)."""
    global _BUILTIN_FUNCTIONS
    if _BUILTIN_FUNCTIONS is None:
        _BUILTIN_FUNCTIONS = get_builtin_functions()
    return _BUILTIN_FUNCTIONS


def eval_predicate(expr: str | SExpr, state: WorldState, include_builtins: bool = True) -> bool:
    """
    Convenience function to evaluate a predicate expression.

    Args:
        expr: S-expression string or parsed expression
        state: World state to evaluate against
        include_builtins: Whether to include built-in functions (default: True)

    Returns:
        Boolean result of predicate
    """
    if isinstance(expr, str):
        expr = parse(expr)
    functions = _get_cached_builtin_functions() if include_builtins else {}
    evaluator = ExprEvaluator(state, functions)
    result = evaluator.eval(expr)
    return bool(result)


def execute_effect(expr: str | SExpr, state: MutableWorldState) -> None:
    """
    Convenience function to execute an effect expression.

    Args:
        expr: S-expression string or parsed expression
        state: Mutable world state to modify
    """
    if isinstance(expr, str):
        expr = parse(expr)
    executor = EffectExecutor(state)
    executor.execute(expr)
