/// <reference types="tree-sitter-cli/dsl" />
// @ts-check

module.exports = grammar({
  name: "grue",

  extras: ($) => [/\s/, $.comment],

  rules: {
    source_file: ($) => repeat($._form),

    _form: ($) =>
      choice(
        $.list,
        $.symbol,
        $.keyword,
        $.string,
        $.number
      ),

    // Comments start with ; and go to end of line
    comment: ($) => /;[^\n]*/,

    // Lists: ( ... )
    list: ($) => seq("(", repeat($._form), ")"),

    // Keywords start with :
    keyword: ($) => /:[a-zA-Z_][a-zA-Z0-9_-]*/,

    // Symbols (identifiers)
    symbol: ($) =>
      choice(
        $.defform,
        $.builtin,
        $.direction,
        $.flag,
        $.behavior_name,
        $.unknown,
        $.identifier
      ),

    // Top-level definition forms
    defform: ($) =>
      choice("world", "room", "object", "defsyntax", "defglobal", "defroutine"),

    // Built-in functions and special forms
    builtin: ($) =>
      choice(
        "case",
        "true",
        "false",
        "and",
        "or",
        "not",
        "eq?",
        "in?",
        "has-flag?",
        "set-flag!",
        "clear-flag!",
        "move!",
        "tell",
        "random",
        "first-child",
        "next-sibling",
        "get-prop",
        "put-prop"
      ),

    // Directions
    direction: ($) =>
      choice(
        "north",
        "south",
        "east",
        "west",
        "up",
        "down",
        "northeast",
        "northwest",
        "southeast",
        "southwest",
        "in",
        "out",
        "land"
      ),

    // Common flags
    flag: ($) =>
      token(
        choice(
          "ONBIT",
          "INVISIBLE",
          "TAKEBIT",
          "DOORBIT",
          "OPENBIT",
          "OPENABLE",
          "LOCKED",
          "CONTBIT",
          "SURFACEBIT",
          "SEARCHBIT",
          "PERSON",
          "NDESCBIT",
          "LIGHTBIT",
          "FLAMEBIT",
          "FOODBIT",
          "DRINKBIT",
          "READBIT",
          "DEVICEBIT",
          "SWITCHBIT",
          "WEARBIT",
          "WORNBIT",
          "VEHBIT",
          "CLIMBBIT",
          "TRANSBIT",
          "TRYTAKEBIT",
          "ACTORBIT",
          "TOUCHBIT",
          "RMUNGBIT",
          "NOABIT",
          "AN"
        )
      ),

    // Behavior names (used in :behaviors blocks)
    behavior_name: ($) =>
      choice(
        "enter",
        "leave",
        "take",
        "drop",
        "examine",
        "through",
        "open",
        "close",
        "lock",
        "unlock",
        "read",
        "turn-on",
        "turn-off",
        "attack",
        "eat",
        "drink",
        "wear",
        "remove",
        "push",
        "pull",
        "climb",
        "smell",
        "listen",
        "touch"
      ),

    // Unknown/placeholder symbol
    unknown: ($) => "?",

    // General identifier (catch-all for other symbols)
    identifier: ($) => /[a-zA-Z_][a-zA-Z0-9_?!-]*/,

    // Strings with escape sequences
    string: ($) =>
      seq(
        '"',
        repeat(
          choice(
            /[^"\\]+/,
            seq("\\", /./)
          )
        ),
        '"'
      ),

    // Numbers (integers)
    number: ($) => /-?[0-9]+/,
  },
});
