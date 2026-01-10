; Tree-sitter highlights for GRUE
; GRUE - Game Runtime for Universal Experiences

; Comments
(comment) @comment

; Strings
(string) @string

; Numbers
(number) @number

; Keywords (:name, :description, etc.)
(keyword) @property

; Definition forms (world, room, object, etc.)
(defform) @keyword

; Built-in functions and special forms
(builtin) @function.builtin

; Directions (north, south, etc.)
(direction) @constant

; Flags (ONBIT, TAKEBIT, etc.)
(flag) @constant.builtin

; Behavior names (enter, leave, take, etc.)
(behavior_name) @function

; Unknown placeholder
(unknown) @punctuation.special

; General identifiers
(identifier) @variable

; Punctuation
"(" @punctuation.bracket
")" @punctuation.bracket
