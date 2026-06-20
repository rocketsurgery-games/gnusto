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


class TestCaptionSplash:
    def test_caption_converts(self):
        block = content_block_data_to_render(
            ContentBlockData(type="caption", text="Meanwhile, below...")
        )
        assert isinstance(block, render.Caption)
        assert block.text == "Meanwhile, below..."

    def test_caption_serializes(self):
        d = block_to_dict(render.Caption(text="hi"))
        assert d == {"type": "caption", "text": "hi", "beat": None}

    def test_splash_converts_with_entity(self):
        block = content_block_data_to_render(
            ContentBlockData(type="splash", text="IT RISES", entity="@vat")
        )
        assert isinstance(block, render.Splash)
        assert block.entity == "@vat"

    def test_splash_serializes(self):
        d = block_to_dict(render.Splash(text="IT RISES", entity="@vat"))
        assert d == {
            "type": "splash",
            "text": "IT RISES",
            "entity": "@vat",
            "beat": None,
        }


class TestDeploy:
    def test_reveal_deploy_passes_through(self):
        block = content_block_data_to_render(
            ContentBlockData(
                type="reveal", text="a knife", entity="@knife", deploy="inset"
            )
        )
        assert isinstance(block, render.Reveal)
        assert block.deploy == "inset"

    def test_focus_deploy_serializes(self):
        d = block_to_dict(render.Focus(text="x", entity="@hacker", deploy="feature"))
        assert d["deploy"] == "feature"


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
