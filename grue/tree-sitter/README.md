# tree-sitter-grue

Tree-sitter grammar for GRUE (Game Runtime for Universal Experiences), a declarative DSL for interactive fiction world definitions.

## Installation

### As a Neovim plugin (recommended)

Add to your plugin manager (e.g., lazy.nvim):

```lua
{ "joelgwebber/tree-sitter-grue" }
```

Then run `:TSInstall grue`.

The plugin auto-registers the parser and filetype on load.

### Manual config

If you prefer explicit configuration:

```lua
local parser_config = require("nvim-treesitter.parsers").get_parser_configs()
parser_config.grue = {
  install_info = {
    url = "https://github.com/joelgwebber/tree-sitter-grue",
    files = { "src/parser.c" },
  },
  filetype = "grue",
}

vim.filetype.add({ extension = { grue = "grue" } })
```

Then run `:TSInstall grue`.

### Quick Install (no plugin manager)

```bash
# Compile the parser
cc -shared -o grue.so -I src src/parser.c -O2

# Copy to nvim-treesitter directories
cp grue.so ~/.local/share/nvim/lazy/nvim-treesitter/parser/
cp -r queries/grue ~/.local/share/nvim/lazy/nvim-treesitter/queries/
```

Add to your init.lua:
```lua
vim.filetype.add({ extension = { grue = "grue" } })
```

### Build from source

```bash
npm install
npx tree-sitter generate
```

## Syntax Highlighting

The grammar provides semantic highlighting for:

- **Keywords**: `:name`, `:description`, `:flags`, `:exits`, `:behaviors`, etc.
- **Definition forms**: `world`, `room`, `object`, `defsyntax`, `defglobal`, `defroutine`
- **Built-ins**: `case`, `true`, `false`, `and`, `or`, `not`, `eq?`, `in?`, `has-flag?`, etc.
- **Directions**: `north`, `south`, `east`, `west`, `up`, `down`, etc.
- **Flags**: `ONBIT`, `INVISIBLE`, `TAKEBIT`, `DOORBIT`, etc.
- **Behaviors**: `enter`, `leave`, `take`, `drop`, `examine`, `through`, etc.
- **Comments**: Lines starting with `;`
- **Strings**: Double-quoted strings with escape sequences
- **Numbers**: Integer literals

## Example GRUE Code

```grue
; A simple room definition
(room LIVING-ROOM
  :description "Living Room"
  :ldesc "You are in a cozy living room. A fireplace crackles warmly."
  :flags (ONBIT LIGHTBIT)
  :exits
    (
      (north :to KITCHEN)
      (east :to HALLWAY)
      (up :to UPSTAIRS)
    )
)

; An object with behaviors
(object LAMP
  :description "brass lamp"
  :location LIVING-ROOM
  :flags (TAKEBIT DEVICEBIT)
  :behaviors
    (
      (turn-on
        (case (not (has-flag? self ONBIT))
          :outcome (set-flag! self ONBIT)
          :message "The lamp is now on."))
      (turn-off
        (case (has-flag? self ONBIT)
          :outcome (clear-flag! self ONBIT)
          :message "The lamp is now off."))
    )
)
```

## License

MIT
