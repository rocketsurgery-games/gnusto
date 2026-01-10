; Tree-sitter indents for GRUE

; Lists increase indent
(list) @indent.begin

; Closing paren decreases indent
")" @indent.end @indent.branch
