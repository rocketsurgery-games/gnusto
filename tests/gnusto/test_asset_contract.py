"""The keyed-asset contract that underpins graceful degradation (gnusto-4ac5.6).

A panel that wants art but has no resolvable asset must receive a None image
signal (never a broken path), so the web UI degrades to a caption/typographic
fallback. These tests pin that contract at the resolver boundary.
"""

from gnusto import render


def test_missing_asset_resolves_to_none(monkeypatch, tmp_path):
    # resolver yields a key, but no matching file exists on disk -> None
    monkeypatch.setattr(render, "resolve_asset_key", lambda name, spec, rt: "ghost")
    (tmp_path / "assets").mkdir()
    url = render._resolve_image_url("spec", "@ghost", object(), tmp_path)
    assert url is None


def test_present_asset_resolves_to_url(monkeypatch, tmp_path):
    monkeypatch.setattr(render, "resolve_asset_key", lambda name, spec, rt: "crowbar")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "crowbar.jpg").write_bytes(b"x")
    url = render._resolve_image_url("spec", "@crowbar", object(), tmp_path)
    assert url == "/assets/crowbar.jpg"


def test_no_key_resolves_to_none(monkeypatch, tmp_path):
    # resolver yields nothing renderable -> None
    monkeypatch.setattr(render, "resolve_asset_key", lambda name, spec, rt: None)
    url = render._resolve_image_url("spec", "@x", object(), tmp_path)
    assert url is None
