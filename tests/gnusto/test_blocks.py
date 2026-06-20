"""Tests for the expanded block vocabulary: sfx blocks + beat pacing (4ac5.5)."""

from gnusto import render
from gnusto.llm import ContentBlockData, content_block_data_to_render
from gnusto.web import block_to_dict


class TestSfxBlock:
    def test_llm_sfx_converts_to_render_sfx(self):
        data = ContentBlockData(type="sfx", text="KRA-KOOM")
        block = content_block_data_to_render(data)
        assert isinstance(block, render.Sfx)
        assert block.text == "KRA-KOOM"

    def test_sfx_serializes(self):
        d = block_to_dict(render.Sfx(text="thoom"))
        assert d == {"type": "sfx", "text": "thoom", "beat": None}


class TestBeat:
    def test_beat_passes_through_conversion(self):
        data = ContentBlockData(type="narrate", text="It moves.", beat="emphasis")
        block = content_block_data_to_render(data)
        assert isinstance(block, render.Narrate)
        assert block.beat == "emphasis"

    def test_beat_serializes_on_dict(self):
        d = block_to_dict(render.Narrate(text="hi", beat="aside"))
        assert d["beat"] == "aside"

    def test_no_beat_is_none(self):
        block = content_block_data_to_render(ContentBlockData(type="speak", text="hi"))
        assert block.beat is None
