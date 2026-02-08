"""Tests for ZIL extractor."""

import pytest
from zil import parse, extract_game_data, ZILObject, Routine, Syntax


class TestObjectExtraction:
    """Test extracting OBJECT definitions."""

    def test_simple_object(self):
        ast = parse('<OBJECT LAMP (IN PLAYER) (DESC "A brass lamp")>')
        data = extract_game_data(ast)
        assert "LAMP" in data.objects
        obj = data.objects["LAMP"]
        assert obj.name == "LAMP"
        assert obj.kind == "OBJECT"

    def test_object_properties(self):
        ast = parse('''<OBJECT KEY
            (IN KITCHEN)
            (DESC "A rusty key")
            (SYNONYM KEY KEYS)
            (FLAGS TAKEBIT)>''')
        data = extract_game_data(ast)
        obj = data.objects["KEY"]
        assert obj.get_property_value("IN") == "KITCHEN"
        assert obj.get_property_value("DESC") == "A rusty key"
        assert obj.get_property_values("FLAGS") == ["TAKEBIT"]

    def test_object_with_multiple_flags(self):
        ast = parse('<OBJECT BOX (FLAGS TAKEBIT CONTBIT OPENABLE)>')
        data = extract_game_data(ast)
        flags = data.objects["BOX"].get_property_values("FLAGS")
        assert flags == ["TAKEBIT", "CONTBIT", "OPENABLE"]


class TestRoomExtraction:
    """Test extracting ROOM definitions."""

    def test_simple_room(self):
        ast = parse('<ROOM KITCHEN (IN ROOMS)>')
        data = extract_game_data(ast)
        assert "KITCHEN" in data.rooms
        assert data.rooms["KITCHEN"].kind == "ROOM"

    def test_room_with_exits(self):
        ast = parse('''<ROOM KITCHEN
            (IN ROOMS)
            (DESC "A kitchen")
            (NORTH TO HALLWAY)
            (SOUTH TO PANTRY)>''')
        data = extract_game_data(ast)
        room = data.rooms["KITCHEN"]
        assert room.get_property_values("NORTH") == ["TO", "HALLWAY"]
        assert room.get_property_values("SOUTH") == ["TO", "PANTRY"]

    def test_rooms_and_objects_separate(self):
        ast = parse('''
            <ROOM KITCHEN (IN ROOMS)>
            <OBJECT LAMP (IN KITCHEN)>
        ''')
        data = extract_game_data(ast)
        assert "KITCHEN" in data.rooms
        assert "LAMP" in data.objects
        assert "KITCHEN" not in data.objects
        assert "LAMP" not in data.rooms


class TestRoutineExtraction:
    """Test extracting ROUTINE definitions."""

    def test_simple_routine(self):
        ast = parse('<ROUTINE V-TAKE () <RTRUE>>')
        data = extract_game_data(ast)
        assert "V-TAKE" in data.routines
        routine = data.routines["V-TAKE"]
        assert routine.name == "V-TAKE"

    def test_routine_with_args(self):
        ast = parse('<ROUTINE MOVE-OBJ (OBJ DEST) <MOVE .OBJ .DEST>>')
        data = extract_game_data(ast)
        routine = data.routines["MOVE-OBJ"]
        assert routine.args == ["OBJ", "DEST"]

    def test_routine_with_aux_vars(self):
        ast = parse('<ROUTINE V-TAKE ("AUX" CNT TMP) <SETG CNT 0>>')
        data = extract_game_data(ast)
        routine = data.routines["V-TAKE"]
        assert routine.aux_vars == ["CNT", "TMP"]

    def test_routine_with_optional_args(self):
        ast = parse('<ROUTINE FOO (X "OPT" Y Z) <TELL .X>>')
        data = extract_game_data(ast)
        routine = data.routines["FOO"]
        assert routine.args == ["X"]
        assert routine.optional_args == ["Y", "Z"]

    def test_define_as_routine(self):
        ast = parse('<DEFINE HELPER () <RTRUE>>')
        data = extract_game_data(ast)
        assert "HELPER" in data.routines


class TestSyntaxExtraction:
    """Test extracting SYNTAX definitions."""

    def test_simple_syntax(self):
        ast = parse('<SYNTAX TAKE OBJECT = V-TAKE>')
        data = extract_game_data(ast)
        assert len(data.syntax) == 1
        syn = data.syntax[0]
        assert syn.verb == "TAKE"
        assert syn.action == "V-TAKE"

    def test_syntax_with_preaction(self):
        ast = parse('<SYNTAX TAKE OBJECT = V-TAKE PRE-TAKE>')
        data = extract_game_data(ast)
        syn = data.syntax[0]
        assert syn.action == "V-TAKE"
        assert syn.pre_action == "PRE-TAKE"

    def test_syntax_with_filters(self):
        ast = parse('<SYNTAX TAKE OBJECT (HELD MANY HAVE) = V-TAKE>')
        data = extract_game_data(ast)
        syn = data.syntax[0]
        assert "HELD" in syn.filters
        assert "MANY" in syn.filters
        assert "HAVE" in syn.filters

    def test_syntax_with_prep(self):
        ast = parse('<SYNTAX PUT OBJECT IN OBJECT = V-PUT>')
        data = extract_game_data(ast)
        syn = data.syntax[0]
        assert syn.verb == "PUT"
        assert "OBJECT" in syn.pattern
        assert "IN" in syn.pattern


class TestConstantExtraction:
    """Test extracting CONSTANT definitions."""

    def test_numeric_constant(self):
        ast = parse('<CONSTANT MAXSCORE 100>')
        data = extract_game_data(ast)
        assert "MAXSCORE" in data.constants
        assert data.constants["MAXSCORE"].value == 100

    def test_string_constant(self):
        ast = parse('<CONSTANT TITLE "Adventure">')
        data = extract_game_data(ast)
        assert data.constants["TITLE"].value == "Adventure"

    def test_atom_constant(self):
        ast = parse('<CONSTANT START-ROOM KITCHEN>')
        data = extract_game_data(ast)
        assert data.constants["START-ROOM"].value == "KITCHEN"


class TestGlobalExtraction:
    """Test extracting GLOBAL definitions."""

    def test_global_with_value(self):
        ast = parse('<GLOBAL SCORE 0>')
        data = extract_game_data(ast)
        assert "SCORE" in data.globals
        assert data.globals["SCORE"].value == 0

    def test_global_without_value(self):
        ast = parse('<GLOBAL HERE>')
        data = extract_game_data(ast)
        assert "HERE" in data.globals
        assert data.globals["HERE"].value is None


class TestSynonymExtraction:
    """Test extracting SYNONYM definitions."""

    def test_simple_synonym(self):
        ast = parse('<SYNONYM TAKE GET GRAB>')
        data = extract_game_data(ast)
        assert "TAKE" in data.synonyms
        assert data.synonyms["TAKE"] == ["GET", "GRAB"]

    def test_verb_synonym(self):
        ast = parse('<VERB-SYNONYM LOOK EXAMINE L>')
        data = extract_game_data(ast)
        assert "LOOK" in data.synonyms
        assert data.synonyms["LOOK"] == ["EXAMINE", "L"]

    def test_prep_synonym(self):
        ast = parse('<PREP-SYNONYM IN INTO INSIDE>')
        data = extract_game_data(ast)
        assert "IN" in data.synonyms


class TestDirectionsExtraction:
    """Test extracting DIRECTIONS definitions."""

    def test_directions(self):
        ast = parse('<DIRECTIONS NORTH SOUTH EAST WEST UP DOWN>')
        data = extract_game_data(ast)
        assert data.directions == ["NORTH", "SOUTH", "EAST", "WEST", "UP", "DOWN"]


class TestCompleteGame:
    """Test extracting a complete game structure."""

    def test_mini_game(self):
        source = '''
            <CONSTANT TITLE "Mini Adventure">
            <GLOBAL SCORE 0>
            <DIRECTIONS NORTH SOUTH>

            <ROOM START-ROOM
                (IN ROOMS)
                (DESC "You are at the start")
                (NORTH TO END-ROOM)>

            <ROOM END-ROOM
                (IN ROOMS)
                (DESC "The end room")
                (SOUTH TO START-ROOM)>

            <OBJECT LAMP
                (IN START-ROOM)
                (DESC "A lamp")
                (FLAGS TAKEBIT)>

            <ROUTINE V-LOOK ()
                <TELL "You look around.">>

            <SYNTAX LOOK = V-LOOK>
        '''
        ast = parse(source)
        data = extract_game_data(ast)

        assert "TITLE" in data.constants
        assert "SCORE" in data.globals
        assert len(data.rooms) == 2
        assert len(data.objects) == 1
        assert len(data.routines) == 1
        assert len(data.syntax) == 1
        assert data.directions == ["NORTH", "SOUTH"]
