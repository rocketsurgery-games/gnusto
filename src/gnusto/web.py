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
from .llm import ImageRequest
from .render import (
    ContentBlock, RoomEnter, ActionResult, Narrative, Image, SystemMessage,
    build_room_block,
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
            "exits": block.exits,
            "objects": block.objects,
            "inventory": block.inventory,
            "image": block.image,
        }
    elif isinstance(block, ActionResult):
        return {
            "type": "action_result",
            "text": block.text,
        }
    elif isinstance(block, Narrative):
        return {
            "type": "narrative",
            "text": block.text,
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

            # Track current room for change detection
            last_room: str | None = None

            # Main message loop
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)

                msg_type = message.get("type")

                if msg_type == "command":
                    command = message.get("text", "").strip()
                    if command:
                        if command.startswith("/"):
                            # Handle slash command
                            session, should_continue = await handle_slash_command_ws(
                                websocket, session, command,
                                app.state.game_path, app.state.game_dir, app.state.debug
                            )
                            if not should_continue:
                                break
                        else:
                            # Get room before processing
                            state_before = get_game_state(session.runtime)
                            last_room = state_before.room

                            # Process and send results
                            await handle_game_command(
                                websocket, session, command,
                                last_room, app.state.game_dir
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
        """Serve images from the game's renders directory."""
        img_path = app.state.game_dir / "assets" / "renders" / "cache" / path
        if img_path.exists():
            return FileResponse(img_path)
        return {"error": "Image not found"}

    # Mount static files (must be after specific routes)
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

    # Add intro if present
    if session.runtime.world.intro:
        blocks.append(Narrative(text=session.runtime.world.intro))

    # Add initial room state
    state = get_game_state(session.runtime)
    room_block = build_room_block(state, session.runtime, game_dir)
    blocks.append(room_block)

    # Add system message
    blocks.append(SystemMessage(text="Type commands in natural language.", level="info"))

    # Send blocks
    await websocket.send_text(json.dumps({
        "type": "blocks",
        "blocks": [block_to_dict(b) for b in blocks],
    }))

    # Signal ready for input
    await websocket.send_text(json.dumps({"type": "turn_complete"}))


async def handle_slash_command_ws(
    websocket: WebSocket,
    session: GameSession,
    command: str,
    game_path: str,
    game_dir: Path,
    debug: bool,
) -> tuple[GameSession, bool]:
    """
    Handle a slash command via websocket.

    Returns:
        Tuple of (session, should_continue) - session may be replaced on reset
    """
    result = handle_slash_command(command, session, game_dir)

    # Handle special actions
    if result.action == "quit":
        await websocket.send_text(json.dumps({"type": "quit"}))
        return session, False

    elif result.action == "clear":
        await websocket.send_text(json.dumps({"type": "clear"}))

    elif result.action == "reset":
        # Create new session
        session = GameSession.from_game_file(game_path, debug=debug)
        # Send reset action first
        await websocket.send_text(json.dumps({"type": "clear"}))
        # Then send initial state
        await send_initial_state(websocket, session, game_dir)
        return session, True

    # Send any blocks
    if result.blocks:
        await websocket.send_text(json.dumps({
            "type": "blocks",
            "blocks": [block_to_dict(b) for b in result.blocks],
        }))

    # Signal turn complete
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

    # Track futures for streamed content
    send_futures: list[concurrent.futures.Future] = []

    def on_narrative(text: str) -> None:
        """Stream LLM narrative immediately via websocket."""
        if text:
            block = Narrative(text=text)
            future = asyncio.run_coroutine_threadsafe(
                websocket.send_text(json.dumps({
                    "type": "blocks",
                    "blocks": [block_to_dict(block)],
                })),
                loop
            )
            send_futures.append(future)
            time.sleep(0.01)

    def on_image(image: ImageRequest) -> None:
        """Stream image immediately via websocket."""
        block = Image(
            src=image.path,
            alt=image.alt,
            layout=image.layout,
            size=image.size,
        )
        future = asyncio.run_coroutine_threadsafe(
            websocket.send_text(json.dumps({
                "type": "blocks",
                "blocks": [block_to_dict(block)],
            })),
            loop
        )
        send_futures.append(future)
        time.sleep(0.01)

    # Run process_input in thread pool so event loop stays responsive
    def do_process() -> None:
        session.process_input(command, on_narrative=on_narrative, on_image=on_image)

    await loop.run_in_executor(None, do_process)

    # Wait for any pending sends to complete (wrap concurrent futures for asyncio)
    if send_futures:
        await asyncio.gather(*[asyncio.wrap_future(f) for f in send_futures], return_exceptions=True)

    # Check for room change
    state = get_game_state(session.runtime)
    if state.room != previous_room:
        room_block = build_room_block(state, session.runtime, game_dir)
        await websocket.send_text(json.dumps({
            "type": "blocks",
            "blocks": [block_to_dict(room_block)],
        }))

    # Signal that the turn is complete
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
