"""
Unified state model for abstract interpretation.

Replaces the ad-hoc StateRef variants (PropertyRef, LocationRef, QueueRef, HeldRef)
with a unified StatePath representation and builtin specifications.

Key concepts:
- StatePath: A string-based path into game state (e.g., "loc(@key)", "prop(@door,locked)")
- DomainConstraint: Represents constraints on value domains
- BuiltinSpec: Specification for runtime operations (go, take, drop)
- BuiltinFunc: Specification for runtime functions (loc, held?, in-room?)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable


# =============================================================================
# StatePath - Unified state reference
# =============================================================================


@dataclass(frozen=True)
class StatePath:
    """A path into game state.

    This is the unified replacement for PropertyRef, LocationRef, QueueRef, and HeldRef.
    Instead of separate classes, we use a single string-based representation that's
    hashable, comparable, and serializable.

    Examples:
        StatePath("loc(@key)")           # Object location
        StatePath("prop(@door,locked)")  # Object property
        StatePath("queue(hacker-helps)") # Event queue state
        StatePath("held(@key)")          # Abstract held predicate (for analysis)

    The path format is designed to be:
    - Human readable for debugging
    - Easily parseable for programmatic manipulation
    - Consistent with how we think about game state
    """

    path: str

    def __str__(self) -> str:
        return self.path

    def __repr__(self) -> str:
        return f"StatePath({self.path!r})"

    # Factory methods for creating paths

    @staticmethod
    def loc(obj: str) -> StatePath:
        """Create a location path: loc(@object)."""
        return StatePath(f"loc({obj})")

    @staticmethod
    def prop(obj: str, prop_name: str) -> StatePath:
        """Create a property path: prop(@object,property)."""
        return StatePath(f"prop({obj},{prop_name})")

    @staticmethod
    def queue(event: str) -> StatePath:
        """Create a queue path: queue(event-name)."""
        return StatePath(f"queue({event})")

    @staticmethod
    def held(obj: str) -> StatePath:
        """Create an abstract held predicate path: held(@object).

        This is used in analysis to abstract location to just "held vs not held".
        """
        return StatePath(f"held({obj})")

    # Parsing methods

    @property
    def kind(self) -> str:
        """Return the kind of state path: 'loc', 'prop', 'queue', or 'held'."""
        paren = self.path.find("(")
        if paren == -1:
            return "unknown"
        return self.path[:paren]

    @property
    def object(self) -> str | None:
        """Extract the object name from a loc, prop, or held path."""
        kind = self.kind
        if kind == "loc":
            # loc(@object)
            return self.path[4:-1]
        elif kind == "held":
            # held(@object)
            return self.path[5:-1]
        elif kind == "prop":
            # prop(@object,property)
            inner = self.path[5:-1]
            comma = inner.find(",")
            if comma != -1:
                return inner[:comma]
        return None

    @property
    def property_name(self) -> str | None:
        """Extract the property name from a prop path."""
        if self.kind != "prop":
            return None
        inner = self.path[5:-1]
        comma = inner.find(",")
        if comma != -1:
            return inner[comma + 1 :]
        return None

    @property
    def event_name(self) -> str | None:
        """Extract the event name from a queue path."""
        if self.kind != "queue":
            return None
        return self.path[6:-1]


# =============================================================================
# DomainConstraint - Value domain specifications
# =============================================================================


class DomainKind(Enum):
    """The kind of domain constraint."""

    ANY = auto()  # Any value (no constraint)
    ROOMS = auto()  # Set of room objects
    OBJECTS = auto()  # Set of all objects
    LOCATIONS = auto()  # rooms ∪ objects ∪ {nil} (anywhere something can be)
    BOOLEAN = auto()  # True or False
    FINITE = auto()  # Explicit finite set of values
    INTEGER = auto()  # Integer values (possibly bounded)


@dataclass(frozen=True)
class DomainConstraint:
    """Represents constraints on a value domain.

    Used to specify what values a runtime parameter can take or what
    values a function can return. This enables the analysis to reason
    about possible values without executing the code.

    Examples:
        DomainConstraint.rooms()      # Any room object
        DomainConstraint.boolean()    # True or False
        DomainConstraint.finite({1, 2, 3})  # One of these values
    """

    kind: DomainKind
    values: frozenset[Any] | None = None  # For FINITE domains
    min_val: int | None = None  # For INTEGER bounds
    max_val: int | None = None  # For INTEGER bounds

    @staticmethod
    def any() -> DomainConstraint:
        """Any value - no constraint."""
        return DomainConstraint(kind=DomainKind.ANY)

    @staticmethod
    def rooms() -> DomainConstraint:
        """Domain of room objects."""
        return DomainConstraint(kind=DomainKind.ROOMS)

    @staticmethod
    def objects() -> DomainConstraint:
        """Domain of all objects."""
        return DomainConstraint(kind=DomainKind.OBJECTS)

    @staticmethod
    def locations() -> DomainConstraint:
        """Domain of all locations (rooms ∪ objects ∪ {nil})."""
        return DomainConstraint(kind=DomainKind.LOCATIONS)

    @staticmethod
    def boolean() -> DomainConstraint:
        """Boolean domain: True or False."""
        return DomainConstraint(kind=DomainKind.BOOLEAN)

    @staticmethod
    def finite(values: set[Any]) -> DomainConstraint:
        """Explicit finite set of possible values."""
        return DomainConstraint(kind=DomainKind.FINITE, values=frozenset(values))

    @staticmethod
    def integer(min_val: int | None = None, max_val: int | None = None) -> DomainConstraint:
        """Integer values, optionally bounded."""
        return DomainConstraint(kind=DomainKind.INTEGER, min_val=min_val, max_val=max_val)


# =============================================================================
# BuiltinSpec - Runtime operation specifications
# =============================================================================


@dataclass
class BuiltinSpec:
    """Specification for a runtime operation (go, take, drop, etc.).

    Runtime operations are actions that the game engine handles directly,
    not through Grue code. This spec tells the analyzer what state they
    read and write, so we can include them in dataflow analysis.

    Attributes:
        name: The operation name (e.g., "runtime:go")
        params: Runtime-provided parameters with their domain constraints
        reads: Function that computes state paths read given params
        writes: Function that computes state paths written given params
        modifies_to: Optional function that returns possible target values for writes
    """

    name: str
    params: dict[str, DomainConstraint] = field(default_factory=dict)
    reads: Callable[..., set[StatePath]] = field(default=lambda: set())
    writes: Callable[..., set[StatePath]] = field(default=lambda: set())
    modifies_to: Callable[..., dict[StatePath, set[Any]]] | None = None


@dataclass
class BuiltinFunc:
    """Specification for a runtime function (loc, held?, in-room?, etc.).

    Runtime functions are pure functions provided by the game engine.
    This spec tells the analyzer what state they read and what their
    return domain is.

    Attributes:
        name: The function name (e.g., "loc")
        params: Expected parameters with their domain constraints
        returns: The domain of possible return values
        reads: Function that computes state paths read given params
    """

    name: str
    params: dict[str, DomainConstraint] = field(default_factory=dict)
    returns: DomainConstraint = field(default_factory=DomainConstraint.any)
    reads: Callable[..., set[StatePath]] = field(default=lambda: set())


# =============================================================================
# Builtin Registry
# =============================================================================


class BuiltinRegistry:
    """Registry of all builtin operations and functions.

    This is populated with the standard Grue runtime builtins. Games can
    extend this if they add custom runtime operations.
    """

    def __init__(self):
        self.operations: dict[str, BuiltinSpec] = {}
        self.functions: dict[str, BuiltinFunc] = {}

    def register_operation(self, spec: BuiltinSpec) -> None:
        """Register a runtime operation."""
        self.operations[spec.name] = spec

    def register_function(self, func: BuiltinFunc) -> None:
        """Register a runtime function."""
        self.functions[func.name] = func

    def get_operation(self, name: str) -> BuiltinSpec | None:
        """Get an operation spec by name."""
        return self.operations.get(name)

    def get_function(self, name: str) -> BuiltinFunc | None:
        """Get a function spec by name."""
        return self.functions.get(name)


def create_standard_builtins() -> BuiltinRegistry:
    """Create the standard Grue runtime builtins registry.

    This defines the state effects of all built-in runtime operations and
    the domains of all built-in runtime functions.
    """
    registry = BuiltinRegistry()

    # === Runtime Operations ===

    # runtime:go - Player navigation
    # Reads: barrier's :through behavior reads (if :via is specified)
    # Writes: player location
    registry.register_operation(
        BuiltinSpec(
            name="runtime:go",
            params={
                "?from": DomainConstraint.rooms(),
                "?to": DomainConstraint.rooms(),
                "?via": DomainConstraint.objects(),  # Optional barrier
            },
            reads=lambda: set(),  # Barrier reads are analyzed from :through behavior
            writes=lambda player="@player": {StatePath.loc(player)},
            modifies_to=lambda to: {StatePath.loc("@player"): {to}},
        )
    )

    # runtime:take - Default take behavior for takeable objects
    # Writes: object location (to @player)
    registry.register_operation(
        BuiltinSpec(
            name="runtime:take",
            params={
                "?obj": DomainConstraint.objects(),
            },
            reads=lambda: set(),
            writes=lambda obj: {StatePath.loc(obj)},
            modifies_to=lambda obj: {StatePath.loc(obj): {"@player"}},
        )
    )

    # runtime:drop - Default drop behavior
    # Writes: object location (to current room - variable)
    registry.register_operation(
        BuiltinSpec(
            name="runtime:drop",
            params={
                "?obj": DomainConstraint.objects(),
                "?room": DomainConstraint.rooms(),  # Current room (variable)
            },
            reads=lambda: set(),
            writes=lambda obj: {StatePath.loc(obj)},
            modifies_to=lambda obj, room: {StatePath.loc(obj): {room}},
        )
    )

    # === Runtime Functions ===

    # loc - Get object location
    registry.register_function(
        BuiltinFunc(
            name="loc",
            params={"obj": DomainConstraint.objects()},
            returns=DomainConstraint.locations(),
            reads=lambda obj: {StatePath.loc(obj)},
        )
    )

    # held? - Check if object is held by player
    registry.register_function(
        BuiltinFunc(
            name="held?",
            params={"obj": DomainConstraint.objects()},
            returns=DomainConstraint.boolean(),
            reads=lambda obj: {StatePath.loc(obj)},
        )
    )

    # in-room? - Check if object is in specific room(s)
    registry.register_function(
        BuiltinFunc(
            name="in-room?",
            params={
                "obj": DomainConstraint.objects(),
                "rooms": DomainConstraint.rooms(),  # Variadic
            },
            returns=DomainConstraint.boolean(),
            reads=lambda obj: {StatePath.loc(obj)},
        )
    )

    # queued? - Check if event is queued
    registry.register_function(
        BuiltinFunc(
            name="queued?",
            params={"event": DomainConstraint.any()},  # Event name
            returns=DomainConstraint.boolean(),
            reads=lambda event: {StatePath.queue(event)},
        )
    )

    return registry


# =============================================================================
# Conversion utilities (for gradual migration)
# =============================================================================


def state_ref_to_path(ref: Any) -> StatePath:
    """Convert an old-style StateRef to a StatePath.

    This is a migration helper that allows gradual transition from the
    old PropertyRef/LocationRef/QueueRef/HeldRef classes to StatePath.
    """
    # Import here to avoid circular dependency during transition
    from frotz.effects import PropertyRef, LocationRef, QueueRef, HeldRef

    if isinstance(ref, PropertyRef):
        return StatePath.prop(ref.object, ref.property)
    elif isinstance(ref, LocationRef):
        return StatePath.loc(ref.object)
    elif isinstance(ref, QueueRef):
        return StatePath.queue(ref.event)
    elif isinstance(ref, HeldRef):
        return StatePath.held(ref.object)
    elif isinstance(ref, StatePath):
        return ref
    else:
        raise TypeError(f"Unknown state ref type: {type(ref)}")


def path_to_state_ref(path: StatePath) -> Any:
    """Convert a StatePath back to an old-style StateRef.

    This is a migration helper for backward compatibility.
    """
    from frotz.effects import PropertyRef, LocationRef, QueueRef, HeldRef

    kind = path.kind
    if kind == "loc":
        return LocationRef(path.object)
    elif kind == "prop":
        return PropertyRef(path.object, path.property_name)
    elif kind == "queue":
        return QueueRef(path.event_name)
    elif kind == "held":
        return HeldRef(path.object)
    else:
        raise ValueError(f"Unknown path kind: {kind}")
