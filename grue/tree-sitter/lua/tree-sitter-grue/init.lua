-- tree-sitter-grue
-- Tree-sitter grammar for GRUE (Game Runtime for Universal Experiences)

local M = {}

function M.setup()
  local ok, parsers = pcall(require, "nvim-treesitter.parsers")
  if not ok then
    vim.notify("tree-sitter-grue: nvim-treesitter not found", vim.log.levels.WARN)
    return
  end

  local parser_config = parsers.get_parser_configs()
  parser_config.grue = {
    install_info = {
      url = "https://github.com/joelgwebber/tree-sitter-grue",
      files = { "src/parser.c" },
    },
    filetype = "grue",
  }

  vim.filetype.add({ extension = { grue = "grue" } })
end

-- Auto-setup when required
M.setup()

return M
