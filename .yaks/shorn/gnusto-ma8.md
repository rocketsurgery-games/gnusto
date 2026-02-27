---
id: gnusto-ma8
title: Tree-sitter grammar for GRUE
type: task
priority: 2
created: '2026-01-10T13:28:21.564269-05:00'
updated: '2026-02-08T19:07:11.059771Z'
---

Create a Tree-sitter grammar for the GRUE DSL to enable syntax highlighting and code navigation in Neovim. This includes:

- Tree-sitter grammar (grammar.js) for GRUE's S-expression syntax
- Neovim queries for highlights, indents, and textobjects
- Installation/setup instructions

GRUE syntax elements to support:
- Top-level forms: defroom, defobject, defsyntax, defglobal, defroutine
- Keywords: :name, :description, :flags, :location, :action, :capacity, etc.
- Behaviors: (enter), (leave), (take), (through), etc. with (case ...) blocks
- S-expression structure: lists, atoms, strings, numbers, symbols
- Comments (if we add them)
