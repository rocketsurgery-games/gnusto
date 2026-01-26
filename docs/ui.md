# Gnusto UI Modes

UI modes for playing Gnusto games:

| Mode | Status | Description |
|------|--------|-------------|
| **Terminal** | ✅ Implemented | Rich-formatted terminal with colors, natural scrolling |
| **Voice** | 🔮 Future | Voice input/output for phones, accessibility |
| **Web** | 🔮 Future | Browser-based GUI with images, sounds |


# Terminal Mode

The default mode. Uses Rich for formatting with graceful degradation for
non-interactive terminals (pipes, scripts).

## Features

- **Colors & styling** - Room names (cyan), commands (green), dialogue (yellow), etc.
- **Natural scrolling** - Uses terminal's native scroll, no alternate screen
- **Slash commands** - `/save`, `/load`, `/debug`, `/help`, `/quit`
- **Pipe-friendly** - Works with `gnusto game/ | tee log.txt`

## Text Styles

| Style | Color/Format | Usage |
|-------|--------------|-------|
| `room.name` | Bold cyan | Room header |
| `room.desc` | Default | Room description |
| `room.nearby` | Dim | "Nearby: kitchen, hallway" |
| `room.inventory` | Dim | "Carrying: flashlight, key" |
| `command` | Bold green | Player commands |
| `action` | Dim | Game action results |
| `narrative` | Default | LLM narrative response |
| `dialogue` | Yellow | Character speech |
| `system` | Dim | System messages, errors |

## Usage

```bash
gnusto games/lurkinghorror/           # Play a game
gnusto games/lurkinghorror/ --debug   # With debug output
```

## Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/save [slot]` | Save game (default slot: "default") |
| `/load [slot]` | Load game |
| `/saves` | List available saves |
| `/debug` | Show LLM context |
| `/quit` | Exit game |


# Future: Web Mode

For rich graphics, we'll move to a web-based interface rather than trying to
do complex rendering in the terminal. Benefits:

- Real image support (not terminal graphics protocols)
- Sound and music
- Works on any device with a browser
- Easier to style and layout

Architecture: Local server + browser, or hosted.


# Future: Voice Mode

Accessibility-focused mode for:
- Visually impaired players
- Phone/mobile play
- Hands-free gaming

Would use speech-to-text for input, text-to-speech for output.
