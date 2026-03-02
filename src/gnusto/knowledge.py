"""
Player knowledge graph for Gnusto.

Tracks what the player has encountered, observed, and learned during gameplay.
This is player-scoped knowledge — it represents what the player *should* know
based on their actions, not the omniscient world state. Staleness is a feature:
"Last seen in the throne room at turn 5" is exactly what a player would know.

Serves as foundation for:
- History/journal (gnusto-dae1)
- Auto-mapping (gnusto-8c77)
- Agent recall tools (context-efficient entity lookups)
"""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .render import ContentBlock, Speak, Reveal, Focus
from .state import GameState


@dataclass
class KNode:
    """An entity the player has encountered."""

    id: str                         # @lantern, @lair, @hacker
    kind: str                       # 'room' or 'entity'
    name: str                       # "Brass Lantern", "The Lair"
    description: str                # Full prose description
    first_seen: int                 # Turn number
    last_seen: int                  # Turn number
    observations: list[str] = field(default_factory=list)

    # Room-specific
    visit_count: int = 0            # Times entered (rooms only)

    # Entity-specific
    last_known_location: str | None = None  # Room or container ID


@dataclass
class KEdge:
    """A relationship the player has observed."""

    source: str                     # Node ID
    relation: str                   # 'exit', etc.
    target: str                     # Node ID
    detail: str                     # Direction label, containment desc, etc.
    turn: int                       # When first observed


@dataclass
class KEvent:
    """Something that happened during gameplay."""

    turn: int
    room: str                       # Room ID where it happened
    text: str                       # Human-readable summary
    entities: list[str] = field(default_factory=list)


class KnowledgeGraph:
    """Accumulated player knowledge about the game world."""

    def __init__(self) -> None:
        self.nodes: dict[str, KNode] = {}
        self.edges: list[KEdge] = []
        self.events: list[KEvent] = []
        self.turn_count: int = 0
        self._current_room: str | None = None  # For detecting room transitions

    # ── Population ──────────────────────────────────────────────

    def observe_turn(
        self,
        state: GameState,
        command: str | None,
        actions: list[str],
        results: list[str],
        blocks: Sequence[ContentBlock],
    ) -> None:
        """Record everything the player learned this turn.

        Called once per turn from GameSession.process_input().
        For initial game state (before any commands), pass command=None.
        """
        turn = self.turn_count

        # Always observe current room and visible entities
        self._observe_room(state, turn)
        self._observe_entities(state, turn)

        # Record the player's command as an event
        if command:
            entities = _extract_entity_ids(command)
            for a in actions:
                entities.extend(_extract_entity_ids(a))
            self.events.append(KEvent(
                turn=turn,
                room=state.room,
                text=command,
                entities=_unique(entities),
            ))

        # Record action results as events
        for action_str, result_str in zip(actions, results):
            if result_str and result_str != "Done.":
                entities = _extract_entity_ids(action_str)
                self.events.append(KEvent(
                    turn=turn,
                    room=state.room,
                    text=f"{action_str}: {result_str}",
                    entities=_unique(entities),
                ))

        # Extract knowledge from narrative blocks
        self._observe_blocks(blocks, turn, state.room)

        self.turn_count += 1

    def _observe_room(self, state: GameState, turn: int) -> None:
        """Create or update room node and exit edges."""
        room_id = state.room
        entered = (room_id != self._current_room)

        if room_id in self.nodes:
            node = self.nodes[room_id]
            node.last_seen = turn
            node.description = state.room_description
            if entered:
                node.visit_count += 1
        else:
            self.nodes[room_id] = KNode(
                id=room_id,
                kind='room',
                name=state.room_name,
                description=state.room_description,
                first_seen=turn,
                last_seen=turn,
                visit_count=1,
            )

        if entered:
            self._current_room = room_id

        # Record exit edges (idempotent — skip if already known)
        known_exits = {
            (e.source, e.target, e.detail)
            for e in self.edges if e.relation == 'exit'
        }
        for exit_info in state.exits:
            key = (room_id, exit_info.destination_id, exit_info.direction)
            if key not in known_exits:
                self.edges.append(KEdge(
                    source=room_id,
                    relation='exit',
                    target=exit_info.destination_id,
                    detail=exit_info.direction,
                    turn=turn,
                ))
                known_exits.add(key)

            # Also create a stub node for unseen destination rooms
            if exit_info.destination_id not in self.nodes:
                self.nodes[exit_info.destination_id] = KNode(
                    id=exit_info.destination_id,
                    kind='room',
                    name=exit_info.destination_name,
                    description='',  # Not yet visited
                    first_seen=turn,
                    last_seen=turn,
                    visit_count=0,  # Known but not visited
                )

    def _observe_entities(self, state: GameState, turn: int) -> None:
        """Create or update nodes for visible objects and inventory."""
        # Visible objects
        for obj in state.visible_objects:
            self._observe_entity(obj.id, obj.description, state.room, turn)
            for child in obj.contents:
                self._observe_entity(child.id, child.description, obj.id, turn)

        # Inventory
        for obj in state.inventory:
            self._observe_entity(obj.id, obj.description, '@player', turn)
            for child in obj.contents:
                self._observe_entity(child.id, child.description, obj.id, turn)

    def _observe_entity(
        self, entity_id: str, description: str, location: str, turn: int,
    ) -> None:
        """Create or update an entity node."""
        if entity_id in self.nodes:
            node = self.nodes[entity_id]
            node.last_seen = turn
            node.last_known_location = location
            if description and description != node.description:
                node.description = description
        else:
            self.nodes[entity_id] = KNode(
                id=entity_id,
                kind='entity',
                name=description,
                description=description,
                first_seen=turn,
                last_seen=turn,
                last_known_location=location,
            )

    def _observe_blocks(
        self, blocks: Sequence[ContentBlock], turn: int, room: str,
    ) -> None:
        """Extract knowledge from narrative content blocks."""
        for block in blocks:
            if isinstance(block, Speak):
                # Record dialogue on the speaker's node
                speaker = block.speaker
                if speaker and speaker in self.nodes:
                    manner = f" ({block.manner})" if block.manner else ""
                    self.nodes[speaker].observations.append(
                        f'Turn {turn}: said{manner} "{block.text}"'
                    )
                elif speaker:
                    # Speaker not yet in nodes — create stub
                    self.nodes[speaker] = KNode(
                        id=speaker,
                        kind='entity',
                        name=speaker,
                        description='',
                        first_seen=turn,
                        last_seen=turn,
                        observations=[f'Turn {turn}: said "{block.text}"'],
                    )

            elif isinstance(block, Reveal):
                if block.entity and block.entity in self.nodes:
                    self.nodes[block.entity].observations.append(
                        f"Turn {turn}: {block.text}"
                    )
                # Also record as event
                entities = _extract_entity_ids(block.text)
                if block.entity:
                    entities = _unique([block.entity] + entities)
                self.events.append(KEvent(
                    turn=turn, room=room,
                    text=f"[reveal] {block.text}",
                    entities=entities,
                ))

            elif isinstance(block, Focus):
                if block.entity and block.entity in self.nodes:
                    self.nodes[block.entity].observations.append(
                        f"Turn {turn}: {block.text}"
                    )
                # Also record as event
                entities = _extract_entity_ids(block.text)
                if block.entity:
                    entities = _unique([block.entity] + entities)
                self.events.append(KEvent(
                    turn=turn, room=room,
                    text=f"[focus] {block.text}",
                    entities=entities,
                ))

    # ── Queries ─────────────────────────────────────────────────

    def recall(self, entity_id: str) -> str:
        """What does the player know about an entity?"""
        node = self.nodes.get(entity_id)
        if not node:
            return f"You don't recall anything about {entity_id}."

        lines = [f"## {node.name} ({node.id})"]

        if node.description:
            lines.append(node.description)
            lines.append("")

        if node.kind == 'room':
            lines.append(f"Visited {node.visit_count} time(s).")
            if node.visit_count == 0:
                lines.append("(Known but not yet visited.)")
            lines.append(f"First seen: turn {node.first_seen}. Last seen: turn {node.last_seen}.")

            # Exits from this room
            exits = [e for e in self.edges if e.source == entity_id and e.relation == 'exit']
            if exits:
                exit_strs = [f"{e.detail} -> {self._node_name(e.target)}" for e in exits]
                lines.append(f"Known exits: {', '.join(exit_strs)}")
        else:
            loc = self._describe_location(node.last_known_location, node.last_seen)
            lines.append(f"Last seen: {loc}.")
            lines.append(f"First seen: turn {node.first_seen}.")

        # Observations
        if node.observations:
            lines.append("")
            lines.append("### What you know")
            for obs in node.observations:
                lines.append(f"- {obs}")

        # Related events
        related = [e for e in self.events if entity_id in e.entities]
        if related:
            lines.append("")
            lines.append("### Related events")
            for ev in related[-10:]:  # Last 10
                room_name = self._node_name(ev.room)
                lines.append(f"- Turn {ev.turn} ({room_name}): {ev.text}")

        return "\n".join(lines)

    def map_summary(self) -> str:
        """Summary of explored rooms and connections."""
        rooms = [n for n in self.nodes.values() if n.kind == 'room']
        if not rooms:
            return "You haven't explored anywhere yet."

        # Sort by first_seen (exploration order)
        rooms.sort(key=lambda r: r.first_seen)

        lines = ["## Explored Map"]
        for room in rooms:
            visited = f"visited {room.visit_count}x" if room.visit_count > 0 else "not yet visited"
            exits = [e for e in self.edges if e.source == room.id and e.relation == 'exit']
            if exits:
                exit_strs = [f"{e.detail} -> {self._node_name(e.target)}" for e in exits]
                lines.append(f"- **{room.name}** ({visited}) — {', '.join(exit_strs)}")
            else:
                lines.append(f"- **{room.name}** ({visited})")

        return "\n".join(lines)

    def entities_summary(self) -> str:
        """Summary of known entities (objects and characters)."""
        entities = [n for n in self.nodes.values() if n.kind == 'entity']
        if not entities:
            return "No entities encountered yet."

        # Sort by last_seen (most recent first)
        entities.sort(key=lambda e: e.last_seen, reverse=True)

        lines = ["## Known Entities"]
        for ent in entities:
            loc = self._describe_location(ent.last_known_location, ent.last_seen)
            note_count = f", {len(ent.observations)} notes" if ent.observations else ""
            lines.append(f"- **{ent.name}** ({ent.id}) — {loc}{note_count}")

        return "\n".join(lines)

    def history(
        self,
        entity_id: str | None = None,
        room_id: str | None = None,
        last_n: int = 20,
    ) -> str:
        """Chronological events, optionally filtered."""
        events = self.events

        if entity_id:
            events = [e for e in events if entity_id in e.entities]
        if room_id:
            events = [e for e in events if e.room == room_id]

        if not events:
            # Fall back to recall data so the agent always gets something
            if entity_id:
                return self.recall(entity_id)
            scope = room_id or "this game"
            return f"No events recorded for {scope}."

        # Take last N
        events = events[-last_n:]

        if room_id:
            title = f"## History: {self._node_name(room_id)}"
        elif entity_id:
            title = f"## History: {self._node_name(entity_id)}"
        else:
            title = "## Recent History"

        lines = [title]
        for ev in events:
            room_name = self._node_name(ev.room)
            lines.append(f"- Turn {ev.turn} ({room_name}): {ev.text}")

        return "\n".join(lines)

    def search(self, keyword: str) -> str:
        """Full-text search across knowledge."""
        keyword_lower = keyword.lower()
        results: list[str] = []

        # Search nodes
        for node in self.nodes.values():
            if (keyword_lower in node.name.lower()
                    or keyword_lower in node.description.lower()
                    or any(keyword_lower in obs.lower() for obs in node.observations)):
                loc = ""
                if node.kind == 'entity' and node.last_known_location:
                    loc = f" (last at {self._node_name(node.last_known_location)})"
                elif node.kind == 'room':
                    loc = f" (visited {node.visit_count}x)" if node.visit_count > 0 else " (not visited)"
                results.append(f"- **{node.name}** ({node.id}){loc}")

        # Search events
        matching_events = [e for e in self.events if keyword_lower in e.text.lower()]
        for ev in matching_events[-10:]:
            room_name = self._node_name(ev.room)
            results.append(f"- Turn {ev.turn} ({room_name}): {ev.text}")

        if not results:
            return f"No matches for '{keyword}'."

        return f"## Search: {keyword}\n" + "\n".join(results)

    # ── Helpers ──────────────────────────────────────────────────

    def _node_name(self, node_id: str) -> str:
        """Get human-readable name for a node ID."""
        if node_id == '@player':
            return 'your inventory'
        node = self.nodes.get(node_id)
        return node.name if node else node_id

    def _describe_location(self, location: str | None, turn: int) -> str:
        """Human-readable location description."""
        if not location:
            return "unknown location"
        if location == '@player':
            return f"in your inventory (turn {turn})"
        name = self._node_name(location)
        return f"{name} (turn {turn})"

    # ── Serialization ───────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for save files."""
        return {
            'turn_count': self.turn_count,
            'current_room': self._current_room,
            'nodes': {
                nid: {
                    'kind': n.kind,
                    'name': n.name,
                    'description': n.description,
                    'first_seen': n.first_seen,
                    'last_seen': n.last_seen,
                    'observations': n.observations,
                    'visit_count': n.visit_count,
                    'last_known_location': n.last_known_location,
                }
                for nid, n in self.nodes.items()
            },
            'edges': [
                {
                    'source': e.source,
                    'relation': e.relation,
                    'target': e.target,
                    'detail': e.detail,
                    'turn': e.turn,
                }
                for e in self.edges
            ],
            'events': [
                {
                    'turn': e.turn,
                    'room': e.room,
                    'text': e.text,
                    'entities': e.entities,
                }
                for e in self.events
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeGraph":
        """Deserialize from a dict."""
        kg = cls()
        kg.turn_count = data.get('turn_count', 0)
        kg._current_room = data.get('current_room')

        for nid, nd in data.get('nodes', {}).items():
            kg.nodes[nid] = KNode(
                id=nid,
                kind=nd['kind'],
                name=nd['name'],
                description=nd.get('description', ''),
                first_seen=nd['first_seen'],
                last_seen=nd['last_seen'],
                observations=nd.get('observations', []),
                visit_count=nd.get('visit_count', 0),
                last_known_location=nd.get('last_known_location'),
            )

        for ed in data.get('edges', []):
            kg.edges.append(KEdge(
                source=ed['source'],
                relation=ed['relation'],
                target=ed['target'],
                detail=ed['detail'],
                turn=ed['turn'],
            ))

        for ev in data.get('events', []):
            kg.events.append(KEvent(
                turn=ev['turn'],
                room=ev['room'],
                text=ev['text'],
                entities=ev.get('entities', []),
            ))

        return kg

    # ── File I/O ────────────────────────────────────────────────

    def save(self, game_name: str, slot: str = "default") -> Path:
        """Save knowledge graph as JSON alongside the game save."""
        from grue.save import get_save_dir
        save_dir = get_save_dir(game_name)
        safe_slot = "".join(c for c in slot if c.isalnum() or c in "-_") or "default"
        path = save_dir / f"{safe_slot}.knowledge.json"
        path.write_text(json.dumps(self.to_dict(), indent=2))
        return path

    @classmethod
    def load(cls, game_name: str, slot: str = "default") -> "KnowledgeGraph":
        """Load knowledge graph from JSON companion file. Returns empty graph if missing."""
        from grue.save import get_save_dir
        save_dir = get_save_dir(game_name)
        safe_slot = "".join(c for c in slot if c.isalnum() or c in "-_") or "default"
        path = save_dir / f"{safe_slot}.knowledge.json"
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        return cls.from_dict(data)


# ── Utility ─────────────────────────────────────────────────

def _extract_entity_ids(text: str) -> list[str]:
    """Extract @entity-id references from a string."""
    return re.findall(r'@[\w-]+', text)


def _unique(items: list[str]) -> list[str]:
    """Deduplicate while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
