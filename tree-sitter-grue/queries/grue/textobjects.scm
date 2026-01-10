; Tree-sitter textobjects for GRUE
; Use with nvim-treesitter-textobjects

; Function-like: top-level definitions
(source_file
  (list
    (symbol (defform)) @function.outer)) @function.outer

; Inner function: contents of a definition
(list
  (symbol (defform))
  (_)* @function.inner)

; Parameter-like: keywords with values
(list
  (keyword) @parameter.outer
  (_) @parameter.inner)

; Comments
(comment) @comment.outer

; Blocks: any list
(list) @block.outer
(list (_)* @block.inner)
