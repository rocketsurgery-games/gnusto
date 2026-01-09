"""
World definition dataclasses and YAML parser.

This module defines the structure for declarative world definitions
and provides YAML parsing/serialization.
"""

from dataclasses import dataclass, field
from typing import Any
import yaml

from .sexpr import parse, SExpr, to_string, Symbol


@dataclass
class Exit:
    """An exit from a room."""
    to: str  # Destination room name
    when: SExpr | None = None  # Optional condition (S-expression)

    def to_dict(self) -> dict:
        result = {"to": self.to}
        if self.when is not None:
            result["when"] = to_string(self.when)
        return result


@dataclass
class Room:
    """A room definition."""
    name: str
    description: str = ""
    long_description: str | None = None
    exits: dict[str, Exit] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        result: dict[str, Any] = {}
        if self.description:
            result["description"] = self.description
        if self.long_description:
            result["long_description"] = self.long_description
        if self.exits:
            result["exits"] = {}
            for direction, exit in self.exits.items():
                if exit.when is None:
                    result["exits"][direction] = exit.to
                else:
                    result["exits"][direction] = exit.to_dict()
        if self.properties:
            result["properties"] = self.properties
        if self.flags:
            result["flags"] = self.flags
        return result


@dataclass
class BehaviorCase:
    """A single case in a behavior's case list."""
    when: SExpr  # Condition (required) - use Symbol("true") for default
    do: SExpr | None = None  # Effects to execute (optional)
    message: str | None = None  # Message to display (optional)
    handled: bool = True  # Stop processing? Default true

    def to_dict(self) -> dict:
        result: dict[str, Any] = {}
        # Handle 'true' as default marker
        if isinstance(self.when, Symbol) and self.when.name == "true":
            pass  # Don't emit when: true for default case
        else:
            result["when"] = to_string(self.when)
        if self.do is not None:
            result["do"] = to_string(self.do)
        if self.message is not None:
            result["message"] = self.message
        if not self.handled:
            result["handled"] = False
        return result


@dataclass
class Behavior:
    """A behavior definition for a specific verb on an object."""
    verb: str  # The verb this handles (e.g., "open", "take")
    cases: list[BehaviorCase] = field(default_factory=list)

    def to_dict(self) -> dict:
        if len(self.cases) == 1 and isinstance(self.cases[0].when, Symbol) and self.cases[0].when.name == "true":
            # Single default case - emit compact form
            case = self.cases[0]
            result: dict[str, Any] = {}
            if case.do is not None:
                result["do"] = to_string(case.do)
            if case.message is not None:
                result["message"] = case.message
            if not case.handled:
                result["handled"] = False
            return result
        else:
            # Multiple cases
            return {"cases": [c.to_dict() for c in self.cases]}


@dataclass
class Object:
    """An object definition."""
    name: str
    description: str = ""
    long_description: str | None = None
    initial_location: str | None = None
    flags: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    synonyms: list[str] = field(default_factory=list)
    adjectives: list[str] = field(default_factory=list)
    behaviors: dict[str, Behavior] = field(default_factory=dict)
    # ZIL source for manual translation reference
    zil_source: str | None = None

    def to_dict(self) -> dict:
        result: dict[str, Any] = {}
        if self.description:
            result["description"] = self.description
        if self.long_description:
            result["long_description"] = self.long_description
        if self.initial_location:
            result["initial_location"] = self.initial_location
        if self.flags:
            result["flags"] = self.flags
        if self.properties:
            result["properties"] = self.properties
        if self.synonyms:
            result["synonyms"] = self.synonyms
        if self.adjectives:
            result["adjectives"] = self.adjectives
        if self.behaviors:
            result["behaviors"] = {v: b.to_dict() for v, b in self.behaviors.items()}
        if self.zil_source:
            result["zil_source"] = self.zil_source
        return result


@dataclass
class ActionMessages:
    """Messages for action outcomes."""
    success: str = ""
    failure: str = ""
    # Additional custom messages
    custom: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        result: dict[str, str] = {}
        if self.success:
            result["success"] = self.success
        if self.failure:
            result["failure"] = self.failure
        result.update(self.custom)
        return result


@dataclass
class Action:
    """An action definition."""
    name: str
    syntax: list[str] = field(default_factory=list)
    preconditions: list[SExpr] = field(default_factory=list)
    effects: list[SExpr] = field(default_factory=list)
    messages: ActionMessages = field(default_factory=ActionMessages)
    determinism: str = "strict"  # "strict" or "flexible"

    def to_dict(self) -> dict:
        result: dict[str, Any] = {}
        if self.syntax:
            result["syntax"] = self.syntax
        if self.preconditions:
            result["preconditions"] = [to_string(p) for p in self.preconditions]
        if self.effects:
            result["effects"] = [to_string(e) for e in self.effects]
        if self.messages.success or self.messages.failure or self.messages.custom:
            result["messages"] = self.messages.to_dict()
        if self.determinism != "strict":
            result["determinism"] = self.determinism
        return result


@dataclass
class Transition:
    """A state transition triggered by specific actions."""
    name: str
    trigger: dict[str, str] = field(default_factory=dict)  # action, object, etc.
    when: SExpr | None = None
    effects: list[SExpr] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict:
        result: dict[str, Any] = {}
        if self.trigger:
            result["trigger"] = self.trigger
        if self.when is not None:
            result["when"] = to_string(self.when)
        if self.effects:
            result["effects"] = [to_string(e) for e in self.effects]
        if self.message:
            result["message"] = self.message
        return result


@dataclass
class Invariant:
    """A game invariant that must always hold."""
    name: str
    check: SExpr
    on_violation: str | None = None  # Action to take on violation

    def to_dict(self) -> dict:
        result: dict[str, Any] = {"check": to_string(self.check)}
        if self.on_violation:
            result["on_violation"] = self.on_violation
        return result


@dataclass
class WinCondition:
    """Victory condition."""
    when: SExpr
    message: str = ""

    def to_dict(self) -> dict:
        result: dict[str, Any] = {"when": to_string(self.when)}
        if self.message:
            result["message"] = self.message
        return result


@dataclass
class LoseCondition:
    """Defeat condition."""
    name: str
    when: SExpr
    message: str = ""

    def to_dict(self) -> dict:
        result: dict[str, Any] = {"when": to_string(self.when)}
        if self.message:
            result["message"] = self.message
        return result


@dataclass
class GameMeta:
    """Game metadata."""
    name: str = ""
    author: str = ""
    version: str = "1.0"
    description: str = ""
    starting_room: str = ""

    def to_dict(self) -> dict:
        result: dict[str, Any] = {}
        if self.name:
            result["name"] = self.name
        if self.author:
            result["author"] = self.author
        if self.version != "1.0":
            result["version"] = self.version
        if self.description:
            result["description"] = self.description
        if self.starting_room:
            result["starting_room"] = self.starting_room
        return result


@dataclass
class WorldDefinition:
    """
    Complete world definition.

    This is the top-level container for all game data.
    """
    meta: GameMeta = field(default_factory=GameMeta)
    rooms: dict[str, Room] = field(default_factory=dict)
    objects: dict[str, Object] = field(default_factory=dict)
    actions: dict[str, Action] = field(default_factory=dict)
    transitions: dict[str, Transition] = field(default_factory=dict)
    invariants: dict[str, Invariant] = field(default_factory=dict)
    victory: WinCondition | None = None
    defeat: dict[str, LoseCondition] = field(default_factory=dict)
    globals: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        result: dict[str, Any] = {}

        if self.meta.name or self.meta.author:
            result["meta"] = self.meta.to_dict()

        if self.globals:
            result["globals"] = self.globals

        if self.rooms:
            result["rooms"] = {name: room.to_dict() for name, room in self.rooms.items()}

        if self.objects:
            result["objects"] = {name: obj.to_dict() for name, obj in self.objects.items()}

        if self.actions:
            result["actions"] = {name: action.to_dict() for name, action in self.actions.items()}

        if self.transitions:
            result["transitions"] = {name: t.to_dict() for name, t in self.transitions.items()}

        if self.invariants:
            result["invariants"] = {}
            for name, inv in self.invariants.items():
                if inv.on_violation:
                    result["invariants"][name] = inv.to_dict()
                else:
                    result["invariants"][name] = to_string(inv.check)

        if self.victory:
            result["victory"] = self.victory.to_dict()

        if self.defeat:
            result["defeat"] = {name: cond.to_dict() for name, cond in self.defeat.items()}

        return result

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        return yaml.dump(
            self.to_dict(),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        )


class WorldParser:
    """Parse YAML world definitions into WorldDefinition objects."""

    def parse(self, yaml_content: str) -> WorldDefinition:
        """Parse YAML content into a WorldDefinition."""
        data = yaml.safe_load(yaml_content)
        if data is None:
            return WorldDefinition()
        return self._parse_world(data)

    def parse_file(self, path: str) -> WorldDefinition:
        """Parse a YAML file into a WorldDefinition."""
        with open(path, "r") as f:
            return self.parse(f.read())

    def _parse_world(self, data: dict) -> WorldDefinition:
        """Parse the top-level world structure."""
        world = WorldDefinition()

        if "meta" in data:
            world.meta = self._parse_meta(data["meta"])

        if "globals" in data:
            world.globals = data["globals"]

        if "rooms" in data:
            for name, room_data in data["rooms"].items():
                world.rooms[name] = self._parse_room(name, room_data)

        if "objects" in data:
            for name, obj_data in data["objects"].items():
                world.objects[name] = self._parse_object(name, obj_data)

        if "actions" in data:
            for name, action_data in data["actions"].items():
                world.actions[name] = self._parse_action(name, action_data)

        if "transitions" in data:
            for name, trans_data in data["transitions"].items():
                world.transitions[name] = self._parse_transition(name, trans_data)

        if "invariants" in data:
            for name, inv_data in data["invariants"].items():
                world.invariants[name] = self._parse_invariant(name, inv_data)

        if "victory" in data:
            world.victory = self._parse_victory(data["victory"])

        if "defeat" in data:
            for name, lose_data in data["defeat"].items():
                world.defeat[name] = self._parse_defeat(name, lose_data)

        return world

    def _parse_meta(self, data: dict) -> GameMeta:
        return GameMeta(
            name=data.get("name", ""),
            author=data.get("author", ""),
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            starting_room=data.get("starting_room", ""),
        )

    def _parse_room(self, name: str, data: dict) -> Room:
        room = Room(name=name)
        room.description = data.get("description", "")
        room.long_description = data.get("long_description")
        room.properties = data.get("properties", {})
        room.flags = data.get("flags", [])

        if "exits" in data:
            for direction, exit_data in data["exits"].items():
                if isinstance(exit_data, str):
                    room.exits[direction] = Exit(to=exit_data)
                else:
                    room.exits[direction] = Exit(
                        to=exit_data["to"],
                        when=parse(exit_data["when"]) if "when" in exit_data else None,
                    )

        return room

    def _parse_object(self, name: str, data: dict) -> Object:
        obj = Object(
            name=name,
            description=data.get("description", ""),
            long_description=data.get("long_description"),
            initial_location=data.get("initial_location"),
            flags=data.get("flags", []),
            properties=data.get("properties", {}),
            synonyms=data.get("synonyms", []),
            adjectives=data.get("adjectives", []),
            zil_source=data.get("zil_source"),
        )

        if "behaviors" in data:
            for verb, behavior_data in data["behaviors"].items():
                obj.behaviors[verb] = self._parse_behavior(verb, behavior_data)

        return obj

    def _parse_behavior(self, verb: str, data: dict) -> Behavior:
        """Parse a behavior definition."""
        behavior = Behavior(verb=verb)

        if "cases" in data:
            # Multiple cases form
            for case_data in data["cases"]:
                behavior.cases.append(self._parse_behavior_case(case_data))
        else:
            # Single/default case form (no 'cases' key)
            # The data itself is the case
            behavior.cases.append(self._parse_behavior_case(data, is_default=True))

        return behavior

    def _parse_behavior_case(self, data: dict, is_default: bool = False) -> BehaviorCase:
        """Parse a single behavior case."""
        if is_default and "when" not in data:
            when = Symbol("true")
        elif "when" not in data:
            when = Symbol("true")
        else:
            when_val = data["when"]
            # Handle YAML parsing "true" as boolean
            if when_val is True or (isinstance(when_val, str) and when_val.lower() == "true"):
                when = Symbol("true")
            else:
                when = parse(when_val)

        do_val = data.get("do")
        do_expr = parse(do_val) if do_val else None

        return BehaviorCase(
            when=when,
            do=do_expr,
            message=data.get("message"),
            handled=data.get("handled", True),
        )

    def _parse_action(self, name: str, data: dict) -> Action:
        action = Action(name=name)
        action.syntax = data.get("syntax", [])
        action.determinism = data.get("determinism", "strict")

        if "preconditions" in data:
            action.preconditions = [parse(p) for p in data["preconditions"]]

        if "effects" in data:
            action.effects = [parse(e) for e in data["effects"]]

        if "messages" in data:
            msg_data = data["messages"]
            action.messages = ActionMessages(
                success=msg_data.get("success", ""),
                failure=msg_data.get("failure", ""),
                custom={k: v for k, v in msg_data.items() if k not in ("success", "failure")},
            )

        return action

    def _parse_transition(self, name: str, data: dict) -> Transition:
        return Transition(
            name=name,
            trigger=data.get("trigger", {}),
            when=parse(data["when"]) if "when" in data else None,
            effects=[parse(e) for e in data.get("effects", [])],
            message=data.get("message", ""),
        )

    def _parse_invariant(self, name: str, data) -> Invariant:
        if isinstance(data, str):
            # Simple form: just the check expression
            return Invariant(name=name, check=parse(data))
        else:
            # Full form with on_violation
            return Invariant(
                name=name,
                check=parse(data["check"]),
                on_violation=data.get("on_violation"),
            )

    def _parse_victory(self, data: dict) -> WinCondition:
        return WinCondition(
            when=parse(data["when"]),
            message=data.get("message", ""),
        )

    def _parse_defeat(self, name: str, data: dict) -> LoseCondition:
        return LoseCondition(
            name=name,
            when=parse(data["when"]),
            message=data.get("message", ""),
        )


def load_world(path: str) -> WorldDefinition:
    """Load a world definition from a YAML file."""
    parser = WorldParser()
    return parser.parse_file(path)


def parse_world(yaml_content: str) -> WorldDefinition:
    """Parse a world definition from YAML content."""
    parser = WorldParser()
    return parser.parse(yaml_content)
