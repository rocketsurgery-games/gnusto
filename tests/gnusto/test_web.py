"""
Tests for the Gnusto web server.

Verifies that the FastAPI app correctly handles WebSocket connections,
HTTP routes, and that StaticFiles does not interfere with WebSocket routing.
"""

import json
import pathlib
import tempfile

import pytest
from starlette.testclient import TestClient

import gnusto.web as web

GAME_PATH = "games/testgame/"


@pytest.fixture
def app(tmp_path):
    """Create a FastAPI app with a fake webui dist directory."""
    fake_webui = tmp_path / "dist"
    fake_webui.mkdir()
    (fake_webui / "index.html").write_text("<html><body>Gnusto</body></html>")
    old_webui = web.WEBUI_DIR
    web.WEBUI_DIR = fake_webui
    try:
        yield web.create_app(GAME_PATH)
    finally:
        web.WEBUI_DIR = old_webui


@pytest.fixture
def client(app):
    return TestClient(app)


class TestWebSocketEndpoint:
    def test_websocket_connects_and_sends_initial_state(self, client):
        """WebSocket at /ws must connect successfully and send initial game state."""
        with client.websocket_connect("/ws") as ws:
            msg = json.loads(ws.receive_text())
            assert msg["type"] == "blocks"
            blocks = msg["blocks"]
            assert len(blocks) > 0

    def test_websocket_sends_turn_complete(self, client):
        """After initial state, server must send turn_complete."""
        with client.websocket_connect("/ws") as ws:
            messages = []
            # Collect until we see turn_complete or run out
            for _ in range(5):
                try:
                    msg = json.loads(ws.receive_text())
                    messages.append(msg)
                    if msg["type"] == "turn_complete":
                        break
                except Exception:
                    break
            types = [m["type"] for m in messages]
            assert "turn_complete" in types

    def test_websocket_does_not_interfere_with_http(self, client):
        """HTTP GET to / must work alongside the WebSocket route."""
        resp = client.get("/")
        assert resp.status_code == 200

    def test_static_files_served_at_root(self, client):
        """StaticFiles mount at / must serve static assets (html=True SPA mode)."""
        resp = client.get("/index.html")
        assert resp.status_code == 200
        assert b"Gnusto" in resp.content

    def test_game_theme_css_absent_is_empty_200(self, client):
        """Per-game theme route must 200 with text/css even when no theme.css
        exists, so the frontend <link> never 404s (gnusto-4ac5.9)."""
        resp = client.get("/game/theme.css")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/css")
        assert resp.text == ""

    def test_game_theme_css_served_when_present(self, tmp_path):
        """When a game ships theme.css, the route serves it as CSS."""
        game = tmp_path / "game"
        game.mkdir()
        (game / "game.grue").write_text('(world :start @r)\n(room @r :name "R")\n')
        (game / "theme.css").write_text(":root { --font-letter: 'Spooky'; }")
        fake_webui = tmp_path / "dist"
        fake_webui.mkdir()
        (fake_webui / "index.html").write_text("<html><body>Gnusto</body></html>")
        old_webui = web.WEBUI_DIR
        web.WEBUI_DIR = fake_webui
        try:
            c = TestClient(web.create_app(str(game)))
            resp = c.get("/game/theme.css")
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/css")
            assert "--font-letter" in resp.text
        finally:
            web.WEBUI_DIR = old_webui

    def test_no_recursion_on_websocket_open(self, client):
        """Opening a WebSocket must not trigger middleware recursion.

        This is a regression test for the StaticFiles-at-root middleware bug:
        without html=True, the Mount at '/' would leave unmatched paths as
        404s that Starlette re-dispatched through the middleware chain on
        WebSocket opens, causing BaseHTTPMiddleware dispatch_func recursion.
        """
        import sys

        original_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(200)
        try:
            with client.websocket_connect("/ws") as ws:
                msg = json.loads(ws.receive_text())
                assert msg["type"] in ("blocks", "scene_context", "turn_complete")
        except RecursionError:
            pytest.fail(
                "RecursionError: StaticFiles at '/' is triggering middleware "
                "recursion on WebSocket open. Fix: add html=True to StaticFiles."
            )
        finally:
            sys.setrecursionlimit(original_limit)
