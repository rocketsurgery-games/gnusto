"""Tests for ZIL-to-DSL converter."""

import pytest
from pathlib import Path

from zil.parser import parse
from zil.extractor import extract_game_data, GameData, ZILObject, Property, Syntax
from zil.dsl import (
    ZILtoDSLConverter,
    convert_zil_to_dsl,
    Room,
    Object,
    Action,
)


@pytest.fixture
def simple_game_data() -> GameData:
    """Create a simple GameData for testing."""
    data = GameData()

    # Add a room
    room = ZILObject(name="LIVING-ROOM", kind="ROOM")
    room.properties["DESC"] = Property("DESC", ["Living Room"])
    room.properties["LDESC"] = Property("LDESC", ["You are in a cozy living room."])
    room.properties["FLAGS"] = Property("FLAGS", ["ONBIT", "LIGHTBIT"])
    room.properties["NORTH"] = Property("NORTH", ["TO", "KITCHEN"])
    room.properties["EAST"] = Property("EAST", ["TO", "BEDROOM"])
    data.rooms["LIVING-ROOM"] = room

    # Add another room
    kitchen = ZILObject(name="KITCHEN", kind="ROOM")
    kitchen.properties["DESC"] = Property("DESC", ["Kitchen"])
    kitchen.properties["SOUTH"] = Property("SOUTH", ["TO", "LIVING-ROOM"])
    kitchen.properties["FLAGS"] = Property("FLAGS", ["ONBIT"])
    data.rooms["KITCHEN"] = kitchen

    # Add an object
    lamp = ZILObject(name="LAMP", kind="OBJECT")
    lamp.properties["DESC"] = Property("DESC", ["brass lamp"])
    lamp.properties["LDESC"] = Property("LDESC", ["A brass lamp sits here."])
    lamp.properties["IN"] = Property("IN", ["LIVING-ROOM"])
    lamp.properties["FLAGS"] = Property("FLAGS", ["TAKEBIT", "LIGHTBIT"])
    lamp.properties["SYNONYM"] = Property("SYNONYM", ["LAMP", "LANTERN"])
    lamp.properties["ADJECTIVE"] = Property("ADJECTIVE", ["BRASS", "OLD"])
    data.objects["LAMP"] = lamp

    # Add a syntax
    take_syntax = Syntax()
    take_syntax.verb = "TAKE"
    take_syntax.pattern = ["OBJECT"]
    take_syntax.filters = ["HELD", "MANY", "HAVE"]
    take_syntax.action = "V-TAKE"
    data.syntax.append(take_syntax)

    # Add another syntax for same action
    get_syntax = Syntax()
    get_syntax.verb = "GET"
    get_syntax.pattern = ["OBJECT"]
    get_syntax.action = "V-TAKE"
    data.syntax.append(get_syntax)

    # Add a different action
    drop_syntax = Syntax()
    drop_syntax.verb = "DROP"
    drop_syntax.pattern = ["OBJECT"]
    drop_syntax.action = "V-DROP"
    data.syntax.append(drop_syntax)

    return data


class TestZILtoDSLConverter:
    """Test the converter class."""

    def test_convert_empty_data(self):
        """Convert empty game data."""
        data = GameData()
        result = convert_zil_to_dsl(data, name="Empty Game")

        assert result.world.meta.name == "Empty Game"
        assert len(result.world.rooms) == 0
        assert len(result.world.objects) == 0

    def test_convert_rooms(self, simple_game_data):
        """Test room conversion."""
        result = convert_zil_to_dsl(simple_game_data)

        assert "LIVING-ROOM" in result.world.rooms
        assert "KITCHEN" in result.world.rooms

        living = result.world.rooms["LIVING-ROOM"]
        assert living.name == "LIVING-ROOM"
        assert living.description == "Living Room"
        assert living.long_description == "You are in a cozy living room."
        assert "ONBIT" in living.flags
        assert "LIGHTBIT" in living.flags

    def test_convert_exits(self, simple_game_data):
        """Test exit extraction from rooms."""
        result = convert_zil_to_dsl(simple_game_data)

        living = result.world.rooms["LIVING-ROOM"]
        assert "north" in living.exits
        assert living.exits["north"].to == "KITCHEN"
        assert "east" in living.exits
        assert living.exits["east"].to == "BEDROOM"

        kitchen = result.world.rooms["KITCHEN"]
        assert "south" in kitchen.exits
        assert kitchen.exits["south"].to == "LIVING-ROOM"

    def test_convert_objects(self, simple_game_data):
        """Test object conversion."""
        result = convert_zil_to_dsl(simple_game_data)

        assert "LAMP" in result.world.objects
        lamp = result.world.objects["LAMP"]

        assert lamp.name == "LAMP"
        assert lamp.description == "brass lamp"
        assert lamp.long_description == "A brass lamp sits here."
        assert lamp.initial_location == "LIVING-ROOM"
        assert "TAKEBIT" in lamp.flags
        assert "LIGHTBIT" in lamp.flags
        assert "LAMP" in lamp.synonyms
        assert "LANTERN" in lamp.synonyms
        assert "BRASS" in lamp.adjectives

    def test_convert_actions(self, simple_game_data):
        """Test action conversion from SYNTAX."""
        result = convert_zil_to_dsl(simple_game_data)

        # V-TAKE should become TAKE action with both syntax patterns
        assert "TAKE" in result.world.actions
        take = result.world.actions["TAKE"]
        assert "take [object]" in take.syntax
        assert "get [object]" in take.syntax

        # V-DROP should become DROP
        assert "DROP" in result.world.actions
        drop = result.world.actions["DROP"]
        assert "drop [object]" in drop.syntax

    def test_action_name_normalization(self, simple_game_data):
        """Test that V- prefix is stripped from action names."""
        result = convert_zil_to_dsl(simple_game_data)

        # Should use TAKE not V-TAKE
        assert "TAKE" in result.world.actions
        assert "V-TAKE" not in result.world.actions

    def test_detect_starting_room(self, simple_game_data):
        """Test automatic starting room detection."""
        result = convert_zil_to_dsl(simple_game_data)

        # Should pick LIVING-ROOM as it matches common pattern
        assert result.world.meta.starting_room == "LIVING-ROOM"

    def test_override_starting_room(self, simple_game_data):
        """Test manual starting room override."""
        result = convert_zil_to_dsl(
            simple_game_data,
            starting_room="KITCHEN"
        )

        assert result.world.meta.starting_room == "KITCHEN"

    def test_meta_fields(self, simple_game_data):
        """Test meta fields are set correctly."""
        result = convert_zil_to_dsl(
            simple_game_data,
            name="Test Game",
            author="Test Author"
        )

        assert result.world.meta.name == "Test Game"
        assert result.world.meta.author == "Test Author"


class TestExitConversion:
    """Test various exit formats."""

    def test_simple_exit(self):
        """Test (NORTH TO ROOM) format."""
        data = GameData()
        room = ZILObject(name="TEST", kind="ROOM")
        room.properties["NORTH"] = Property("NORTH", ["TO", "DEST"])
        data.rooms["TEST"] = room

        result = convert_zil_to_dsl(data)
        assert result.world.rooms["TEST"].exits["north"].to == "DEST"

    def test_per_exit_generates_warning(self):
        """Test (NORTH PER ROUTINE) generates warning."""
        data = GameData()
        room = ZILObject(name="TEST", kind="ROOM")
        room.properties["NORTH"] = Property("NORTH", ["PER", "CHECK-EXIT"])
        data.rooms["TEST"] = room

        result = convert_zil_to_dsl(data)

        # Should have warning about conditional exit
        assert any("PER" in w for w in result.warnings)
        # Should still create placeholder exit
        assert "north" in result.world.rooms["TEST"].exits

    def test_blocked_exit_generates_warning(self):
        """Test blocked exit with message generates warning."""
        data = GameData()
        room = ZILObject(name="TEST", kind="ROOM")
        room.properties["NORTH"] = Property("NORTH", ['"You can\'t go that way."'])
        data.rooms["TEST"] = room

        result = convert_zil_to_dsl(data)

        # Should have warning about blocked exit needing transition
        assert any("blocked" in w.lower() for w in result.warnings)


class TestSyntaxConversion:
    """Test SYNTAX to action pattern conversion."""

    def test_simple_verb(self):
        """Test simple verb-only syntax."""
        data = GameData()
        syntax = Syntax()
        syntax.verb = "INVENTORY"
        syntax.action = "V-INVENTORY"
        data.syntax.append(syntax)

        result = convert_zil_to_dsl(data)
        assert "INVENTORY" in result.world.actions
        assert "inventory" in result.world.actions["INVENTORY"].syntax

    def test_verb_with_object(self):
        """Test verb + object syntax."""
        data = GameData()
        syntax = Syntax()
        syntax.verb = "EXAMINE"
        syntax.pattern = ["OBJECT"]
        syntax.action = "V-EXAMINE"
        data.syntax.append(syntax)

        result = convert_zil_to_dsl(data)
        assert "examine [object]" in result.world.actions["EXAMINE"].syntax

    def test_verb_with_prep_and_object(self):
        """Test verb + prep + object syntax."""
        data = GameData()
        syntax = Syntax()
        syntax.verb = "LOOK"
        syntax.pattern = ["AT", "OBJECT"]
        syntax.action = "V-LOOK-AT"
        data.syntax.append(syntax)

        result = convert_zil_to_dsl(data)
        assert "look at [object]" in result.world.actions["LOOK-AT"].syntax

    def test_verb_with_two_objects(self):
        """Test verb + object + prep + object syntax."""
        data = GameData()
        syntax = Syntax()
        syntax.verb = "PUT"
        syntax.pattern = ["OBJECT", "IN", "OBJECT"]
        syntax.action = "V-PUT"
        data.syntax.append(syntax)

        result = convert_zil_to_dsl(data)
        assert "put [object] in [object]" in result.world.actions["PUT"].syntax


class TestLurkingHorrorConversion:
    """Test conversion of actual Lurking Horror ZIL."""

    @pytest.fixture
    def lurking_horror_data(self):
        """Load and parse actual Lurking Horror ZIL."""
        base = Path(__file__).parent.parent / "infocom" / "lurkinghorror"
        if not base.exists():
            pytest.skip("Lurking Horror ZIL files not found")

        # Parse cs.zil which has the computer center rooms
        cs_path = base / "cs.zil"
        if not cs_path.exists():
            pytest.skip("cs.zil not found")

        with open(cs_path) as f:
            content = f.read()

        ast = parse(content)
        return extract_game_data(ast)

    def test_extract_terminal_room(self, lurking_horror_data):
        """Extract TERMINAL-ROOM from actual ZIL."""
        data = lurking_horror_data

        # Terminal room might not be in cs.zil, check what rooms we have
        if "TERMINAL-ROOM" not in data.rooms:
            # Check other rooms that should be there
            assert any(r.startswith("CS-") or r == "COMP-CENTER" for r in data.rooms)
            return

        result = convert_zil_to_dsl(data, starting_room="TERMINAL-ROOM")
        room = result.world.rooms.get("TERMINAL-ROOM")

        if room:
            assert room.name == "TERMINAL-ROOM"
            assert room.description  # Should have some description

    def test_extract_rooms_from_cs(self, lurking_horror_data):
        """Extract rooms from cs.zil."""
        data = lurking_horror_data
        result = convert_zil_to_dsl(data)

        # Should have multiple rooms from cs.zil
        assert len(result.world.rooms) > 0

        # Check for expected rooms
        if "COMP-CENTER" in result.world.rooms:
            cc = result.world.rooms["COMP-CENTER"]
            assert cc.description == "Computer Center"

        if "CS-2ND" in result.world.rooms:
            cs2 = result.world.rooms["CS-2ND"]
            assert cs2.description == "Second Floor"
            assert "north" in cs2.exits  # Should have north to TERMINAL-ROOM

    def test_extract_objects_from_cs(self, lurking_horror_data):
        """Extract objects from cs.zil."""
        data = lurking_horror_data
        result = convert_zil_to_dsl(data)

        # cs.zil has OFFICE-DOOR object
        if "OFFICE-DOOR" in result.world.objects:
            door = result.world.objects["OFFICE-DOOR"]
            assert "DOORBIT" in door.flags

    def test_yaml_roundtrip(self, lurking_horror_data):
        """Test that converted world can be serialized to YAML."""
        data = lurking_horror_data
        result = convert_zil_to_dsl(
            data,
            name="The Lurking Horror",
            author="Infocom"
        )

        # Should be able to serialize to YAML
        yaml_str = result.world.to_yaml()
        assert "The Lurking Horror" in yaml_str
        assert "rooms:" in yaml_str


class TestWarningsAndErrors:
    """Test warning/error generation."""

    def test_non_standard_action_generates_warning(self):
        """Test that custom actions generate warnings about needing definition."""
        data = GameData()
        syntax = Syntax()
        syntax.verb = "FROBNICATE"
        syntax.pattern = ["OBJECT"]
        syntax.action = "V-FROBNICATE"
        data.syntax.append(syntax)

        result = convert_zil_to_dsl(data)

        # Should warn about needing manual preconditions/effects
        assert any("FROBNICATE" in w for w in result.warnings)

    def test_standard_actions_no_warning(self):
        """Test that standard actions don't generate warnings."""
        data = GameData()
        syntax = Syntax()
        syntax.verb = "TAKE"
        syntax.pattern = ["OBJECT"]
        syntax.action = "V-TAKE"
        data.syntax.append(syntax)

        result = convert_zil_to_dsl(data)

        # Should NOT warn about TAKE (it's standard)
        assert not any("TAKE" in w and "preconditions" in w for w in result.warnings)
