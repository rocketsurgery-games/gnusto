"""Tests for the player knowledge graph."""

from .knowledge import KnowledgeGraph, _extract_entity_ids
from .render import Narrate, Speak, Reveal, Focus
from .state import GameState, ObjectInfo, ExitInfo


def _make_state(
    room: str = "@office",
    room_name: str = "The Office",
    room_description: str = "A cluttered office.",
    visible_objects: list[ObjectInfo] | None = None,
    inventory: list[ObjectInfo] | None = None,
    exits: list[ExitInfo] | None = None,
) -> GameState:
    """Create a minimal GameState for testing."""
    return GameState(
        room=room,
        room_name=room_name,
        room_description=room_description,
        visible_objects=visible_objects or [],
        inventory=inventory or [],
        exits=exits or [],
    )


class TestObserveTurn:
    def test_initial_state_creates_room_node(self):
        kg = KnowledgeGraph()
        state = _make_state()
        kg.observe_turn(state, command=None, actions=[], results=[], blocks=[])

        assert "@office" in kg.nodes
        node = kg.nodes["@office"]
        assert node.kind == "room"
        assert node.name == "The Office"
        assert node.visit_count == 1
        assert kg.turn_count == 1

    def test_same_room_does_not_increment_visit(self):
        kg = KnowledgeGraph()
        state = _make_state()
        kg.observe_turn(state, command=None, actions=[], results=[], blocks=[])
        kg.observe_turn(state, command="look", actions=[], results=[], blocks=[])

        assert kg.nodes["@office"].visit_count == 1  # Same room, no re-entry
        assert kg.turn_count == 2

    def test_room_reentry_increments_visit(self):
        kg = KnowledgeGraph()
        office = _make_state()
        hallway = _make_state(room="@hallway", room_name="Hallway")
        kg.observe_turn(office, command=None, actions=[], results=[], blocks=[])
        kg.observe_turn(hallway, command="go north", actions=[], results=[], blocks=[])
        kg.observe_turn(office, command="go south", actions=[], results=[], blocks=[])

        assert kg.nodes["@office"].visit_count == 2
        assert kg.nodes["@hallway"].visit_count == 1

    def test_exit_edges_created(self):
        kg = KnowledgeGraph()
        state = _make_state(
            exits=[ExitInfo(direction="north", destination_id="@hallway", destination_name="Hallway")],
        )
        kg.observe_turn(state, command=None, actions=[], results=[], blocks=[])

        exit_edges = [e for e in kg.edges if e.relation == "exit"]
        assert len(exit_edges) == 1
        assert exit_edges[0].source == "@office"
        assert exit_edges[0].target == "@hallway"
        assert exit_edges[0].detail == "north"

    def test_exit_edges_idempotent(self):
        kg = KnowledgeGraph()
        state = _make_state(
            exits=[ExitInfo(direction="north", destination_id="@hallway", destination_name="Hallway")],
        )
        kg.observe_turn(state, command=None, actions=[], results=[], blocks=[])
        kg.observe_turn(state, command="look", actions=[], results=[], blocks=[])

        exit_edges = [e for e in kg.edges if e.relation == "exit"]
        assert len(exit_edges) == 1  # Not duplicated

    def test_unseen_destination_gets_stub_node(self):
        kg = KnowledgeGraph()
        state = _make_state(
            exits=[ExitInfo(direction="north", destination_id="@hallway", destination_name="Hallway")],
        )
        kg.observe_turn(state, command=None, actions=[], results=[], blocks=[])

        assert "@hallway" in kg.nodes
        assert kg.nodes["@hallway"].kind == "room"
        assert kg.nodes["@hallway"].visit_count == 0

    def test_visible_objects_observed(self):
        kg = KnowledgeGraph()
        state = _make_state(
            visible_objects=[ObjectInfo(id="@lantern", description="a brass lantern")],
        )
        kg.observe_turn(state, command=None, actions=[], results=[], blocks=[])

        assert "@lantern" in kg.nodes
        node = kg.nodes["@lantern"]
        assert node.kind == "entity"
        assert node.last_known_location == "@office"

    def test_inventory_tracked(self):
        kg = KnowledgeGraph()
        state = _make_state(
            inventory=[ObjectInfo(id="@key", description="a brass key")],
        )
        kg.observe_turn(state, command=None, actions=[], results=[], blocks=[])

        assert "@key" in kg.nodes
        assert kg.nodes["@key"].last_known_location == "@player"

    def test_command_creates_event(self):
        kg = KnowledgeGraph()
        state = _make_state()
        kg.observe_turn(state, command="look around", actions=[], results=[], blocks=[])

        assert len(kg.events) == 1
        assert kg.events[0].text == "look around"
        assert kg.events[0].room == "@office"

    def test_action_results_create_events(self):
        kg = KnowledgeGraph()
        state = _make_state()
        kg.observe_turn(
            state,
            command="take the key",
            actions=["take @key"],
            results=["Taken."],
            blocks=[],
        )

        # Command event + action result event (result is not "Done." so it gets recorded)
        result_events = [e for e in kg.events if "take @key" in e.text]
        assert len(result_events) == 1
        assert "@key" in result_events[0].entities

    def test_speak_blocks_add_observations(self):
        kg = KnowledgeGraph()
        state = _make_state(
            visible_objects=[ObjectInfo(id="@hacker", description="a scruffy hacker")],
        )
        blocks = [Speak(speaker="@hacker", text="The password is swordfish.", manner="whispering")]
        kg.observe_turn(state, command="talk to hacker", actions=[], results=[], blocks=blocks)

        assert "@hacker" in kg.nodes
        obs = kg.nodes["@hacker"].observations
        assert len(obs) == 1
        assert "swordfish" in obs[0]
        assert "whispering" in obs[0]

    def test_reveal_blocks_create_events(self):
        kg = KnowledgeGraph()
        state = _make_state(
            visible_objects=[ObjectInfo(id="@safe", description="a wall safe")],
        )
        blocks = [Reveal(text="Behind the painting, you notice a wall safe.", entity="@safe")]
        kg.observe_turn(state, command="look behind painting", actions=[], results=[], blocks=blocks)

        reveal_events = [e for e in kg.events if "[reveal]" in e.text]
        assert len(reveal_events) == 1
        assert "@safe" in reveal_events[0].entities
        # Also adds observation to entity node
        assert len(kg.nodes["@safe"].observations) == 1

    def test_focus_blocks_add_observations(self):
        kg = KnowledgeGraph()
        state = _make_state(
            visible_objects=[ObjectInfo(id="@lantern", description="a brass lantern")],
        )
        blocks = [Focus(text="The lantern has an inscription: FIAT LUX.", entity="@lantern")]
        kg.observe_turn(state, command="examine lantern", actions=[], results=[], blocks=blocks)

        assert "FIAT LUX" in kg.nodes["@lantern"].observations[0]


class TestQueries:
    def _build_explored_graph(self) -> KnowledgeGraph:
        """Build a small graph with a few rooms and entities."""
        kg = KnowledgeGraph()

        # Turn 0: Start in office with lantern
        state0 = _make_state(
            exits=[ExitInfo(direction="north", destination_id="@hallway", destination_name="Hallway")],
            visible_objects=[ObjectInfo(id="@lantern", description="a brass lantern")],
        )
        kg.observe_turn(state0, command=None, actions=[], results=[], blocks=[])

        # Turn 1: Pick up lantern
        state1 = _make_state(
            exits=[ExitInfo(direction="north", destination_id="@hallway", destination_name="Hallway")],
            inventory=[ObjectInfo(id="@lantern", description="a brass lantern")],
        )
        kg.observe_turn(
            state1, command="take the lantern",
            actions=["take @lantern"], results=["Taken."],
            blocks=[Narrate(text="You pick up the brass lantern.")],
        )

        # Turn 2: Move to hallway
        state2 = _make_state(
            room="@hallway", room_name="Hallway",
            room_description="A long dark hallway.",
            exits=[
                ExitInfo(direction="south", destination_id="@office", destination_name="The Office"),
                ExitInfo(direction="east", destination_id="@lab", destination_name="The Lab"),
            ],
            inventory=[ObjectInfo(id="@lantern", description="a brass lantern")],
        )
        kg.observe_turn(
            state2, command="go north",
            actions=["go north"], results=["Done."],
            blocks=[],
        )

        return kg

    def test_recall_room(self):
        kg = self._build_explored_graph()
        result = kg.recall("@office")

        assert "The Office" in result
        assert "visited" in result.lower()
        assert "north" in result

    def test_recall_entity(self):
        kg = self._build_explored_graph()
        result = kg.recall("@lantern")

        assert "brass lantern" in result
        assert "inventory" in result.lower()

    def test_recall_unknown(self):
        kg = self._build_explored_graph()
        result = kg.recall("@unknown")

        assert "don't recall" in result.lower()

    def test_entities_summary(self):
        kg = self._build_explored_graph()
        result = kg.entities_summary()

        assert "brass lantern" in result
        assert "@lantern" in result
        assert "inventory" in result.lower()

    def test_map_summary(self):
        kg = self._build_explored_graph()
        result = kg.map_summary()

        assert "The Office" in result
        assert "Hallway" in result
        assert "The Lab" in result  # Known but not visited
        assert "not yet visited" in result

    def test_history_all(self):
        kg = self._build_explored_graph()
        result = kg.history()

        assert "Recent History" in result
        assert "lantern" in result.lower()

    def test_history_by_room(self):
        kg = self._build_explored_graph()
        result = kg.history(room_id="@office")

        # Should only show events that happened in the office
        assert "office" in result.lower()

    def test_history_by_entity(self):
        kg = self._build_explored_graph()
        result = kg.history(entity_id="@lantern")

        assert "lantern" in result.lower()

    def test_search(self):
        kg = self._build_explored_graph()
        result = kg.search("lantern")

        assert "brass lantern" in result

    def test_search_no_match(self):
        kg = self._build_explored_graph()
        result = kg.search("xyzzy")

        assert "No matches" in result


class TestSerialization:
    def test_roundtrip(self):
        kg = KnowledgeGraph()
        state = _make_state(
            exits=[ExitInfo(direction="north", destination_id="@hallway", destination_name="Hallway")],
            visible_objects=[ObjectInfo(id="@lantern", description="a brass lantern")],
            inventory=[ObjectInfo(id="@key", description="a brass key")],
        )
        blocks = [Speak(speaker="@lantern", text="I glow!", manner=None)]
        kg.observe_turn(state, command="talk to lantern", actions=[], results=[], blocks=blocks)

        # Serialize and deserialize
        data = kg.to_dict()
        kg2 = KnowledgeGraph.from_dict(data)

        assert kg2.turn_count == kg.turn_count
        assert set(kg2.nodes.keys()) == set(kg.nodes.keys())
        assert len(kg2.edges) == len(kg.edges)
        assert len(kg2.events) == len(kg.events)

        # Verify node content preserved
        assert kg2.nodes["@lantern"].observations == kg.nodes["@lantern"].observations
        assert kg2.nodes["@key"].last_known_location == "@player"

        # Verify edge content preserved
        assert kg2.edges[0].source == "@office"
        assert kg2.edges[0].detail == "north"


class TestUtility:
    def test_extract_entity_ids(self):
        assert _extract_entity_ids("take @key") == ["@key"]
        assert _extract_entity_ids("give @key to @hacker") == ["@key", "@hacker"]
        assert _extract_entity_ids("look around") == []
        assert _extract_entity_ids("examine @brass-lantern") == ["@brass-lantern"]
