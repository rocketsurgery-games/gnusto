# tree-sitter-grue

Tree-sitter grammar for GRUE (Game Runtime for Universal Experiences), a declarative DSL for interactive fiction world definitions.

## Installation

### Neovim (with nvim-treesitter)

1. Add the parser to your nvim-treesitter config:

```lua
local parser_config = require("nvim-treesitter.parsers").get_parser_configs()
parser_config.grue = {
  install_info = {
    url = "/path/to/tree-sitter-grue",  -- local path or git URL
    files = { "src/parser.c" },
    branch = "main",
  },
  filetype = "grue",
}
```

2. Copy the queries to your Neovim config:

```bash
# Create the queries directory
mkdir -p ~/.config/nvim/queries/grue

# Copy the query files
cp queries/grue/*.scm ~/.config/nvim/queries/grue/
```

3. Set up the filetype (add to your init.lua):

```lua
vim.filetype.add({
  extension = {
    grue = "grue",
  },
})
```

4. Install the parser:

```vim
:TSInstall grue
```

### Manual Build

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
