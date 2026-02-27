---
id: gnusto-af0
title: Terminal UI (Textual)
type: task
priority: 2
created: '2026-01-19T19:26:46.207501-05:00'
updated: '2026-02-08T19:07:11.006579Z'
---

Build a proper fullscreen TUI using Textual (built on rich).

## Goals
- Segregated text streams: room description, objects, conversation, action/reaction, debug
- Keyboard shortcuts for common actions
- Toggle-able debug panel showing LLM context
- Clean separation from REPL mode (which remains useful for debugging)

## Future considerations
- Voice UI mode (phone/accessibility)
- GUI mode with graphics
- Notes/maps/context tracking (auto-journaling)
- Scrollbar-in-border rendering (LazyGit-style) - requires custom widget

See docs/ui.md for style notes per game.
