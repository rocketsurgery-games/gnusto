; Aerial queries for GRUE
; Captures top-level definitions for outline view

; (room NAME ...) - Room definitions
(list
  (symbol (defform) @_type)
  (#eq? @_type "room")
  (symbol (identifier) @name)
  (#set! "kind" "Class")) @symbol

; (object NAME ...) - Object definitions
(list
  (symbol (defform) @_type)
  (#eq? @_type "object")
  (symbol (identifier) @name)
  (#set! "kind" "Struct")) @symbol

; (world ...) - World definition
(list
  (symbol (defform) @_type)
  (#eq? @_type "world")
  (#set! "kind" "Module")
  (#set! "name" "world")) @symbol

; (defsyntax NAME ...) - Syntax definitions
(list
  (symbol (defform) @_type)
  (#eq? @_type "defsyntax")
  (symbol (identifier) @name)
  (#set! "kind" "Interface")) @symbol

; (defglobal NAME ...) - Global definitions
(list
  (symbol (defform) @_type)
  (#eq? @_type "defglobal")
  (symbol (identifier) @name)
  (#set! "kind" "Variable")) @symbol

; (defroutine NAME ...) - Routine definitions
(list
  (symbol (defform) @_type)
  (#eq? @_type "defroutine")
  (symbol (identifier) @name)
  (#set! "kind" "Function")) @symbol
