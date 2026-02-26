"""
Web server for Gnusto.

Serves the web UI and provides a WebSocket API for game interaction.
Uses content blocks for structured output.
"""

import asyncio
import concurrent.futures
import json
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .agent import GameSession
from .commands import handle_command as handle_slash_command
from .render import (
    ContentBlock, RoomEnter, ActionResult, Narrate, Speak, Think, Ambient,
    Reveal, Focus, Image, SystemMessage, DebugInfo,
    build_room_block, build_scene_context,
)
from .state import get_game_state


# Path to the built web UI
WEBUI_DIR = Path(__file__).parent / "webui" / "dist"


def block_to_dict(block: ContentBlock) -> dict[str, Any]:
    """Convert a ContentBlock to a JSON-serializable dict."""
    if isinstance(block, RoomEnter):
        return {
            "type": "room_enter",
            "room_id": block.room_id,
            "name": block.name,
            "description": block.description,
            "exits": [{"direction": e.direction, "destination": e.destination}
                      for e in block.exits],
            "objects": [{"id": o.id, "name": o.name, "behaviors": o.behaviors} for o in block.objects],
            "inventory": [{"id": o.id, "name": o.name, "behaviors": o.behaviors} for o in block.inventory],
            "image": block.image,
        }
    elif isinstance(block, ActionResult):
        return {
            "type": "action_result",
            "text": block.text,
        }
    elif isinstance(block, Narrate):
        return {
            "type": "narrate",
            "text": block.text,
        }
    elif isinstance(block, Speak):
        return {
            "type": "speak",
            "text": block.text,
            "speaker": block.speaker,
            "manner": block.manner,
        }
    elif isinstance(block, Think):
        return {
            "type": "think",
            "text": block.text,
        }
    elif isinstance(block, Ambient):
        return {
            "type": "ambient",
            "text": block.text,
        }
    elif isinstance(block, Reveal):
        return {
            "type": "reveal",
            "text": block.text,
            "entity": block.entity,
        }
    elif isinstance(block, Focus):
        return {
            "type": "focus",
            "text": block.text,
            "entity": block.entity,
        }
    elif isinstance(block, Image):
        return {
            "type": "image",
            "src": block.src,
            "alt": block.alt,
            "layout": block.layout,
            "size": block.size,
        }
    elif isinstance(block, SystemMessage):
        return {
            "type": "system",
            "text": block.text,
            "level": block.level,
        }
    elif isinstance(block, DebugInfo):
        return {
            "type": "debug",
            "label": block.label,
            "content": block.content,
        }
    else:
        return {"type": "unknown", "text": str(block)}


def create_app(game_path: str, debug: bool = False) -> FastAPI:
    """Create the FastAPI application for a game."""
    app = FastAPI(title="Gnusto", debug=debug)

    # Store game path in app state
    game_dir = Path(game_path).resolve()
    if game_dir.is_file():
        game_dir = game_dir.parent
    app.state.game_path = game_path
    app.state.game_dir = game_dir
    app.state.debug = debug

    @app.websocket("/ws")
    async def game_websocket(websocket: WebSocket):
        """WebSocket endpoint for game interaction."""
        await websocket.accept()

        # Create a new game session for this connection
        session = GameSession.from_game_file(
            app.state.game_path,
            debug=app.state.debug
        )

        try:
            # Send initial game state
            await send_initial_state(websocket, session, app.state.game_dir)

            # Main message loop
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)

                msg_type = message.get("type")

                if msg_type == "command":
                    command = message.get("text", "").strip()
                    if command:
                        if command.startswith("/"):
                            session, should_continue = await handle_slash_command_ws(
                                websocket, session, command,
                                app.state.game_path, app.state.game_dir, app.state.debug
                            )
                            if not should_continue:
                                break
                        else:
                            state_before = get_game_state(session.runtime)
                            last_room = state_before.room

                            await handle_game_command(
                                websocket, session, command,
                                last_room, app.state.game_dir,
                            )

        except WebSocketDisconnect:
            pass

    # Serve index.html for root
    @app.get("/")
    async def serve_index():
        index_path = WEBUI_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"error": "Web UI not built. Run: cd src/gnusto/webui && npm run build"}

    # Serve rendered images
    @app.get("/renders/{path:path}")
    async def serve_rendered_image(path: str):
        """Serve images from the game's renders or refs directories."""
        renders_dir = app.state.game_dir / "assets" / "renders"
        refs_dir = app.state.game_dir / "assets" / "refs"
        render_dirs = [renders_dir, renders_dir / "cache"]

        # Try exact match in renders
        for subdir in render_dirs:
            img_path = subdir / path
            if img_path.exists():
                return FileResponse(img_path)

        stem = Path(path).stem
        suffix = Path(path).suffix

        # Try stem-based match in renders (hash-suffixed files)
        for subdir in render_dirs:
            matches = sorted(subdir.glob(f"{stem}-*{suffix}"))
            if matches:
                return FileResponse(matches[-1])

        # Fall back to refs directory (any extension)
        if refs_dir.exists():
            ref_path = refs_dir / path
            if ref_path.exists():
                return FileResponse(ref_path)
            for match in refs_dir.glob(f"{stem}.*"):
                if match.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                    return FileResponse(match)

        return {"error": "Image not found"}

    # Serve game assets (refs, renders, etc.) at /assets/
    assets_dir = game_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # Mount web UI static files (must be last)
    if WEBUI_DIR.exists():
        app.mount("/", StaticFiles(directory=WEBUI_DIR), name="static")

    return app


async def send_initial_state(
    websocket: WebSocket,
    session: GameSession,
    game_dir: Path,
) -> None:
    """Send initial game state to the client."""
    blocks: list[ContentBlock] = []

    if session.runtime.world.intro:
        blocks.append(Narrate(text=session.runtime.world.intro))

    state = get_game_state(session.runtime)
    room_block = build_room_block(state, session.runtime, game_dir)
    blocks.append(room_block)

    blocks.append(SystemMessage(text="Type commands in natural language.", level="info"))

    # Send scene context (entity images) before blocks
    scene_ctx = build_scene_context(state, session.runtime, game_dir)
    if scene_ctx:
        await websocket.send_text(json.dumps({
            "type": "scene_context",
            "entities": scene_ctx,
        }))

    await websocket.send_text(json.dumps({
        "type": "blocks",
        "blocks": [block_to_dict(b) for b in blocks],
    }))

    await websocket.send_text(json.dumps({"type": "turn_complete"}))


async def handle_slash_command_ws(
    websocket: WebSocket,
    session: GameSession,
    command: str,
    game_path: str,
    game_dir: Path,
    debug: bool,
) -> tuple[GameSession, bool]:
    """Handle a slash command via websocket."""
    result = handle_slash_command(command, session, game_dir)

    if result.action == "quit":
        await websocket.send_text(json.dumps({"type": "quit"}))
        return session, False

    elif result.action == "clear":
        await websocket.send_text(json.dumps({"type": "clear"}))

    elif result.action == "reset":
        session = GameSession.from_game_file(game_path, debug=debug)
        await websocket.send_text(json.dumps({"type": "clear"}))
        await send_initial_state(websocket, session, game_dir)
        return session, True

    if result.blocks:
        await websocket.send_text(json.dumps({
            "type": "blocks",
            "blocks": [block_to_dict(b) for b in result.blocks],
        }))

    await websocket.send_text(json.dumps({"type": "turn_complete"}))
    return session, True


async def handle_game_command(
    websocket: WebSocket,
    session: GameSession,
    command: str,
    previous_room: str | None,
    game_dir: Path,
) -> None:
    """Process a player command and send results, streaming LLM outputs."""
    loop = asyncio.get_running_loop()

    send_futures: list[concurrent.futures.Future] = []

    def on_blocks(blocks: list) -> None:
        """Stream content blocks immediately via websocket."""
        block_dicts = [block_to_dict(b) for b in blocks]
        future = asyncio.run_coroutine_threadsafe(
            websocket.send_text(json.dumps({
                "type": "blocks",
                "blocks": block_dicts,
            })),
            loop
        )
        send_futures.append(future)
        time.sleep(0.01)

    def on_debug(action_sexpr: str, result_details: str) -> None:
        """Stream debug info as a DebugInfo block via websocket."""
        block = DebugInfo(label=action_sexpr, content=result_details)
        future = asyncio.run_coroutine_threadsafe(
            websocket.send_text(json.dumps({
                "type": "blocks",
                "blocks": [block_to_dict(block)],
            })),
            loop
        )
        send_futures.append(future)
        time.sleep(0.01)

    def do_process() -> None:
        session.process_input(
            command,
            on_blocks=on_blocks,
            on_debug=on_debug if session.debug else None,
        )

    await loop.run_in_executor(None, do_process)

    if send_futures:
        await asyncio.gather(*[asyncio.wrap_future(f) for f in send_futures], return_exceptions=True)

    state = get_game_state(session.runtime)

    # Always refresh scene context (entity images may have changed)
    scene_ctx = build_scene_context(state, session.runtime, game_dir)
    if scene_ctx:
        await websocket.send_text(json.dumps({
            "type": "scene_context",
            "entities": scene_ctx,
        }))

    if state.room != previous_room:
        # Full room transition
        room_block = build_room_block(state, session.runtime, game_dir)
        await websocket.send_text(json.dumps({
            "type": "blocks",
            "blocks": [block_to_dict(room_block)],
        }))
    else:
        # Same room — update sidebar (exits, objects, inventory)
        room_block = build_room_block(state, session.runtime, game_dir)
        await websocket.send_text(json.dumps({
            "type": "state_update",
            "exits": [{"direction": e.direction, "destination": e.destination}
                       for e in room_block.exits],
            "objects": [{"id": o.id, "name": o.name, "behaviors": o.behaviors} for o in room_block.objects],
            "inventory": [{"id": o.id, "name": o.name, "behaviors": o.behaviors} for o in room_block.inventory],
        }))

    await websocket.send_text(json.dumps({"type": "turn_complete"}))


def run_server(game_path: str, host: str = "127.0.0.1", port: int = 8000, debug: bool = False) -> None:
    """Run the web server."""
    import uvicorn

    app = create_app(game_path, debug=debug)

    print(f"Starting Gnusto web server...")
    print(f"Game: {game_path}")
    print(f"Open http://{host}:{port} in your browser")
    print()

    uvicorn.run(app, host=host, port=port, log_level="info" if debug else "warning")
