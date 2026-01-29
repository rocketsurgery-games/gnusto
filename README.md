# Gnusto

LLM-powered interactive fiction system using the Grue language.

## Overview

Gnusto is a toolkit for creating and playing text adventure games:

- **Grue Language** - A LISP-like language for defining interactive fiction games with pure functional semantics and formal effect systems
- **LLM Player** - Play games using natural language via Claude
- **Frotz** - Static analysis tools for verifying winnability and detecting soft-locks
- **Filfre** - Generate scene illustrations using OmniGen2

## Installation

```bash
pip install -e .
```

## Development

### Setup

```bash
# Install dependencies and project in editable mode
uv sync

# Run tests
uv run python -m pytest tests/

# Run a specific game's tests
grue-test games/lurkinghorror/ -v
```

### Web UI Development

The web UI uses Vite + TypeScript:

```bash
cd src/gnusto/webui
npm install
npm run build      # Build for production
npm run dev        # Dev server with hot reload (proxies to Python backend)
```

## CLI Tools

### gnusto - Play Games

Play a Grue game with an LLM-powered natural language agent:

```bash
gnusto games/lurkinghorror/             # Terminal UI (default)
gnusto games/lurkinghorror/ --web       # Web UI at http://127.0.0.1:8000
gnusto games/lurkinghorror/ --web -p 3000  # Web UI on custom port
gnusto games/lurkinghorror/ --debug     # Show agent tool calls
```

### grue-test - Run Tests

Run Grue-native tests for game validation:

```bash
grue-test games/testgame/              # Test a game
grue-test games/lurkinghorror/ -v      # Verbose output
grue-test . -q                         # Quiet, summary only
```

### grue-repl - Interactive REPL

Interactive REPL for exploring Grue games:

```bash
grue-repl games/testgame/
```

### frotz - Design Tools

Static analysis tools for game design validation:

```bash
# Check if a state is reachable
frotz reach --to "@key@player" games/testgame
frotz reach --to "(= (:location @player) @lair)" games/lurkinghorror --dot reach.dot

# Full state space analysis with victory path
frotz analyze games/testgame --walkthrough
frotz analyze games/testgame --fast --dot states.dot
```

See `docs/frotz.md` for detailed documentation.

### zilch - ZIL Converter

Convert ZIL source code to Grue format (ZIL-changer):

```bash
zilch path/to/zil-game/ -d output/
zilch path/to/zil-game/ --stdout
```

### filfre - Scene Generation

Generate illustrations using OmniGen2 (requires CUDA GPU with 17GB+ VRAM).
Named after the Enchanter spell that creates gratuitous fireworks:

```bash
filfre --prompt "A white house in the woods, with a mailbox out front." --output white-house.png
filfre --prompt "A troll under a bridge" --output troll.png
```

See `CLAUDE.md` for hardware-specific notes.

## Project Structure

```
src/
  grue/         # Grue language runtime and parser
  frotz/        # Static analysis tools
  gnusto/       # LLM player
  filfre/       # Scene generation (filfre CLI)
games/
  testgame/     # Simple test game
  lurkinghorror/ # The Lurking Horror (in progress)
docs/
  frotz.md      # Frotz design and usage
  design/       # Detailed algorithm documentation
```

## Documentation

- `CLAUDE.md` - Instructions for AI assistants working on this codebase
- `docs/frotz.md` - Frotz static analysis documentation
- `docs/design/` - Algorithm design documents
- `games/lurkinghorror/README.md` - Notes on the LH conversion

