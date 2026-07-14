#!/usr/bin/env python3
"""Generate a human-readable playthrough transcript.

Drives the real parse-only harness (natural-language in, engine-authored text
out) over a scripted walkthrough and writes a clean, human-readable transcript:
each turn shows the player's NL command (``> ...``) followed by the game's
authored output. No debug tool calls, no LLM-invented prose.

Usage:
    python scripts/make_transcript.py [GAME_DIR] [-o OUT.md]

The walkthrough below is a coherent "recover your first treasure" arc for
Zork I (enter the house, gear up, descend, cross to the Gallery, and bank the
painting in the trophy case). Because the action selection runs through a live
LLM, exact wording of chosen actions can vary run to run; the engine's output
text does not.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from gnusto.agent import GameSession
from gnusto.commands import render_blocks_to_text
from gnusto.render import build_room_block
from gnusto.state import get_game_state

# A coherent single-session adventure: open the mailbox, enter the house, gear
# up, descend, slip past to the Gallery for the painting, climb the chimney
# home, and bank the treasure.
WALKTHROUGH = [
    "open the mailbox",
    "read the leaflet",
    "go north",
    "go east",
    "open the window",
    "climb through the window into the kitchen",
    "go west to the living room",
    "take the lamp and the sword",
    "turn on the lamp",
    "move the rug",
    "open the trap door",
    "go down",
    "go south",
    "go east",
    "take the painting",
    "drop the sword",
    "go north",
    "go up the chimney",
    "go west",
    "open the trophy case",
    "put the painting in the trophy case",
    "look",
]


def load_commands(path: str) -> list[str]:
    """Read natural-language commands from a file (one per line).

    Blank lines and ``#`` comment lines are ignored, so the file can carry
    section headers for readability. This lets a natural-language walkthrough
    (e.g. from the play-grue skill) drive the transcript directly.
    """
    commands = []
    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        commands.append(line)
    return commands


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("game", nargs="?", default="games/zork1/", help="game directory")
    ap.add_argument("-o", "--out", default=None, help="write transcript to this file")
    ap.add_argument(
        "-c",
        "--commands",
        default=None,
        help="file of natural-language commands (one per line; # comments ok). "
        "Defaults to the built-in first-treasure walkthrough.",
    )
    ap.add_argument(
        "--load",
        default=None,
        metavar="SLOT",
        help="resume from this save slot (a continuation segment; the title/intro "
        "and opening-room header are omitted so segments stitch cleanly).",
    )
    ap.add_argument(
        "--save",
        default=None,
        metavar="SLOT",
        help="save to this slot after the last command (checkpoint for the next segment).",
    )
    args = ap.parse_args()

    walkthrough = load_commands(args.commands) if args.commands else WALKTHROUGH

    session = GameSession.from_game_file(args.game, parsing_only=True)
    runtime = session.runtime
    game_dir = session.game_dir

    # Resume from a checkpoint (reliable segment-by-segment play): load the saved
    # state before playing this segment's commands.
    if args.load:
        from grue.save import load_game

        load_game(runtime, args.load)  # mutates runtime state to the saved game

    lines: list[str] = []

    def emit(text: str) -> None:
        if text and text.strip():
            lines.append(text.rstrip())

    # Title + intro + opening room — only for a fresh start. A --load continuation
    # omits them so concatenated segments read as one seamless transcript.
    if not args.load:
        title = runtime.world.name or "Adventure"
        lines.append(f"# {title} — transcript\n")
        if runtime.world.intro:
            emit(runtime.world.intro)
        state = get_game_state(runtime)
        emit(render_blocks_to_text([build_room_block(state, runtime, game_dir)]))
    else:
        state = get_game_state(runtime)

    prev_room = state.room
    for command in walkthrough:
        collected: list = []
        session.process_input(command, on_blocks=collected.extend)
        lines.append(f"\n> {command}\n")
        emit(render_blocks_to_text(collected))

        # Mirror the front-ends: show the destination room when it changes and
        # the game hasn't ended (so we don't render past a death/victory).
        state = get_game_state(runtime)
        if not session._end_state() and state.room != prev_room:
            emit(render_blocks_to_text([build_room_block(state, runtime, game_dir)]))
        prev_room = state.room
        if session._end_state():
            break

    if args.save:
        from grue.save import save_game

        save_game(runtime, args.save, session.turn_history, session.summaries)

    ended = session._end_state()
    transcript = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(transcript)
        print(f"Wrote transcript to {args.out}" + (f" [END: {ended}]" if ended else ""))
    else:
        print(transcript)


if __name__ == "__main__":
    main()
