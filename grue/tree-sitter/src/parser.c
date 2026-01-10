#include "tree_sitter/parser.h"

#if defined(__GNUC__) || defined(__clang__)
#pragma GCC diagnostic ignored "-Wmissing-field-initializers"
#endif

#ifdef _MSC_VER
#pragma optimize("", off)
#elif defined(__clang__)
#pragma clang optimize off
#elif defined(__GNUC__)
#pragma GCC optimize ("O0")
#endif

#define LANGUAGE_VERSION 14
#define STATE_COUNT 21
#define LARGE_STATE_COUNT 15
#define SYMBOL_COUNT 85
#define ALIAS_COUNT 0
#define TOKEN_COUNT 74
#define EXTERNAL_TOKEN_COUNT 0
#define FIELD_COUNT 0
#define MAX_ALIAS_SEQUENCE_LENGTH 3
#define PRODUCTION_ID_COUNT 1

enum ts_symbol_identifiers {
  sym_comment = 1,
  anon_sym_LPAREN = 2,
  anon_sym_RPAREN = 3,
  sym_keyword = 4,
  anon_sym_world = 5,
  anon_sym_room = 6,
  anon_sym_object = 7,
  anon_sym_defsyntax = 8,
  anon_sym_defglobal = 9,
  anon_sym_defroutine = 10,
  anon_sym_case = 11,
  anon_sym_true = 12,
  anon_sym_false = 13,
  anon_sym_and = 14,
  anon_sym_or = 15,
  anon_sym_not = 16,
  anon_sym_eq_QMARK = 17,
  anon_sym_in_QMARK = 18,
  anon_sym_has_DASHflag_QMARK = 19,
  anon_sym_set_DASHflag_BANG = 20,
  anon_sym_clear_DASHflag_BANG = 21,
  anon_sym_move_BANG = 22,
  anon_sym_tell = 23,
  anon_sym_random = 24,
  anon_sym_first_DASHchild = 25,
  anon_sym_next_DASHsibling = 26,
  anon_sym_get_DASHprop = 27,
  anon_sym_put_DASHprop = 28,
  anon_sym_north = 29,
  anon_sym_south = 30,
  anon_sym_east = 31,
  anon_sym_west = 32,
  anon_sym_up = 33,
  anon_sym_down = 34,
  anon_sym_northeast = 35,
  anon_sym_northwest = 36,
  anon_sym_southeast = 37,
  anon_sym_southwest = 38,
  anon_sym_in = 39,
  anon_sym_out = 40,
  anon_sym_land = 41,
  sym_flag = 42,
  anon_sym_enter = 43,
  anon_sym_leave = 44,
  anon_sym_take = 45,
  anon_sym_drop = 46,
  anon_sym_examine = 47,
  anon_sym_through = 48,
  anon_sym_open = 49,
  anon_sym_close = 50,
  anon_sym_lock = 51,
  anon_sym_unlock = 52,
  anon_sym_read = 53,
  anon_sym_turn_DASHon = 54,
  anon_sym_turn_DASHoff = 55,
  anon_sym_attack = 56,
  anon_sym_eat = 57,
  anon_sym_drink = 58,
  anon_sym_wear = 59,
  anon_sym_remove = 60,
  anon_sym_push = 61,
  anon_sym_pull = 62,
  anon_sym_climb = 63,
  anon_sym_smell = 64,
  anon_sym_listen = 65,
  anon_sym_touch = 66,
  sym_unknown = 67,
  sym_identifier = 68,
  anon_sym_DQUOTE = 69,
  aux_sym_string_token1 = 70,
  anon_sym_BSLASH = 71,
  aux_sym_string_token2 = 72,
  sym_number = 73,
  sym_source_file = 74,
  sym__form = 75,
  sym_list = 76,
  sym_symbol = 77,
  sym_defform = 78,
  sym_builtin = 79,
  sym_direction = 80,
  sym_behavior_name = 81,
  sym_string = 82,
  aux_sym_source_file_repeat1 = 83,
  aux_sym_string_repeat1 = 84,
};

static const char * const ts_symbol_names[] = {
  [ts_builtin_sym_end] = "end",
  [sym_comment] = "comment",
  [anon_sym_LPAREN] = "(",
  [anon_sym_RPAREN] = ")",
  [sym_keyword] = "keyword",
  [anon_sym_world] = "world",
  [anon_sym_room] = "room",
  [anon_sym_object] = "object",
  [anon_sym_defsyntax] = "defsyntax",
  [anon_sym_defglobal] = "defglobal",
  [anon_sym_defroutine] = "defroutine",
  [anon_sym_case] = "case",
  [anon_sym_true] = "true",
  [anon_sym_false] = "false",
  [anon_sym_and] = "and",
  [anon_sym_or] = "or",
  [anon_sym_not] = "not",
  [anon_sym_eq_QMARK] = "eq\?",
  [anon_sym_in_QMARK] = "in\?",
  [anon_sym_has_DASHflag_QMARK] = "has-flag\?",
  [anon_sym_set_DASHflag_BANG] = "set-flag!",
  [anon_sym_clear_DASHflag_BANG] = "clear-flag!",
  [anon_sym_move_BANG] = "move!",
  [anon_sym_tell] = "tell",
  [anon_sym_random] = "random",
  [anon_sym_first_DASHchild] = "first-child",
  [anon_sym_next_DASHsibling] = "next-sibling",
  [anon_sym_get_DASHprop] = "get-prop",
  [anon_sym_put_DASHprop] = "put-prop",
  [anon_sym_north] = "north",
  [anon_sym_south] = "south",
  [anon_sym_east] = "east",
  [anon_sym_west] = "west",
  [anon_sym_up] = "up",
  [anon_sym_down] = "down",
  [anon_sym_northeast] = "northeast",
  [anon_sym_northwest] = "northwest",
  [anon_sym_southeast] = "southeast",
  [anon_sym_southwest] = "southwest",
  [anon_sym_in] = "in",
  [anon_sym_out] = "out",
  [anon_sym_land] = "land",
  [sym_flag] = "flag",
  [anon_sym_enter] = "enter",
  [anon_sym_leave] = "leave",
  [anon_sym_take] = "take",
  [anon_sym_drop] = "drop",
  [anon_sym_examine] = "examine",
  [anon_sym_through] = "through",
  [anon_sym_open] = "open",
  [anon_sym_close] = "close",
  [anon_sym_lock] = "lock",
  [anon_sym_unlock] = "unlock",
  [anon_sym_read] = "read",
  [anon_sym_turn_DASHon] = "turn-on",
  [anon_sym_turn_DASHoff] = "turn-off",
  [anon_sym_attack] = "attack",
  [anon_sym_eat] = "eat",
  [anon_sym_drink] = "drink",
  [anon_sym_wear] = "wear",
  [anon_sym_remove] = "remove",
  [anon_sym_push] = "push",
  [anon_sym_pull] = "pull",
  [anon_sym_climb] = "climb",
  [anon_sym_smell] = "smell",
  [anon_sym_listen] = "listen",
  [anon_sym_touch] = "touch",
  [sym_unknown] = "unknown",
  [sym_identifier] = "identifier",
  [anon_sym_DQUOTE] = "\"",
  [aux_sym_string_token1] = "string_token1",
  [anon_sym_BSLASH] = "\\",
  [aux_sym_string_token2] = "string_token2",
  [sym_number] = "number",
  [sym_source_file] = "source_file",
  [sym__form] = "_form",
  [sym_list] = "list",
  [sym_symbol] = "symbol",
  [sym_defform] = "defform",
  [sym_builtin] = "builtin",
  [sym_direction] = "direction",
  [sym_behavior_name] = "behavior_name",
  [sym_string] = "string",
  [aux_sym_source_file_repeat1] = "source_file_repeat1",
  [aux_sym_string_repeat1] = "string_repeat1",
};

static const TSSymbol ts_symbol_map[] = {
  [ts_builtin_sym_end] = ts_builtin_sym_end,
  [sym_comment] = sym_comment,
  [anon_sym_LPAREN] = anon_sym_LPAREN,
  [anon_sym_RPAREN] = anon_sym_RPAREN,
  [sym_keyword] = sym_keyword,
  [anon_sym_world] = anon_sym_world,
  [anon_sym_room] = anon_sym_room,
  [anon_sym_object] = anon_sym_object,
  [anon_sym_defsyntax] = anon_sym_defsyntax,
  [anon_sym_defglobal] = anon_sym_defglobal,
  [anon_sym_defroutine] = anon_sym_defroutine,
  [anon_sym_case] = anon_sym_case,
  [anon_sym_true] = anon_sym_true,
  [anon_sym_false] = anon_sym_false,
  [anon_sym_and] = anon_sym_and,
  [anon_sym_or] = anon_sym_or,
  [anon_sym_not] = anon_sym_not,
  [anon_sym_eq_QMARK] = anon_sym_eq_QMARK,
  [anon_sym_in_QMARK] = anon_sym_in_QMARK,
  [anon_sym_has_DASHflag_QMARK] = anon_sym_has_DASHflag_QMARK,
  [anon_sym_set_DASHflag_BANG] = anon_sym_set_DASHflag_BANG,
  [anon_sym_clear_DASHflag_BANG] = anon_sym_clear_DASHflag_BANG,
  [anon_sym_move_BANG] = anon_sym_move_BANG,
  [anon_sym_tell] = anon_sym_tell,
  [anon_sym_random] = anon_sym_random,
  [anon_sym_first_DASHchild] = anon_sym_first_DASHchild,
  [anon_sym_next_DASHsibling] = anon_sym_next_DASHsibling,
  [anon_sym_get_DASHprop] = anon_sym_get_DASHprop,
  [anon_sym_put_DASHprop] = anon_sym_put_DASHprop,
  [anon_sym_north] = anon_sym_north,
  [anon_sym_south] = anon_sym_south,
  [anon_sym_east] = anon_sym_east,
  [anon_sym_west] = anon_sym_west,
  [anon_sym_up] = anon_sym_up,
  [anon_sym_down] = anon_sym_down,
  [anon_sym_northeast] = anon_sym_northeast,
  [anon_sym_northwest] = anon_sym_northwest,
  [anon_sym_southeast] = anon_sym_southeast,
  [anon_sym_southwest] = anon_sym_southwest,
  [anon_sym_in] = anon_sym_in,
  [anon_sym_out] = anon_sym_out,
  [anon_sym_land] = anon_sym_land,
  [sym_flag] = sym_flag,
  [anon_sym_enter] = anon_sym_enter,
  [anon_sym_leave] = anon_sym_leave,
  [anon_sym_take] = anon_sym_take,
  [anon_sym_drop] = anon_sym_drop,
  [anon_sym_examine] = anon_sym_examine,
  [anon_sym_through] = anon_sym_through,
  [anon_sym_open] = anon_sym_open,
  [anon_sym_close] = anon_sym_close,
  [anon_sym_lock] = anon_sym_lock,
  [anon_sym_unlock] = anon_sym_unlock,
  [anon_sym_read] = anon_sym_read,
  [anon_sym_turn_DASHon] = anon_sym_turn_DASHon,
  [anon_sym_turn_DASHoff] = anon_sym_turn_DASHoff,
  [anon_sym_attack] = anon_sym_attack,
  [anon_sym_eat] = anon_sym_eat,
  [anon_sym_drink] = anon_sym_drink,
  [anon_sym_wear] = anon_sym_wear,
  [anon_sym_remove] = anon_sym_remove,
  [anon_sym_push] = anon_sym_push,
  [anon_sym_pull] = anon_sym_pull,
  [anon_sym_climb] = anon_sym_climb,
  [anon_sym_smell] = anon_sym_smell,
  [anon_sym_listen] = anon_sym_listen,
  [anon_sym_touch] = anon_sym_touch,
  [sym_unknown] = sym_unknown,
  [sym_identifier] = sym_identifier,
  [anon_sym_DQUOTE] = anon_sym_DQUOTE,
  [aux_sym_string_token1] = aux_sym_string_token1,
  [anon_sym_BSLASH] = anon_sym_BSLASH,
  [aux_sym_string_token2] = aux_sym_string_token2,
  [sym_number] = sym_number,
  [sym_source_file] = sym_source_file,
  [sym__form] = sym__form,
  [sym_list] = sym_list,
  [sym_symbol] = sym_symbol,
  [sym_defform] = sym_defform,
  [sym_builtin] = sym_builtin,
  [sym_direction] = sym_direction,
  [sym_behavior_name] = sym_behavior_name,
  [sym_string] = sym_string,
  [aux_sym_source_file_repeat1] = aux_sym_source_file_repeat1,
  [aux_sym_string_repeat1] = aux_sym_string_repeat1,
};

static const TSSymbolMetadata ts_symbol_metadata[] = {
  [ts_builtin_sym_end] = {
    .visible = false,
    .named = true,
  },
  [sym_comment] = {
    .visible = true,
    .named = true,
  },
  [anon_sym_LPAREN] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_RPAREN] = {
    .visible = true,
    .named = false,
  },
  [sym_keyword] = {
    .visible = true,
    .named = true,
  },
  [anon_sym_world] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_room] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_object] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_defsyntax] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_defglobal] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_defroutine] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_case] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_true] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_false] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_and] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_or] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_not] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_eq_QMARK] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_in_QMARK] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_has_DASHflag_QMARK] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_set_DASHflag_BANG] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_clear_DASHflag_BANG] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_move_BANG] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_tell] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_random] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_first_DASHchild] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_next_DASHsibling] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_get_DASHprop] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_put_DASHprop] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_north] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_south] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_east] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_west] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_up] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_down] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_northeast] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_northwest] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_southeast] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_southwest] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_in] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_out] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_land] = {
    .visible = true,
    .named = false,
  },
  [sym_flag] = {
    .visible = true,
    .named = true,
  },
  [anon_sym_enter] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_leave] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_take] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_drop] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_examine] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_through] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_open] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_close] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_lock] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_unlock] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_read] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_turn_DASHon] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_turn_DASHoff] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_attack] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_eat] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_drink] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_wear] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_remove] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_push] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_pull] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_climb] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_smell] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_listen] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_touch] = {
    .visible = true,
    .named = false,
  },
  [sym_unknown] = {
    .visible = true,
    .named = true,
  },
  [sym_identifier] = {
    .visible = true,
    .named = true,
  },
  [anon_sym_DQUOTE] = {
    .visible = true,
    .named = false,
  },
  [aux_sym_string_token1] = {
    .visible = false,
    .named = false,
  },
  [anon_sym_BSLASH] = {
    .visible = true,
    .named = false,
  },
  [aux_sym_string_token2] = {
    .visible = false,
    .named = false,
  },
  [sym_number] = {
    .visible = true,
    .named = true,
  },
  [sym_source_file] = {
    .visible = true,
    .named = true,
  },
  [sym__form] = {
    .visible = false,
    .named = true,
  },
  [sym_list] = {
    .visible = true,
    .named = true,
  },
  [sym_symbol] = {
    .visible = true,
    .named = true,
  },
  [sym_defform] = {
    .visible = true,
    .named = true,
  },
  [sym_builtin] = {
    .visible = true,
    .named = true,
  },
  [sym_direction] = {
    .visible = true,
    .named = true,
  },
  [sym_behavior_name] = {
    .visible = true,
    .named = true,
  },
  [sym_string] = {
    .visible = true,
    .named = true,
  },
  [aux_sym_source_file_repeat1] = {
    .visible = false,
    .named = false,
  },
  [aux_sym_string_repeat1] = {
    .visible = false,
    .named = false,
  },
};

static const TSSymbol ts_alias_sequences[PRODUCTION_ID_COUNT][MAX_ALIAS_SEQUENCE_LENGTH] = {
  [0] = {0},
};

static const uint16_t ts_non_terminal_alias_map[] = {
  0,
};

static const TSStateId ts_primary_state_ids[STATE_COUNT] = {
  [0] = 0,
  [1] = 1,
  [2] = 2,
  [3] = 3,
  [4] = 4,
  [5] = 5,
  [6] = 6,
  [7] = 7,
  [8] = 8,
  [9] = 9,
  [10] = 10,
  [11] = 11,
  [12] = 12,
  [13] = 13,
  [14] = 14,
  [15] = 15,
  [16] = 16,
  [17] = 17,
  [18] = 18,
  [19] = 19,
  [20] = 20,
};

static bool ts_lex(TSLexer *lexer, TSStateId state) {
  START_LEXER();
  eof = lexer->eof(lexer);
  switch (state) {
    case 0:
      if (eof) ADVANCE(5);
      ADVANCE_MAP(
        '"', 364,
        '(', 8,
        ')', 9,
        '-', 3,
        ':', 4,
        ';', 7,
        '?', 73,
        'A', 100,
        'C', 135,
        'D', 109,
        'F', 136,
        'I', 148,
        'L', 124,
        'N', 107,
        'O', 141,
        'P', 111,
        'R', 115,
        'S', 117,
        'T', 88,
        'V', 112,
        'W', 118,
        '\\', 367,
        'a', 279,
        'c', 170,
        'd', 206,
        'e', 171,
        'f', 172,
        'g', 219,
        'h', 175,
        'i', 280,
        'l', 174,
        'm', 293,
        'n', 207,
        'o', 190,
        'p', 350,
        'r', 187,
        's', 223,
        't', 173,
        'u', 286,
        'w', 208,
      );
      if (('\t' <= lookahead && lookahead <= '\r') ||
          lookahead == ' ') SKIP(0);
      if (('0' <= lookahead && lookahead <= '9')) ADVANCE(370);
      if (('B' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 1:
      if (lookahead == '\n') SKIP(1);
      if (lookahead == ';') ADVANCE(7);
      if (('\t' <= lookahead && lookahead <= '\r') ||
          lookahead == ' ') ADVANCE(369);
      if (lookahead != 0) ADVANCE(368);
      END_STATE();
    case 2:
      if (lookahead == '"') ADVANCE(364);
      if (lookahead == ';') ADVANCE(6);
      if (lookahead == '\\') ADVANCE(367);
      if (('\t' <= lookahead && lookahead <= '\r') ||
          lookahead == ' ') ADVANCE(365);
      if (lookahead != 0) ADVANCE(366);
      END_STATE();
    case 3:
      if (('0' <= lookahead && lookahead <= '9')) ADVANCE(370);
      END_STATE();
    case 4:
      if (('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(10);
      END_STATE();
    case 5:
      ACCEPT_TOKEN(ts_builtin_sym_end);
      END_STATE();
    case 6:
      ACCEPT_TOKEN(sym_comment);
      if (lookahead == '\n') ADVANCE(366);
      if (lookahead == '"' ||
          lookahead == '\\') ADVANCE(7);
      if (lookahead != 0) ADVANCE(6);
      END_STATE();
    case 7:
      ACCEPT_TOKEN(sym_comment);
      if (lookahead != 0 &&
          lookahead != '\n') ADVANCE(7);
      END_STATE();
    case 8:
      ACCEPT_TOKEN(anon_sym_LPAREN);
      END_STATE();
    case 9:
      ACCEPT_TOKEN(anon_sym_RPAREN);
      END_STATE();
    case 10:
      ACCEPT_TOKEN(sym_keyword);
      if (lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(10);
      END_STATE();
    case 11:
      ACCEPT_TOKEN(anon_sym_world);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 12:
      ACCEPT_TOKEN(anon_sym_room);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 13:
      ACCEPT_TOKEN(anon_sym_object);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 14:
      ACCEPT_TOKEN(anon_sym_defsyntax);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 15:
      ACCEPT_TOKEN(anon_sym_defglobal);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 16:
      ACCEPT_TOKEN(anon_sym_defroutine);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 17:
      ACCEPT_TOKEN(anon_sym_case);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 18:
      ACCEPT_TOKEN(anon_sym_true);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 19:
      ACCEPT_TOKEN(anon_sym_false);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 20:
      ACCEPT_TOKEN(anon_sym_and);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 21:
      ACCEPT_TOKEN(anon_sym_or);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 22:
      ACCEPT_TOKEN(anon_sym_not);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 23:
      ACCEPT_TOKEN(anon_sym_eq_QMARK);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 24:
      ACCEPT_TOKEN(anon_sym_in_QMARK);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 25:
      ACCEPT_TOKEN(anon_sym_has_DASHflag_QMARK);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 26:
      ACCEPT_TOKEN(anon_sym_set_DASHflag_BANG);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 27:
      ACCEPT_TOKEN(anon_sym_clear_DASHflag_BANG);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 28:
      ACCEPT_TOKEN(anon_sym_move_BANG);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 29:
      ACCEPT_TOKEN(anon_sym_tell);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 30:
      ACCEPT_TOKEN(anon_sym_random);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 31:
      ACCEPT_TOKEN(anon_sym_first_DASHchild);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 32:
      ACCEPT_TOKEN(anon_sym_next_DASHsibling);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 33:
      ACCEPT_TOKEN(anon_sym_get_DASHprop);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 34:
      ACCEPT_TOKEN(anon_sym_put_DASHprop);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 35:
      ACCEPT_TOKEN(anon_sym_north);
      if (lookahead == 'e') ADVANCE(188);
      if (lookahead == 'w') ADVANCE(227);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 36:
      ACCEPT_TOKEN(anon_sym_south);
      if (lookahead == 'e') ADVANCE(189);
      if (lookahead == 'w') ADVANCE(228);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 37:
      ACCEPT_TOKEN(anon_sym_east);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 38:
      ACCEPT_TOKEN(anon_sym_west);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 39:
      ACCEPT_TOKEN(anon_sym_up);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 40:
      ACCEPT_TOKEN(anon_sym_down);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 41:
      ACCEPT_TOKEN(anon_sym_northeast);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 42:
      ACCEPT_TOKEN(anon_sym_northwest);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 43:
      ACCEPT_TOKEN(anon_sym_southeast);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 44:
      ACCEPT_TOKEN(anon_sym_southwest);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 45:
      ACCEPT_TOKEN(anon_sym_in);
      if (lookahead == '?') ADVANCE(24);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 46:
      ACCEPT_TOKEN(anon_sym_out);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 47:
      ACCEPT_TOKEN(anon_sym_land);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 48:
      ACCEPT_TOKEN(sym_flag);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 49:
      ACCEPT_TOKEN(anon_sym_enter);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 50:
      ACCEPT_TOKEN(anon_sym_leave);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 51:
      ACCEPT_TOKEN(anon_sym_take);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 52:
      ACCEPT_TOKEN(anon_sym_drop);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 53:
      ACCEPT_TOKEN(anon_sym_examine);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 54:
      ACCEPT_TOKEN(anon_sym_through);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 55:
      ACCEPT_TOKEN(anon_sym_open);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 56:
      ACCEPT_TOKEN(anon_sym_close);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 57:
      ACCEPT_TOKEN(anon_sym_lock);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 58:
      ACCEPT_TOKEN(anon_sym_unlock);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 59:
      ACCEPT_TOKEN(anon_sym_read);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 60:
      ACCEPT_TOKEN(anon_sym_turn_DASHon);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 61:
      ACCEPT_TOKEN(anon_sym_turn_DASHoff);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 62:
      ACCEPT_TOKEN(anon_sym_attack);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 63:
      ACCEPT_TOKEN(anon_sym_eat);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 64:
      ACCEPT_TOKEN(anon_sym_drink);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 65:
      ACCEPT_TOKEN(anon_sym_wear);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 66:
      ACCEPT_TOKEN(anon_sym_remove);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 67:
      ACCEPT_TOKEN(anon_sym_push);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 68:
      ACCEPT_TOKEN(anon_sym_pull);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 69:
      ACCEPT_TOKEN(anon_sym_climb);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 70:
      ACCEPT_TOKEN(anon_sym_smell);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 71:
      ACCEPT_TOKEN(anon_sym_listen);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 72:
      ACCEPT_TOKEN(anon_sym_touch);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 73:
      ACCEPT_TOKEN(sym_unknown);
      END_STATE();
    case 74:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == '!') ADVANCE(28);
      if (lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 75:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == '!') ADVANCE(26);
      if (lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 76:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == '!') ADVANCE(27);
      if (lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 77:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == '-') ADVANCE(232);
      if (lookahead == '!' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 78:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == '-') ADVANCE(307);
      if (lookahead == '!' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 79:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == '-') ADVANCE(320);
      if (lookahead == '!' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 80:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == '-') ADVANCE(294);
      if (lookahead == '!' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 81:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == '-') ADVANCE(233);
      if (lookahead == '!' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 82:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == '-') ADVANCE(198);
      if (lookahead == '!' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 83:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == '-') ADVANCE(234);
      if (lookahead == '!' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 84:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == '-') ADVANCE(308);
      if (lookahead == '!' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 85:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == '?') ADVANCE(23);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 86:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == '?') ADVANCE(25);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 87:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'A') ADVANCE(99);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('B' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 88:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'A') ADVANCE(133);
      if (lookahead == 'O') ADVANCE(166);
      if (lookahead == 'R') ADVANCE(96);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('B' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 89:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'A') ADVANCE(133);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('B' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 90:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'A') ADVANCE(106);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('B' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 91:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'A') ADVANCE(139);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('B' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 92:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'A') ADVANCE(103);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('B' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 93:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'A') ADVANCE(98);
      if (lookahead == 'B') ADVANCE(131);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('C' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 94:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'A') ADVANCE(152);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('B' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 95:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'A') ADVANCE(154);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('B' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 96:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'A') ADVANCE(147);
      if (lookahead == 'Y') ADVANCE(165);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('B' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 97:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'B') ADVANCE(99);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 98:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'B') ADVANCE(137);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 99:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'B') ADVANCE(131);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 100:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'C') ADVANCE(162);
      if (lookahead == 'N') ADVANCE(48);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 101:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'C') ADVANCE(99);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 102:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'C') ADVANCE(122);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 103:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'C') ADVANCE(110);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 104:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'C') ADVANCE(134);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 105:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'D') ADVANCE(48);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 106:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'D') ADVANCE(99);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 107:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'D') ADVANCE(113);
      if (lookahead == 'O') ADVANCE(87);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 108:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'E') ADVANCE(48);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 109:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'E') ADVANCE(168);
      if (lookahead == 'O') ADVANCE(150);
      if (lookahead == 'R') ADVANCE(126);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 110:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'E') ADVANCE(99);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 111:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'E') ADVANCE(155);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 112:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'E') ADVANCE(122);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 113:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'E') ADVANCE(159);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 114:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'E') ADVANCE(105);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 115:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'E') ADVANCE(90);
      if (lookahead == 'M') ADVANCE(167);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 116:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'E') ADVANCE(143);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 117:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'E') ADVANCE(95);
      if (lookahead == 'U') ADVANCE(153);
      if (lookahead == 'W') ADVANCE(127);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 118:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'E') ADVANCE(94);
      if (lookahead == 'O') ADVANCE(156);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 119:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'F') ADVANCE(92);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 120:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'G') ADVANCE(99);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 121:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'G') ADVANCE(123);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 122:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'H') ADVANCE(99);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 123:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'H') ADVANCE(163);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 124:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'I') ADVANCE(121);
      if (lookahead == 'O') ADVANCE(104);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 125:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'I') ADVANCE(138);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 126:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'I') ADVANCE(146);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 127:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'I') ADVANCE(164);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 128:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'I') ADVANCE(103);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 129:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'I') ADVANCE(98);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 130:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'I') ADVANCE(160);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 131:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'I') ADVANCE(161);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 132:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'K') ADVANCE(99);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 133:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'K') ADVANCE(110);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 134:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'K') ADVANCE(114);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 135:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'L') ADVANCE(125);
      if (lookahead == 'O') ADVANCE(144);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 136:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'L') ADVANCE(91);
      if (lookahead == 'O') ADVANCE(149);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 137:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'L') ADVANCE(108);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 138:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'M') ADVANCE(97);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 139:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'M') ADVANCE(110);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 140:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'N') ADVANCE(48);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 141:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'N') ADVANCE(99);
      if (lookahead == 'P') ADVANCE(116);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 142:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'N') ADVANCE(99);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 143:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'N') ADVANCE(93);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 144:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'N') ADVANCE(163);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 145:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'N') ADVANCE(120);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 146:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'N') ADVANCE(132);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 147:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'N') ADVANCE(157);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 148:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'N') ADVANCE(169);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 149:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'O') ADVANCE(106);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 150:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'O') ADVANCE(152);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 151:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'O') ADVANCE(140);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 152:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'R') ADVANCE(99);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 153:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'R') ADVANCE(119);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 154:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'R') ADVANCE(102);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 155:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'R') ADVANCE(158);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 156:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'R') ADVANCE(142);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 157:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'S') ADVANCE(99);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 158:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'S') ADVANCE(151);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 159:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'S') ADVANCE(101);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 160:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'S') ADVANCE(129);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 161:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'T') ADVANCE(48);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 162:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'T') ADVANCE(150);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 163:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'T') ADVANCE(99);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 164:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'T') ADVANCE(102);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 165:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'T') ADVANCE(89);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 166:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'U') ADVANCE(102);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 167:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'U') ADVANCE(145);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 168:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'V') ADVANCE(128);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 169:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'V') ADVANCE(130);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 170:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(321);
      if (lookahead == 'l') ADVANCE(221);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 171:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(322);
      if (lookahead == 'n') ADVANCE(344);
      if (lookahead == 'q') ADVANCE(85);
      if (lookahead == 'x') ADVANCE(177);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 172:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(274);
      if (lookahead == 'i') ADVANCE(317);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 173:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(258);
      if (lookahead == 'e') ADVANCE(266);
      if (lookahead == 'h') ADVANCE(311);
      if (lookahead == 'o') ADVANCE(352);
      if (lookahead == 'r') ADVANCE(353);
      if (lookahead == 'u') ADVANCE(312);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 174:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(284);
      if (lookahead == 'e') ADVANCE(186);
      if (lookahead == 'i') ADVANCE(323);
      if (lookahead == 'o') ADVANCE(194);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 175:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(319);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 176:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(360);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 177:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(276);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 178:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(236);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 179:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(237);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 180:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(202);
      if (lookahead == 'm') ADVANCE(303);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 181:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(238);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 182:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(309);
      if (lookahead == 's') ADVANCE(334);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 183:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(318);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 184:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(262);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 185:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(195);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 186:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(357);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 187:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(285);
      if (lookahead == 'e') ADVANCE(180);
      if (lookahead == 'o') ADVANCE(296);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 188:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(327);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 189:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'a') ADVANCE(329);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('b' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 190:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'b') ADVANCE(253);
      if (lookahead == 'p') ADVANCE(222);
      if (lookahead == 'r') ADVANCE(21);
      if (lookahead == 'u') ADVANCE(332);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 191:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'b') ADVANCE(69);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 192:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'b') ADVANCE(184);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 193:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'b') ADVANCE(273);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 194:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'c') ADVANCE(254);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 195:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'c') ADVANCE(256);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 196:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'c') ADVANCE(244);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 197:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'c') ADVANCE(257);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 198:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'c') ADVANCE(246);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 199:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'c') ADVANCE(335);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 200:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'd') ADVANCE(20);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 201:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'd') ADVANCE(47);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 202:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'd') ADVANCE(59);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 203:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'd') ADVANCE(11);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 204:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'd') ADVANCE(31);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 205:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'd') ADVANCE(298);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 206:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(229);
      if (lookahead == 'o') ADVANCE(359);
      if (lookahead == 'r') ADVANCE(248);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 207:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(361);
      if (lookahead == 'o') ADVANCE(316);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 208:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(182);
      if (lookahead == 'o') ADVANCE(313);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 209:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(17);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 210:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(74);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 211:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(51);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 212:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(18);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 213:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(56);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 214:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(19);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 215:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(50);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 216:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(66);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 217:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(53);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 218:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(16);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 219:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(331);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 220:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(199);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 221:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(183);
      if (lookahead == 'i') ADVANCE(275);
      if (lookahead == 'o') ADVANCE(324);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 222:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(282);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 223:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(348);
      if (lookahead == 'm') ADVANCE(226);
      if (lookahead == 'o') ADVANCE(354);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 224:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(310);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 225:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(283);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 226:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(271);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 227:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(328);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 228:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'e') ADVANCE(330);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 229:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'f') ADVANCE(240);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 230:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'f') ADVANCE(61);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 231:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'f') ADVANCE(230);
      if (lookahead == 'n') ADVANCE(60);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 232:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'f') ADVANCE(267);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 233:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'f') ADVANCE(270);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 234:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'f') ADVANCE(272);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 235:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'g') ADVANCE(32);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 236:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'g') ADVANCE(86);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 237:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'g') ADVANCE(75);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 238:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'g') ADVANCE(76);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 239:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'g') ADVANCE(245);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 240:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'g') ADVANCE(268);
      if (lookahead == 'r') ADVANCE(301);
      if (lookahead == 's') ADVANCE(362);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 241:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'h') ADVANCE(67);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 242:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'h') ADVANCE(35);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 243:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'h') ADVANCE(36);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 244:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'h') ADVANCE(72);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 245:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'h') ADVANCE(54);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 246:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'h') ADVANCE(251);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 247:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'i') ADVANCE(193);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 248:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'i') ADVANCE(287);
      if (lookahead == 'o') ADVANCE(304);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 249:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'i') ADVANCE(290);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 250:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'i') ADVANCE(289);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 251:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'i') ADVANCE(269);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 252:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'i') ADVANCE(291);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 253:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'j') ADVANCE(220);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 254:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'k') ADVANCE(57);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 255:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'k') ADVANCE(64);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 256:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'k') ADVANCE(62);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 257:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'k') ADVANCE(58);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 258:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'k') ADVANCE(211);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 259:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(68);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 260:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(29);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 261:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(70);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 262:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(15);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 263:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(302);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 264:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(259);
      if (lookahead == 's') ADVANCE(241);
      if (lookahead == 't') ADVANCE(84);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 265:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(203);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 266:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(260);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 267:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(178);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 268:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(295);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 269:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(204);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 270:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(179);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 271:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(261);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 272:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(181);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 273:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(250);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 274:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'l') ADVANCE(325);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 275:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'm') ADVANCE(191);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 276:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'm') ADVANCE(249);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 277:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'm') ADVANCE(12);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 278:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'm') ADVANCE(30);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 279:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'n') ADVANCE(200);
      if (lookahead == 't') ADVANCE(343);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 280:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'n') ADVANCE(45);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 281:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'n') ADVANCE(40);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 282:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'n') ADVANCE(55);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 283:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'n') ADVANCE(71);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 284:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'n') ADVANCE(201);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 285:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'n') ADVANCE(205);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 286:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'n') ADVANCE(263);
      if (lookahead == 'p') ADVANCE(39);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 287:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'n') ADVANCE(255);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 288:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'n') ADVANCE(80);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 289:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'n') ADVANCE(235);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 290:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'n') ADVANCE(217);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 291:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'n') ADVANCE(218);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 292:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'n') ADVANCE(346);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 293:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'o') ADVANCE(356);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 294:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'o') ADVANCE(231);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 295:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'o') ADVANCE(192);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 296:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'o') ADVANCE(277);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 297:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'o') ADVANCE(305);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 298:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'o') ADVANCE(278);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 299:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'o') ADVANCE(306);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 300:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'o') ADVANCE(351);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 301:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'o') ADVANCE(355);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 302:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'o') ADVANCE(197);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 303:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'o') ADVANCE(358);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 304:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'p') ADVANCE(52);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 305:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'p') ADVANCE(33);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 306:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'p') ADVANCE(34);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 307:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'p') ADVANCE(314);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 308:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'p') ADVANCE(315);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 309:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'r') ADVANCE(65);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 310:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'r') ADVANCE(49);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 311:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'r') ADVANCE(300);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 312:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'r') ADVANCE(288);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 313:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'r') ADVANCE(265);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 314:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'r') ADVANCE(297);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 315:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'r') ADVANCE(299);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 316:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'r') ADVANCE(340);
      if (lookahead == 't') ADVANCE(22);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 317:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'r') ADVANCE(326);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 318:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'r') ADVANCE(83);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 319:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 's') ADVANCE(77);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 320:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 's') ADVANCE(247);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 321:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 's') ADVANCE(209);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 322:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 's') ADVANCE(333);
      if (lookahead == 't') ADVANCE(63);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 323:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 's') ADVANCE(347);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 324:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 's') ADVANCE(213);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 325:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 's') ADVANCE(214);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 326:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 's') ADVANCE(345);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 327:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 's') ADVANCE(336);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 328:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 's') ADVANCE(337);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 329:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 's') ADVANCE(338);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 330:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 's') ADVANCE(339);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 331:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(78);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 332:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(46);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 333:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(37);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 334:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(38);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 335:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(13);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 336:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(41);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 337:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(42);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 338:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(43);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 339:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(44);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 340:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(242);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 341:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(79);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 342:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(243);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 343:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(185);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 344:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(224);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 345:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(82);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 346:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(176);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 347:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(225);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 348:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(81);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 349:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 't') ADVANCE(252);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 350:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'u') ADVANCE(264);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 351:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'u') ADVANCE(239);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 352:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'u') ADVANCE(196);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 353:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'u') ADVANCE(212);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 354:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'u') ADVANCE(342);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 355:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'u') ADVANCE(349);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 356:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'v') ADVANCE(210);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 357:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'v') ADVANCE(215);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 358:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'v') ADVANCE(216);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 359:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'w') ADVANCE(281);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 360:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'x') ADVANCE(14);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 361:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'x') ADVANCE(341);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 362:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == 'y') ADVANCE(292);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 363:
      ACCEPT_TOKEN(sym_identifier);
      if (lookahead == '!' ||
          lookahead == '-' ||
          ('0' <= lookahead && lookahead <= '9') ||
          lookahead == '?' ||
          ('A' <= lookahead && lookahead <= 'Z') ||
          lookahead == '_' ||
          ('a' <= lookahead && lookahead <= 'z')) ADVANCE(363);
      END_STATE();
    case 364:
      ACCEPT_TOKEN(anon_sym_DQUOTE);
      END_STATE();
    case 365:
      ACCEPT_TOKEN(aux_sym_string_token1);
      if (lookahead == ';') ADVANCE(6);
      if (('\t' <= lookahead && lookahead <= '\r') ||
          lookahead == ' ') ADVANCE(365);
      if (lookahead != 0 &&
          lookahead != '"' &&
          lookahead != '\\') ADVANCE(366);
      END_STATE();
    case 366:
      ACCEPT_TOKEN(aux_sym_string_token1);
      if (lookahead != 0 &&
          lookahead != '"' &&
          lookahead != '\\') ADVANCE(366);
      END_STATE();
    case 367:
      ACCEPT_TOKEN(anon_sym_BSLASH);
      END_STATE();
    case 368:
      ACCEPT_TOKEN(aux_sym_string_token2);
      END_STATE();
    case 369:
      ACCEPT_TOKEN(aux_sym_string_token2);
      if (lookahead == ';') ADVANCE(7);
      if (lookahead == '\t' ||
          (0x0b <= lookahead && lookahead <= '\r') ||
          lookahead == ' ') ADVANCE(369);
      if (lookahead != 0 &&
          (lookahead < '\t' || '\r' < lookahead)) ADVANCE(368);
      END_STATE();
    case 370:
      ACCEPT_TOKEN(sym_number);
      if (('0' <= lookahead && lookahead <= '9')) ADVANCE(370);
      END_STATE();
    default:
      return false;
  }
}

static const TSLexMode ts_lex_modes[STATE_COUNT] = {
  [0] = {.lex_state = 0},
  [1] = {.lex_state = 0},
  [2] = {.lex_state = 0},
  [3] = {.lex_state = 0},
  [4] = {.lex_state = 0},
  [5] = {.lex_state = 0},
  [6] = {.lex_state = 0},
  [7] = {.lex_state = 0},
  [8] = {.lex_state = 0},
  [9] = {.lex_state = 0},
  [10] = {.lex_state = 0},
  [11] = {.lex_state = 0},
  [12] = {.lex_state = 0},
  [13] = {.lex_state = 0},
  [14] = {.lex_state = 0},
  [15] = {.lex_state = 2},
  [16] = {.lex_state = 2},
  [17] = {.lex_state = 2},
  [18] = {.lex_state = 2},
  [19] = {.lex_state = 0},
  [20] = {.lex_state = 1},
};

static const uint16_t ts_parse_table[LARGE_STATE_COUNT][SYMBOL_COUNT] = {
  [0] = {
    [ts_builtin_sym_end] = ACTIONS(1),
    [sym_comment] = ACTIONS(3),
    [anon_sym_LPAREN] = ACTIONS(1),
    [anon_sym_RPAREN] = ACTIONS(1),
    [sym_keyword] = ACTIONS(1),
    [anon_sym_world] = ACTIONS(1),
    [anon_sym_room] = ACTIONS(1),
    [anon_sym_object] = ACTIONS(1),
    [anon_sym_defsyntax] = ACTIONS(1),
    [anon_sym_defglobal] = ACTIONS(1),
    [anon_sym_defroutine] = ACTIONS(1),
    [anon_sym_case] = ACTIONS(1),
    [anon_sym_true] = ACTIONS(1),
    [anon_sym_false] = ACTIONS(1),
    [anon_sym_and] = ACTIONS(1),
    [anon_sym_or] = ACTIONS(1),
    [anon_sym_not] = ACTIONS(1),
    [anon_sym_eq_QMARK] = ACTIONS(1),
    [anon_sym_in_QMARK] = ACTIONS(1),
    [anon_sym_has_DASHflag_QMARK] = ACTIONS(1),
    [anon_sym_set_DASHflag_BANG] = ACTIONS(1),
    [anon_sym_clear_DASHflag_BANG] = ACTIONS(1),
    [anon_sym_move_BANG] = ACTIONS(1),
    [anon_sym_tell] = ACTIONS(1),
    [anon_sym_random] = ACTIONS(1),
    [anon_sym_first_DASHchild] = ACTIONS(1),
    [anon_sym_next_DASHsibling] = ACTIONS(1),
    [anon_sym_get_DASHprop] = ACTIONS(1),
    [anon_sym_put_DASHprop] = ACTIONS(1),
    [anon_sym_north] = ACTIONS(1),
    [anon_sym_south] = ACTIONS(1),
    [anon_sym_east] = ACTIONS(1),
    [anon_sym_west] = ACTIONS(1),
    [anon_sym_up] = ACTIONS(1),
    [anon_sym_down] = ACTIONS(1),
    [anon_sym_northeast] = ACTIONS(1),
    [anon_sym_northwest] = ACTIONS(1),
    [anon_sym_southeast] = ACTIONS(1),
    [anon_sym_southwest] = ACTIONS(1),
    [anon_sym_in] = ACTIONS(1),
    [anon_sym_out] = ACTIONS(1),
    [anon_sym_land] = ACTIONS(1),
    [sym_flag] = ACTIONS(1),
    [anon_sym_enter] = ACTIONS(1),
    [anon_sym_leave] = ACTIONS(1),
    [anon_sym_take] = ACTIONS(1),
    [anon_sym_drop] = ACTIONS(1),
    [anon_sym_examine] = ACTIONS(1),
    [anon_sym_through] = ACTIONS(1),
    [anon_sym_open] = ACTIONS(1),
    [anon_sym_close] = ACTIONS(1),
    [anon_sym_lock] = ACTIONS(1),
    [anon_sym_unlock] = ACTIONS(1),
    [anon_sym_read] = ACTIONS(1),
    [anon_sym_turn_DASHon] = ACTIONS(1),
    [anon_sym_turn_DASHoff] = ACTIONS(1),
    [anon_sym_attack] = ACTIONS(1),
    [anon_sym_eat] = ACTIONS(1),
    [anon_sym_drink] = ACTIONS(1),
    [anon_sym_wear] = ACTIONS(1),
    [anon_sym_remove] = ACTIONS(1),
    [anon_sym_push] = ACTIONS(1),
    [anon_sym_pull] = ACTIONS(1),
    [anon_sym_climb] = ACTIONS(1),
    [anon_sym_smell] = ACTIONS(1),
    [anon_sym_listen] = ACTIONS(1),
    [anon_sym_touch] = ACTIONS(1),
    [sym_unknown] = ACTIONS(1),
    [sym_identifier] = ACTIONS(1),
    [anon_sym_DQUOTE] = ACTIONS(1),
    [anon_sym_BSLASH] = ACTIONS(1),
    [sym_number] = ACTIONS(1),
  },
  [1] = {
    [sym_source_file] = STATE(19),
    [sym__form] = STATE(3),
    [sym_list] = STATE(3),
    [sym_symbol] = STATE(3),
    [sym_defform] = STATE(10),
    [sym_builtin] = STATE(10),
    [sym_direction] = STATE(10),
    [sym_behavior_name] = STATE(10),
    [sym_string] = STATE(3),
    [aux_sym_source_file_repeat1] = STATE(3),
    [ts_builtin_sym_end] = ACTIONS(5),
    [sym_comment] = ACTIONS(3),
    [anon_sym_LPAREN] = ACTIONS(7),
    [sym_keyword] = ACTIONS(9),
    [anon_sym_world] = ACTIONS(11),
    [anon_sym_room] = ACTIONS(11),
    [anon_sym_object] = ACTIONS(11),
    [anon_sym_defsyntax] = ACTIONS(11),
    [anon_sym_defglobal] = ACTIONS(11),
    [anon_sym_defroutine] = ACTIONS(11),
    [anon_sym_case] = ACTIONS(13),
    [anon_sym_true] = ACTIONS(13),
    [anon_sym_false] = ACTIONS(13),
    [anon_sym_and] = ACTIONS(13),
    [anon_sym_or] = ACTIONS(13),
    [anon_sym_not] = ACTIONS(13),
    [anon_sym_eq_QMARK] = ACTIONS(13),
    [anon_sym_in_QMARK] = ACTIONS(13),
    [anon_sym_has_DASHflag_QMARK] = ACTIONS(13),
    [anon_sym_set_DASHflag_BANG] = ACTIONS(13),
    [anon_sym_clear_DASHflag_BANG] = ACTIONS(13),
    [anon_sym_move_BANG] = ACTIONS(13),
    [anon_sym_tell] = ACTIONS(13),
    [anon_sym_random] = ACTIONS(13),
    [anon_sym_first_DASHchild] = ACTIONS(13),
    [anon_sym_next_DASHsibling] = ACTIONS(13),
    [anon_sym_get_DASHprop] = ACTIONS(13),
    [anon_sym_put_DASHprop] = ACTIONS(13),
    [anon_sym_north] = ACTIONS(15),
    [anon_sym_south] = ACTIONS(15),
    [anon_sym_east] = ACTIONS(15),
    [anon_sym_west] = ACTIONS(15),
    [anon_sym_up] = ACTIONS(15),
    [anon_sym_down] = ACTIONS(15),
    [anon_sym_northeast] = ACTIONS(15),
    [anon_sym_northwest] = ACTIONS(15),
    [anon_sym_southeast] = ACTIONS(15),
    [anon_sym_southwest] = ACTIONS(15),
    [anon_sym_in] = ACTIONS(15),
    [anon_sym_out] = ACTIONS(15),
    [anon_sym_land] = ACTIONS(15),
    [sym_flag] = ACTIONS(17),
    [anon_sym_enter] = ACTIONS(19),
    [anon_sym_leave] = ACTIONS(19),
    [anon_sym_take] = ACTIONS(19),
    [anon_sym_drop] = ACTIONS(19),
    [anon_sym_examine] = ACTIONS(19),
    [anon_sym_through] = ACTIONS(19),
    [anon_sym_open] = ACTIONS(19),
    [anon_sym_close] = ACTIONS(19),
    [anon_sym_lock] = ACTIONS(19),
    [anon_sym_unlock] = ACTIONS(19),
    [anon_sym_read] = ACTIONS(19),
    [anon_sym_turn_DASHon] = ACTIONS(19),
    [anon_sym_turn_DASHoff] = ACTIONS(19),
    [anon_sym_attack] = ACTIONS(19),
    [anon_sym_eat] = ACTIONS(19),
    [anon_sym_drink] = ACTIONS(19),
    [anon_sym_wear] = ACTIONS(19),
    [anon_sym_remove] = ACTIONS(19),
    [anon_sym_push] = ACTIONS(19),
    [anon_sym_pull] = ACTIONS(19),
    [anon_sym_climb] = ACTIONS(19),
    [anon_sym_smell] = ACTIONS(19),
    [anon_sym_listen] = ACTIONS(19),
    [anon_sym_touch] = ACTIONS(19),
    [sym_unknown] = ACTIONS(21),
    [sym_identifier] = ACTIONS(17),
    [anon_sym_DQUOTE] = ACTIONS(23),
    [sym_number] = ACTIONS(9),
  },
  [2] = {
    [sym__form] = STATE(2),
    [sym_list] = STATE(2),
    [sym_symbol] = STATE(2),
    [sym_defform] = STATE(10),
    [sym_builtin] = STATE(10),
    [sym_direction] = STATE(10),
    [sym_behavior_name] = STATE(10),
    [sym_string] = STATE(2),
    [aux_sym_source_file_repeat1] = STATE(2),
    [ts_builtin_sym_end] = ACTIONS(25),
    [sym_comment] = ACTIONS(3),
    [anon_sym_LPAREN] = ACTIONS(27),
    [anon_sym_RPAREN] = ACTIONS(25),
    [sym_keyword] = ACTIONS(30),
    [anon_sym_world] = ACTIONS(33),
    [anon_sym_room] = ACTIONS(33),
    [anon_sym_object] = ACTIONS(33),
    [anon_sym_defsyntax] = ACTIONS(33),
    [anon_sym_defglobal] = ACTIONS(33),
    [anon_sym_defroutine] = ACTIONS(33),
    [anon_sym_case] = ACTIONS(36),
    [anon_sym_true] = ACTIONS(36),
    [anon_sym_false] = ACTIONS(36),
    [anon_sym_and] = ACTIONS(36),
    [anon_sym_or] = ACTIONS(36),
    [anon_sym_not] = ACTIONS(36),
    [anon_sym_eq_QMARK] = ACTIONS(36),
    [anon_sym_in_QMARK] = ACTIONS(36),
    [anon_sym_has_DASHflag_QMARK] = ACTIONS(36),
    [anon_sym_set_DASHflag_BANG] = ACTIONS(36),
    [anon_sym_clear_DASHflag_BANG] = ACTIONS(36),
    [anon_sym_move_BANG] = ACTIONS(36),
    [anon_sym_tell] = ACTIONS(36),
    [anon_sym_random] = ACTIONS(36),
    [anon_sym_first_DASHchild] = ACTIONS(36),
    [anon_sym_next_DASHsibling] = ACTIONS(36),
    [anon_sym_get_DASHprop] = ACTIONS(36),
    [anon_sym_put_DASHprop] = ACTIONS(36),
    [anon_sym_north] = ACTIONS(39),
    [anon_sym_south] = ACTIONS(39),
    [anon_sym_east] = ACTIONS(39),
    [anon_sym_west] = ACTIONS(39),
    [anon_sym_up] = ACTIONS(39),
    [anon_sym_down] = ACTIONS(39),
    [anon_sym_northeast] = ACTIONS(39),
    [anon_sym_northwest] = ACTIONS(39),
    [anon_sym_southeast] = ACTIONS(39),
    [anon_sym_southwest] = ACTIONS(39),
    [anon_sym_in] = ACTIONS(39),
    [anon_sym_out] = ACTIONS(39),
    [anon_sym_land] = ACTIONS(39),
    [sym_flag] = ACTIONS(42),
    [anon_sym_enter] = ACTIONS(45),
    [anon_sym_leave] = ACTIONS(45),
    [anon_sym_take] = ACTIONS(45),
    [anon_sym_drop] = ACTIONS(45),
    [anon_sym_examine] = ACTIONS(45),
    [anon_sym_through] = ACTIONS(45),
    [anon_sym_open] = ACTIONS(45),
    [anon_sym_close] = ACTIONS(45),
    [anon_sym_lock] = ACTIONS(45),
    [anon_sym_unlock] = ACTIONS(45),
    [anon_sym_read] = ACTIONS(45),
    [anon_sym_turn_DASHon] = ACTIONS(45),
    [anon_sym_turn_DASHoff] = ACTIONS(45),
    [anon_sym_attack] = ACTIONS(45),
    [anon_sym_eat] = ACTIONS(45),
    [anon_sym_drink] = ACTIONS(45),
    [anon_sym_wear] = ACTIONS(45),
    [anon_sym_remove] = ACTIONS(45),
    [anon_sym_push] = ACTIONS(45),
    [anon_sym_pull] = ACTIONS(45),
    [anon_sym_climb] = ACTIONS(45),
    [anon_sym_smell] = ACTIONS(45),
    [anon_sym_listen] = ACTIONS(45),
    [anon_sym_touch] = ACTIONS(45),
    [sym_unknown] = ACTIONS(48),
    [sym_identifier] = ACTIONS(42),
    [anon_sym_DQUOTE] = ACTIONS(51),
    [sym_number] = ACTIONS(30),
  },
  [3] = {
    [sym__form] = STATE(2),
    [sym_list] = STATE(2),
    [sym_symbol] = STATE(2),
    [sym_defform] = STATE(10),
    [sym_builtin] = STATE(10),
    [sym_direction] = STATE(10),
    [sym_behavior_name] = STATE(10),
    [sym_string] = STATE(2),
    [aux_sym_source_file_repeat1] = STATE(2),
    [ts_builtin_sym_end] = ACTIONS(54),
    [sym_comment] = ACTIONS(3),
    [anon_sym_LPAREN] = ACTIONS(7),
    [sym_keyword] = ACTIONS(56),
    [anon_sym_world] = ACTIONS(11),
    [anon_sym_room] = ACTIONS(11),
    [anon_sym_object] = ACTIONS(11),
    [anon_sym_defsyntax] = ACTIONS(11),
    [anon_sym_defglobal] = ACTIONS(11),
    [anon_sym_defroutine] = ACTIONS(11),
    [anon_sym_case] = ACTIONS(13),
    [anon_sym_true] = ACTIONS(13),
    [anon_sym_false] = ACTIONS(13),
    [anon_sym_and] = ACTIONS(13),
    [anon_sym_or] = ACTIONS(13),
    [anon_sym_not] = ACTIONS(13),
    [anon_sym_eq_QMARK] = ACTIONS(13),
    [anon_sym_in_QMARK] = ACTIONS(13),
    [anon_sym_has_DASHflag_QMARK] = ACTIONS(13),
    [anon_sym_set_DASHflag_BANG] = ACTIONS(13),
    [anon_sym_clear_DASHflag_BANG] = ACTIONS(13),
    [anon_sym_move_BANG] = ACTIONS(13),
    [anon_sym_tell] = ACTIONS(13),
    [anon_sym_random] = ACTIONS(13),
    [anon_sym_first_DASHchild] = ACTIONS(13),
    [anon_sym_next_DASHsibling] = ACTIONS(13),
    [anon_sym_get_DASHprop] = ACTIONS(13),
    [anon_sym_put_DASHprop] = ACTIONS(13),
    [anon_sym_north] = ACTIONS(15),
    [anon_sym_south] = ACTIONS(15),
    [anon_sym_east] = ACTIONS(15),
    [anon_sym_west] = ACTIONS(15),
    [anon_sym_up] = ACTIONS(15),
    [anon_sym_down] = ACTIONS(15),
    [anon_sym_northeast] = ACTIONS(15),
    [anon_sym_northwest] = ACTIONS(15),
    [anon_sym_southeast] = ACTIONS(15),
    [anon_sym_southwest] = ACTIONS(15),
    [anon_sym_in] = ACTIONS(15),
    [anon_sym_out] = ACTIONS(15),
    [anon_sym_land] = ACTIONS(15),
    [sym_flag] = ACTIONS(17),
    [anon_sym_enter] = ACTIONS(19),
    [anon_sym_leave] = ACTIONS(19),
    [anon_sym_take] = ACTIONS(19),
    [anon_sym_drop] = ACTIONS(19),
    [anon_sym_examine] = ACTIONS(19),
    [anon_sym_through] = ACTIONS(19),
    [anon_sym_open] = ACTIONS(19),
    [anon_sym_close] = ACTIONS(19),
    [anon_sym_lock] = ACTIONS(19),
    [anon_sym_unlock] = ACTIONS(19),
    [anon_sym_read] = ACTIONS(19),
    [anon_sym_turn_DASHon] = ACTIONS(19),
    [anon_sym_turn_DASHoff] = ACTIONS(19),
    [anon_sym_attack] = ACTIONS(19),
    [anon_sym_eat] = ACTIONS(19),
    [anon_sym_drink] = ACTIONS(19),
    [anon_sym_wear] = ACTIONS(19),
    [anon_sym_remove] = ACTIONS(19),
    [anon_sym_push] = ACTIONS(19),
    [anon_sym_pull] = ACTIONS(19),
    [anon_sym_climb] = ACTIONS(19),
    [anon_sym_smell] = ACTIONS(19),
    [anon_sym_listen] = ACTIONS(19),
    [anon_sym_touch] = ACTIONS(19),
    [sym_unknown] = ACTIONS(21),
    [sym_identifier] = ACTIONS(17),
    [anon_sym_DQUOTE] = ACTIONS(23),
    [sym_number] = ACTIONS(56),
  },
  [4] = {
    [sym__form] = STATE(5),
    [sym_list] = STATE(5),
    [sym_symbol] = STATE(5),
    [sym_defform] = STATE(10),
    [sym_builtin] = STATE(10),
    [sym_direction] = STATE(10),
    [sym_behavior_name] = STATE(10),
    [sym_string] = STATE(5),
    [aux_sym_source_file_repeat1] = STATE(5),
    [sym_comment] = ACTIONS(3),
    [anon_sym_LPAREN] = ACTIONS(7),
    [anon_sym_RPAREN] = ACTIONS(58),
    [sym_keyword] = ACTIONS(60),
    [anon_sym_world] = ACTIONS(11),
    [anon_sym_room] = ACTIONS(11),
    [anon_sym_object] = ACTIONS(11),
    [anon_sym_defsyntax] = ACTIONS(11),
    [anon_sym_defglobal] = ACTIONS(11),
    [anon_sym_defroutine] = ACTIONS(11),
    [anon_sym_case] = ACTIONS(13),
    [anon_sym_true] = ACTIONS(13),
    [anon_sym_false] = ACTIONS(13),
    [anon_sym_and] = ACTIONS(13),
    [anon_sym_or] = ACTIONS(13),
    [anon_sym_not] = ACTIONS(13),
    [anon_sym_eq_QMARK] = ACTIONS(13),
    [anon_sym_in_QMARK] = ACTIONS(13),
    [anon_sym_has_DASHflag_QMARK] = ACTIONS(13),
    [anon_sym_set_DASHflag_BANG] = ACTIONS(13),
    [anon_sym_clear_DASHflag_BANG] = ACTIONS(13),
    [anon_sym_move_BANG] = ACTIONS(13),
    [anon_sym_tell] = ACTIONS(13),
    [anon_sym_random] = ACTIONS(13),
    [anon_sym_first_DASHchild] = ACTIONS(13),
    [anon_sym_next_DASHsibling] = ACTIONS(13),
    [anon_sym_get_DASHprop] = ACTIONS(13),
    [anon_sym_put_DASHprop] = ACTIONS(13),
    [anon_sym_north] = ACTIONS(15),
    [anon_sym_south] = ACTIONS(15),
    [anon_sym_east] = ACTIONS(15),
    [anon_sym_west] = ACTIONS(15),
    [anon_sym_up] = ACTIONS(15),
    [anon_sym_down] = ACTIONS(15),
    [anon_sym_northeast] = ACTIONS(15),
    [anon_sym_northwest] = ACTIONS(15),
    [anon_sym_southeast] = ACTIONS(15),
    [anon_sym_southwest] = ACTIONS(15),
    [anon_sym_in] = ACTIONS(15),
    [anon_sym_out] = ACTIONS(15),
    [anon_sym_land] = ACTIONS(15),
    [sym_flag] = ACTIONS(17),
    [anon_sym_enter] = ACTIONS(19),
    [anon_sym_leave] = ACTIONS(19),
    [anon_sym_take] = ACTIONS(19),
    [anon_sym_drop] = ACTIONS(19),
    [anon_sym_examine] = ACTIONS(19),
    [anon_sym_through] = ACTIONS(19),
    [anon_sym_open] = ACTIONS(19),
    [anon_sym_close] = ACTIONS(19),
    [anon_sym_lock] = ACTIONS(19),
    [anon_sym_unlock] = ACTIONS(19),
    [anon_sym_read] = ACTIONS(19),
    [anon_sym_turn_DASHon] = ACTIONS(19),
    [anon_sym_turn_DASHoff] = ACTIONS(19),
    [anon_sym_attack] = ACTIONS(19),
    [anon_sym_eat] = ACTIONS(19),
    [anon_sym_drink] = ACTIONS(19),
    [anon_sym_wear] = ACTIONS(19),
    [anon_sym_remove] = ACTIONS(19),
    [anon_sym_push] = ACTIONS(19),
    [anon_sym_pull] = ACTIONS(19),
    [anon_sym_climb] = ACTIONS(19),
    [anon_sym_smell] = ACTIONS(19),
    [anon_sym_listen] = ACTIONS(19),
    [anon_sym_touch] = ACTIONS(19),
    [sym_unknown] = ACTIONS(21),
    [sym_identifier] = ACTIONS(17),
    [anon_sym_DQUOTE] = ACTIONS(23),
    [sym_number] = ACTIONS(60),
  },
  [5] = {
    [sym__form] = STATE(2),
    [sym_list] = STATE(2),
    [sym_symbol] = STATE(2),
    [sym_defform] = STATE(10),
    [sym_builtin] = STATE(10),
    [sym_direction] = STATE(10),
    [sym_behavior_name] = STATE(10),
    [sym_string] = STATE(2),
    [aux_sym_source_file_repeat1] = STATE(2),
    [sym_comment] = ACTIONS(3),
    [anon_sym_LPAREN] = ACTIONS(7),
    [anon_sym_RPAREN] = ACTIONS(62),
    [sym_keyword] = ACTIONS(56),
    [anon_sym_world] = ACTIONS(11),
    [anon_sym_room] = ACTIONS(11),
    [anon_sym_object] = ACTIONS(11),
    [anon_sym_defsyntax] = ACTIONS(11),
    [anon_sym_defglobal] = ACTIONS(11),
    [anon_sym_defroutine] = ACTIONS(11),
    [anon_sym_case] = ACTIONS(13),
    [anon_sym_true] = ACTIONS(13),
    [anon_sym_false] = ACTIONS(13),
    [anon_sym_and] = ACTIONS(13),
    [anon_sym_or] = ACTIONS(13),
    [anon_sym_not] = ACTIONS(13),
    [anon_sym_eq_QMARK] = ACTIONS(13),
    [anon_sym_in_QMARK] = ACTIONS(13),
    [anon_sym_has_DASHflag_QMARK] = ACTIONS(13),
    [anon_sym_set_DASHflag_BANG] = ACTIONS(13),
    [anon_sym_clear_DASHflag_BANG] = ACTIONS(13),
    [anon_sym_move_BANG] = ACTIONS(13),
    [anon_sym_tell] = ACTIONS(13),
    [anon_sym_random] = ACTIONS(13),
    [anon_sym_first_DASHchild] = ACTIONS(13),
    [anon_sym_next_DASHsibling] = ACTIONS(13),
    [anon_sym_get_DASHprop] = ACTIONS(13),
    [anon_sym_put_DASHprop] = ACTIONS(13),
    [anon_sym_north] = ACTIONS(15),
    [anon_sym_south] = ACTIONS(15),
    [anon_sym_east] = ACTIONS(15),
    [anon_sym_west] = ACTIONS(15),
    [anon_sym_up] = ACTIONS(15),
    [anon_sym_down] = ACTIONS(15),
    [anon_sym_northeast] = ACTIONS(15),
    [anon_sym_northwest] = ACTIONS(15),
    [anon_sym_southeast] = ACTIONS(15),
    [anon_sym_southwest] = ACTIONS(15),
    [anon_sym_in] = ACTIONS(15),
    [anon_sym_out] = ACTIONS(15),
    [anon_sym_land] = ACTIONS(15),
    [sym_flag] = ACTIONS(17),
    [anon_sym_enter] = ACTIONS(19),
    [anon_sym_leave] = ACTIONS(19),
    [anon_sym_take] = ACTIONS(19),
    [anon_sym_drop] = ACTIONS(19),
    [anon_sym_examine] = ACTIONS(19),
    [anon_sym_through] = ACTIONS(19),
    [anon_sym_open] = ACTIONS(19),
    [anon_sym_close] = ACTIONS(19),
    [anon_sym_lock] = ACTIONS(19),
    [anon_sym_unlock] = ACTIONS(19),
    [anon_sym_read] = ACTIONS(19),
    [anon_sym_turn_DASHon] = ACTIONS(19),
    [anon_sym_turn_DASHoff] = ACTIONS(19),
    [anon_sym_attack] = ACTIONS(19),
    [anon_sym_eat] = ACTIONS(19),
    [anon_sym_drink] = ACTIONS(19),
    [anon_sym_wear] = ACTIONS(19),
    [anon_sym_remove] = ACTIONS(19),
    [anon_sym_push] = ACTIONS(19),
    [anon_sym_pull] = ACTIONS(19),
    [anon_sym_climb] = ACTIONS(19),
    [anon_sym_smell] = ACTIONS(19),
    [anon_sym_listen] = ACTIONS(19),
    [anon_sym_touch] = ACTIONS(19),
    [sym_unknown] = ACTIONS(21),
    [sym_identifier] = ACTIONS(17),
    [anon_sym_DQUOTE] = ACTIONS(23),
    [sym_number] = ACTIONS(56),
  },
  [6] = {
    [ts_builtin_sym_end] = ACTIONS(64),
    [sym_comment] = ACTIONS(3),
    [anon_sym_LPAREN] = ACTIONS(64),
    [anon_sym_RPAREN] = ACTIONS(64),
    [sym_keyword] = ACTIONS(64),
    [anon_sym_world] = ACTIONS(66),
    [anon_sym_room] = ACTIONS(66),
    [anon_sym_object] = ACTIONS(66),
    [anon_sym_defsyntax] = ACTIONS(66),
    [anon_sym_defglobal] = ACTIONS(66),
    [anon_sym_defroutine] = ACTIONS(66),
    [anon_sym_case] = ACTIONS(66),
    [anon_sym_true] = ACTIONS(66),
    [anon_sym_false] = ACTIONS(66),
    [anon_sym_and] = ACTIONS(66),
    [anon_sym_or] = ACTIONS(66),
    [anon_sym_not] = ACTIONS(66),
    [anon_sym_eq_QMARK] = ACTIONS(66),
    [anon_sym_in_QMARK] = ACTIONS(66),
    [anon_sym_has_DASHflag_QMARK] = ACTIONS(66),
    [anon_sym_set_DASHflag_BANG] = ACTIONS(66),
    [anon_sym_clear_DASHflag_BANG] = ACTIONS(66),
    [anon_sym_move_BANG] = ACTIONS(66),
    [anon_sym_tell] = ACTIONS(66),
    [anon_sym_random] = ACTIONS(66),
    [anon_sym_first_DASHchild] = ACTIONS(66),
    [anon_sym_next_DASHsibling] = ACTIONS(66),
    [anon_sym_get_DASHprop] = ACTIONS(66),
    [anon_sym_put_DASHprop] = ACTIONS(66),
    [anon_sym_north] = ACTIONS(66),
    [anon_sym_south] = ACTIONS(66),
    [anon_sym_east] = ACTIONS(66),
    [anon_sym_west] = ACTIONS(66),
    [anon_sym_up] = ACTIONS(66),
    [anon_sym_down] = ACTIONS(66),
    [anon_sym_northeast] = ACTIONS(66),
    [anon_sym_northwest] = ACTIONS(66),
    [anon_sym_southeast] = ACTIONS(66),
    [anon_sym_southwest] = ACTIONS(66),
    [anon_sym_in] = ACTIONS(66),
    [anon_sym_out] = ACTIONS(66),
    [anon_sym_land] = ACTIONS(66),
    [sym_flag] = ACTIONS(66),
    [anon_sym_enter] = ACTIONS(66),
    [anon_sym_leave] = ACTIONS(66),
    [anon_sym_take] = ACTIONS(66),
    [anon_sym_drop] = ACTIONS(66),
    [anon_sym_examine] = ACTIONS(66),
    [anon_sym_through] = ACTIONS(66),
    [anon_sym_open] = ACTIONS(66),
    [anon_sym_close] = ACTIONS(66),
    [anon_sym_lock] = ACTIONS(66),
    [anon_sym_unlock] = ACTIONS(66),
    [anon_sym_read] = ACTIONS(66),
    [anon_sym_turn_DASHon] = ACTIONS(66),
    [anon_sym_turn_DASHoff] = ACTIONS(66),
    [anon_sym_attack] = ACTIONS(66),
    [anon_sym_eat] = ACTIONS(66),
    [anon_sym_drink] = ACTIONS(66),
    [anon_sym_wear] = ACTIONS(66),
    [anon_sym_remove] = ACTIONS(66),
    [anon_sym_push] = ACTIONS(66),
    [anon_sym_pull] = ACTIONS(66),
    [anon_sym_climb] = ACTIONS(66),
    [anon_sym_smell] = ACTIONS(66),
    [anon_sym_listen] = ACTIONS(66),
    [anon_sym_touch] = ACTIONS(66),
    [sym_unknown] = ACTIONS(64),
    [sym_identifier] = ACTIONS(66),
    [anon_sym_DQUOTE] = ACTIONS(64),
    [sym_number] = ACTIONS(64),
  },
  [7] = {
    [ts_builtin_sym_end] = ACTIONS(68),
    [sym_comment] = ACTIONS(3),
    [anon_sym_LPAREN] = ACTIONS(68),
    [anon_sym_RPAREN] = ACTIONS(68),
    [sym_keyword] = ACTIONS(68),
    [anon_sym_world] = ACTIONS(70),
    [anon_sym_room] = ACTIONS(70),
    [anon_sym_object] = ACTIONS(70),
    [anon_sym_defsyntax] = ACTIONS(70),
    [anon_sym_defglobal] = ACTIONS(70),
    [anon_sym_defroutine] = ACTIONS(70),
    [anon_sym_case] = ACTIONS(70),
    [anon_sym_true] = ACTIONS(70),
    [anon_sym_false] = ACTIONS(70),
    [anon_sym_and] = ACTIONS(70),
    [anon_sym_or] = ACTIONS(70),
    [anon_sym_not] = ACTIONS(70),
    [anon_sym_eq_QMARK] = ACTIONS(70),
    [anon_sym_in_QMARK] = ACTIONS(70),
    [anon_sym_has_DASHflag_QMARK] = ACTIONS(70),
    [anon_sym_set_DASHflag_BANG] = ACTIONS(70),
    [anon_sym_clear_DASHflag_BANG] = ACTIONS(70),
    [anon_sym_move_BANG] = ACTIONS(70),
    [anon_sym_tell] = ACTIONS(70),
    [anon_sym_random] = ACTIONS(70),
    [anon_sym_first_DASHchild] = ACTIONS(70),
    [anon_sym_next_DASHsibling] = ACTIONS(70),
    [anon_sym_get_DASHprop] = ACTIONS(70),
    [anon_sym_put_DASHprop] = ACTIONS(70),
    [anon_sym_north] = ACTIONS(70),
    [anon_sym_south] = ACTIONS(70),
    [anon_sym_east] = ACTIONS(70),
    [anon_sym_west] = ACTIONS(70),
    [anon_sym_up] = ACTIONS(70),
    [anon_sym_down] = ACTIONS(70),
    [anon_sym_northeast] = ACTIONS(70),
    [anon_sym_northwest] = ACTIONS(70),
    [anon_sym_southeast] = ACTIONS(70),
    [anon_sym_southwest] = ACTIONS(70),
    [anon_sym_in] = ACTIONS(70),
    [anon_sym_out] = ACTIONS(70),
    [anon_sym_land] = ACTIONS(70),
    [sym_flag] = ACTIONS(70),
    [anon_sym_enter] = ACTIONS(70),
    [anon_sym_leave] = ACTIONS(70),
    [anon_sym_take] = ACTIONS(70),
    [anon_sym_drop] = ACTIONS(70),
    [anon_sym_examine] = ACTIONS(70),
    [anon_sym_through] = ACTIONS(70),
    [anon_sym_open] = ACTIONS(70),
    [anon_sym_close] = ACTIONS(70),
    [anon_sym_lock] = ACTIONS(70),
    [anon_sym_unlock] = ACTIONS(70),
    [anon_sym_read] = ACTIONS(70),
    [anon_sym_turn_DASHon] = ACTIONS(70),
    [anon_sym_turn_DASHoff] = ACTIONS(70),
    [anon_sym_attack] = ACTIONS(70),
    [anon_sym_eat] = ACTIONS(70),
    [anon_sym_drink] = ACTIONS(70),
    [anon_sym_wear] = ACTIONS(70),
    [anon_sym_remove] = ACTIONS(70),
    [anon_sym_push] = ACTIONS(70),
    [anon_sym_pull] = ACTIONS(70),
    [anon_sym_climb] = ACTIONS(70),
    [anon_sym_smell] = ACTIONS(70),
    [anon_sym_listen] = ACTIONS(70),
    [anon_sym_touch] = ACTIONS(70),
    [sym_unknown] = ACTIONS(68),
    [sym_identifier] = ACTIONS(70),
    [anon_sym_DQUOTE] = ACTIONS(68),
    [sym_number] = ACTIONS(68),
  },
  [8] = {
    [ts_builtin_sym_end] = ACTIONS(72),
    [sym_comment] = ACTIONS(3),
    [anon_sym_LPAREN] = ACTIONS(72),
    [anon_sym_RPAREN] = ACTIONS(72),
    [sym_keyword] = ACTIONS(72),
    [anon_sym_world] = ACTIONS(74),
    [anon_sym_room] = ACTIONS(74),
    [anon_sym_object] = ACTIONS(74),
    [anon_sym_defsyntax] = ACTIONS(74),
    [anon_sym_defglobal] = ACTIONS(74),
    [anon_sym_defroutine] = ACTIONS(74),
    [anon_sym_case] = ACTIONS(74),
    [anon_sym_true] = ACTIONS(74),
    [anon_sym_false] = ACTIONS(74),
    [anon_sym_and] = ACTIONS(74),
    [anon_sym_or] = ACTIONS(74),
    [anon_sym_not] = ACTIONS(74),
    [anon_sym_eq_QMARK] = ACTIONS(74),
    [anon_sym_in_QMARK] = ACTIONS(74),
    [anon_sym_has_DASHflag_QMARK] = ACTIONS(74),
    [anon_sym_set_DASHflag_BANG] = ACTIONS(74),
    [anon_sym_clear_DASHflag_BANG] = ACTIONS(74),
    [anon_sym_move_BANG] = ACTIONS(74),
    [anon_sym_tell] = ACTIONS(74),
    [anon_sym_random] = ACTIONS(74),
    [anon_sym_first_DASHchild] = ACTIONS(74),
    [anon_sym_next_DASHsibling] = ACTIONS(74),
    [anon_sym_get_DASHprop] = ACTIONS(74),
    [anon_sym_put_DASHprop] = ACTIONS(74),
    [anon_sym_north] = ACTIONS(74),
    [anon_sym_south] = ACTIONS(74),
    [anon_sym_east] = ACTIONS(74),
    [anon_sym_west] = ACTIONS(74),
    [anon_sym_up] = ACTIONS(74),
    [anon_sym_down] = ACTIONS(74),
    [anon_sym_northeast] = ACTIONS(74),
    [anon_sym_northwest] = ACTIONS(74),
    [anon_sym_southeast] = ACTIONS(74),
    [anon_sym_southwest] = ACTIONS(74),
    [anon_sym_in] = ACTIONS(74),
    [anon_sym_out] = ACTIONS(74),
    [anon_sym_land] = ACTIONS(74),
    [sym_flag] = ACTIONS(74),
    [anon_sym_enter] = ACTIONS(74),
    [anon_sym_leave] = ACTIONS(74),
    [anon_sym_take] = ACTIONS(74),
    [anon_sym_drop] = ACTIONS(74),
    [anon_sym_examine] = ACTIONS(74),
    [anon_sym_through] = ACTIONS(74),
    [anon_sym_open] = ACTIONS(74),
    [anon_sym_close] = ACTIONS(74),
    [anon_sym_lock] = ACTIONS(74),
    [anon_sym_unlock] = ACTIONS(74),
    [anon_sym_read] = ACTIONS(74),
    [anon_sym_turn_DASHon] = ACTIONS(74),
    [anon_sym_turn_DASHoff] = ACTIONS(74),
    [anon_sym_attack] = ACTIONS(74),
    [anon_sym_eat] = ACTIONS(74),
    [anon_sym_drink] = ACTIONS(74),
    [anon_sym_wear] = ACTIONS(74),
    [anon_sym_remove] = ACTIONS(74),
    [anon_sym_push] = ACTIONS(74),
    [anon_sym_pull] = ACTIONS(74),
    [anon_sym_climb] = ACTIONS(74),
    [anon_sym_smell] = ACTIONS(74),
    [anon_sym_listen] = ACTIONS(74),
    [anon_sym_touch] = ACTIONS(74),
    [sym_unknown] = ACTIONS(72),
    [sym_identifier] = ACTIONS(74),
    [anon_sym_DQUOTE] = ACTIONS(72),
    [sym_number] = ACTIONS(72),
  },
  [9] = {
    [ts_builtin_sym_end] = ACTIONS(76),
    [sym_comment] = ACTIONS(3),
    [anon_sym_LPAREN] = ACTIONS(76),
    [anon_sym_RPAREN] = ACTIONS(76),
    [sym_keyword] = ACTIONS(76),
    [anon_sym_world] = ACTIONS(78),
    [anon_sym_room] = ACTIONS(78),
    [anon_sym_object] = ACTIONS(78),
    [anon_sym_defsyntax] = ACTIONS(78),
    [anon_sym_defglobal] = ACTIONS(78),
    [anon_sym_defroutine] = ACTIONS(78),
    [anon_sym_case] = ACTIONS(78),
    [anon_sym_true] = ACTIONS(78),
    [anon_sym_false] = ACTIONS(78),
    [anon_sym_and] = ACTIONS(78),
    [anon_sym_or] = ACTIONS(78),
    [anon_sym_not] = ACTIONS(78),
    [anon_sym_eq_QMARK] = ACTIONS(78),
    [anon_sym_in_QMARK] = ACTIONS(78),
    [anon_sym_has_DASHflag_QMARK] = ACTIONS(78),
    [anon_sym_set_DASHflag_BANG] = ACTIONS(78),
    [anon_sym_clear_DASHflag_BANG] = ACTIONS(78),
    [anon_sym_move_BANG] = ACTIONS(78),
    [anon_sym_tell] = ACTIONS(78),
    [anon_sym_random] = ACTIONS(78),
    [anon_sym_first_DASHchild] = ACTIONS(78),
    [anon_sym_next_DASHsibling] = ACTIONS(78),
    [anon_sym_get_DASHprop] = ACTIONS(78),
    [anon_sym_put_DASHprop] = ACTIONS(78),
    [anon_sym_north] = ACTIONS(78),
    [anon_sym_south] = ACTIONS(78),
    [anon_sym_east] = ACTIONS(78),
    [anon_sym_west] = ACTIONS(78),
    [anon_sym_up] = ACTIONS(78),
    [anon_sym_down] = ACTIONS(78),
    [anon_sym_northeast] = ACTIONS(78),
    [anon_sym_northwest] = ACTIONS(78),
    [anon_sym_southeast] = ACTIONS(78),
    [anon_sym_southwest] = ACTIONS(78),
    [anon_sym_in] = ACTIONS(78),
    [anon_sym_out] = ACTIONS(78),
    [anon_sym_land] = ACTIONS(78),
    [sym_flag] = ACTIONS(78),
    [anon_sym_enter] = ACTIONS(78),
    [anon_sym_leave] = ACTIONS(78),
    [anon_sym_take] = ACTIONS(78),
    [anon_sym_drop] = ACTIONS(78),
    [anon_sym_examine] = ACTIONS(78),
    [anon_sym_through] = ACTIONS(78),
    [anon_sym_open] = ACTIONS(78),
    [anon_sym_close] = ACTIONS(78),
    [anon_sym_lock] = ACTIONS(78),
    [anon_sym_unlock] = ACTIONS(78),
    [anon_sym_read] = ACTIONS(78),
    [anon_sym_turn_DASHon] = ACTIONS(78),
    [anon_sym_turn_DASHoff] = ACTIONS(78),
    [anon_sym_attack] = ACTIONS(78),
    [anon_sym_eat] = ACTIONS(78),
    [anon_sym_drink] = ACTIONS(78),
    [anon_sym_wear] = ACTIONS(78),
    [anon_sym_remove] = ACTIONS(78),
    [anon_sym_push] = ACTIONS(78),
    [anon_sym_pull] = ACTIONS(78),
    [anon_sym_climb] = ACTIONS(78),
    [anon_sym_smell] = ACTIONS(78),
    [anon_sym_listen] = ACTIONS(78),
    [anon_sym_touch] = ACTIONS(78),
    [sym_unknown] = ACTIONS(76),
    [sym_identifier] = ACTIONS(78),
    [anon_sym_DQUOTE] = ACTIONS(76),
    [sym_number] = ACTIONS(76),
  },
  [10] = {
    [ts_builtin_sym_end] = ACTIONS(80),
    [sym_comment] = ACTIONS(3),
    [anon_sym_LPAREN] = ACTIONS(80),
    [anon_sym_RPAREN] = ACTIONS(80),
    [sym_keyword] = ACTIONS(80),
    [anon_sym_world] = ACTIONS(82),
    [anon_sym_room] = ACTIONS(82),
    [anon_sym_object] = ACTIONS(82),
    [anon_sym_defsyntax] = ACTIONS(82),
    [anon_sym_defglobal] = ACTIONS(82),
    [anon_sym_defroutine] = ACTIONS(82),
    [anon_sym_case] = ACTIONS(82),
    [anon_sym_true] = ACTIONS(82),
    [anon_sym_false] = ACTIONS(82),
    [anon_sym_and] = ACTIONS(82),
    [anon_sym_or] = ACTIONS(82),
    [anon_sym_not] = ACTIONS(82),
    [anon_sym_eq_QMARK] = ACTIONS(82),
    [anon_sym_in_QMARK] = ACTIONS(82),
    [anon_sym_has_DASHflag_QMARK] = ACTIONS(82),
    [anon_sym_set_DASHflag_BANG] = ACTIONS(82),
    [anon_sym_clear_DASHflag_BANG] = ACTIONS(82),
    [anon_sym_move_BANG] = ACTIONS(82),
    [anon_sym_tell] = ACTIONS(82),
    [anon_sym_random] = ACTIONS(82),
    [anon_sym_first_DASHchild] = ACTIONS(82),
    [anon_sym_next_DASHsibling] = ACTIONS(82),
    [anon_sym_get_DASHprop] = ACTIONS(82),
    [anon_sym_put_DASHprop] = ACTIONS(82),
    [anon_sym_north] = ACTIONS(82),
    [anon_sym_south] = ACTIONS(82),
    [anon_sym_east] = ACTIONS(82),
    [anon_sym_west] = ACTIONS(82),
    [anon_sym_up] = ACTIONS(82),
    [anon_sym_down] = ACTIONS(82),
    [anon_sym_northeast] = ACTIONS(82),
    [anon_sym_northwest] = ACTIONS(82),
    [anon_sym_southeast] = ACTIONS(82),
    [anon_sym_southwest] = ACTIONS(82),
    [anon_sym_in] = ACTIONS(82),
    [anon_sym_out] = ACTIONS(82),
    [anon_sym_land] = ACTIONS(82),
    [sym_flag] = ACTIONS(82),
    [anon_sym_enter] = ACTIONS(82),
    [anon_sym_leave] = ACTIONS(82),
    [anon_sym_take] = ACTIONS(82),
    [anon_sym_drop] = ACTIONS(82),
    [anon_sym_examine] = ACTIONS(82),
    [anon_sym_through] = ACTIONS(82),
    [anon_sym_open] = ACTIONS(82),
    [anon_sym_close] = ACTIONS(82),
    [anon_sym_lock] = ACTIONS(82),
    [anon_sym_unlock] = ACTIONS(82),
    [anon_sym_read] = ACTIONS(82),
    [anon_sym_turn_DASHon] = ACTIONS(82),
    [anon_sym_turn_DASHoff] = ACTIONS(82),
    [anon_sym_attack] = ACTIONS(82),
    [anon_sym_eat] = ACTIONS(82),
    [anon_sym_drink] = ACTIONS(82),
    [anon_sym_wear] = ACTIONS(82),
    [anon_sym_remove] = ACTIONS(82),
    [anon_sym_push] = ACTIONS(82),
    [anon_sym_pull] = ACTIONS(82),
    [anon_sym_climb] = ACTIONS(82),
    [anon_sym_smell] = ACTIONS(82),
    [anon_sym_listen] = ACTIONS(82),
    [anon_sym_touch] = ACTIONS(82),
    [sym_unknown] = ACTIONS(80),
    [sym_identifier] = ACTIONS(82),
    [anon_sym_DQUOTE] = ACTIONS(80),
    [sym_number] = ACTIONS(80),
  },
  [11] = {
    [ts_builtin_sym_end] = ACTIONS(84),
    [sym_comment] = ACTIONS(3),
    [anon_sym_LPAREN] = ACTIONS(84),
    [anon_sym_RPAREN] = ACTIONS(84),
    [sym_keyword] = ACTIONS(84),
    [anon_sym_world] = ACTIONS(86),
    [anon_sym_room] = ACTIONS(86),
    [anon_sym_object] = ACTIONS(86),
    [anon_sym_defsyntax] = ACTIONS(86),
    [anon_sym_defglobal] = ACTIONS(86),
    [anon_sym_defroutine] = ACTIONS(86),
    [anon_sym_case] = ACTIONS(86),
    [anon_sym_true] = ACTIONS(86),
    [anon_sym_false] = ACTIONS(86),
    [anon_sym_and] = ACTIONS(86),
    [anon_sym_or] = ACTIONS(86),
    [anon_sym_not] = ACTIONS(86),
    [anon_sym_eq_QMARK] = ACTIONS(86),
    [anon_sym_in_QMARK] = ACTIONS(86),
    [anon_sym_has_DASHflag_QMARK] = ACTIONS(86),
    [anon_sym_set_DASHflag_BANG] = ACTIONS(86),
    [anon_sym_clear_DASHflag_BANG] = ACTIONS(86),
    [anon_sym_move_BANG] = ACTIONS(86),
    [anon_sym_tell] = ACTIONS(86),
    [anon_sym_random] = ACTIONS(86),
    [anon_sym_first_DASHchild] = ACTIONS(86),
    [anon_sym_next_DASHsibling] = ACTIONS(86),
    [anon_sym_get_DASHprop] = ACTIONS(86),
    [anon_sym_put_DASHprop] = ACTIONS(86),
    [anon_sym_north] = ACTIONS(86),
    [anon_sym_south] = ACTIONS(86),
    [anon_sym_east] = ACTIONS(86),
    [anon_sym_west] = ACTIONS(86),
    [anon_sym_up] = ACTIONS(86),
    [anon_sym_down] = ACTIONS(86),
    [anon_sym_northeast] = ACTIONS(86),
    [anon_sym_northwest] = ACTIONS(86),
    [anon_sym_southeast] = ACTIONS(86),
    [anon_sym_southwest] = ACTIONS(86),
    [anon_sym_in] = ACTIONS(86),
    [anon_sym_out] = ACTIONS(86),
    [anon_sym_land] = ACTIONS(86),
    [sym_flag] = ACTIONS(86),
    [anon_sym_enter] = ACTIONS(86),
    [anon_sym_leave] = ACTIONS(86),
    [anon_sym_take] = ACTIONS(86),
    [anon_sym_drop] = ACTIONS(86),
    [anon_sym_examine] = ACTIONS(86),
    [anon_sym_through] = ACTIONS(86),
    [anon_sym_open] = ACTIONS(86),
    [anon_sym_close] = ACTIONS(86),
    [anon_sym_lock] = ACTIONS(86),
    [anon_sym_unlock] = ACTIONS(86),
    [anon_sym_read] = ACTIONS(86),
    [anon_sym_turn_DASHon] = ACTIONS(86),
    [anon_sym_turn_DASHoff] = ACTIONS(86),
    [anon_sym_attack] = ACTIONS(86),
    [anon_sym_eat] = ACTIONS(86),
    [anon_sym_drink] = ACTIONS(86),
    [anon_sym_wear] = ACTIONS(86),
    [anon_sym_remove] = ACTIONS(86),
    [anon_sym_push] = ACTIONS(86),
    [anon_sym_pull] = ACTIONS(86),
    [anon_sym_climb] = ACTIONS(86),
    [anon_sym_smell] = ACTIONS(86),
    [anon_sym_listen] = ACTIONS(86),
    [anon_sym_touch] = ACTIONS(86),
    [sym_unknown] = ACTIONS(84),
    [sym_identifier] = ACTIONS(86),
    [anon_sym_DQUOTE] = ACTIONS(84),
    [sym_number] = ACTIONS(84),
  },
  [12] = {
    [ts_builtin_sym_end] = ACTIONS(88),
    [sym_comment] = ACTIONS(3),
    [anon_sym_LPAREN] = ACTIONS(88),
    [anon_sym_RPAREN] = ACTIONS(88),
    [sym_keyword] = ACTIONS(88),
    [anon_sym_world] = ACTIONS(90),
    [anon_sym_room] = ACTIONS(90),
    [anon_sym_object] = ACTIONS(90),
    [anon_sym_defsyntax] = ACTIONS(90),
    [anon_sym_defglobal] = ACTIONS(90),
    [anon_sym_defroutine] = ACTIONS(90),
    [anon_sym_case] = ACTIONS(90),
    [anon_sym_true] = ACTIONS(90),
    [anon_sym_false] = ACTIONS(90),
    [anon_sym_and] = ACTIONS(90),
    [anon_sym_or] = ACTIONS(90),
    [anon_sym_not] = ACTIONS(90),
    [anon_sym_eq_QMARK] = ACTIONS(90),
    [anon_sym_in_QMARK] = ACTIONS(90),
    [anon_sym_has_DASHflag_QMARK] = ACTIONS(90),
    [anon_sym_set_DASHflag_BANG] = ACTIONS(90),
    [anon_sym_clear_DASHflag_BANG] = ACTIONS(90),
    [anon_sym_move_BANG] = ACTIONS(90),
    [anon_sym_tell] = ACTIONS(90),
    [anon_sym_random] = ACTIONS(90),
    [anon_sym_first_DASHchild] = ACTIONS(90),
    [anon_sym_next_DASHsibling] = ACTIONS(90),
    [anon_sym_get_DASHprop] = ACTIONS(90),
    [anon_sym_put_DASHprop] = ACTIONS(90),
    [anon_sym_north] = ACTIONS(90),
    [anon_sym_south] = ACTIONS(90),
    [anon_sym_east] = ACTIONS(90),
    [anon_sym_west] = ACTIONS(90),
    [anon_sym_up] = ACTIONS(90),
    [anon_sym_down] = ACTIONS(90),
    [anon_sym_northeast] = ACTIONS(90),
    [anon_sym_northwest] = ACTIONS(90),
    [anon_sym_southeast] = ACTIONS(90),
    [anon_sym_southwest] = ACTIONS(90),
    [anon_sym_in] = ACTIONS(90),
    [anon_sym_out] = ACTIONS(90),
    [anon_sym_land] = ACTIONS(90),
    [sym_flag] = ACTIONS(90),
    [anon_sym_enter] = ACTIONS(90),
    [anon_sym_leave] = ACTIONS(90),
    [anon_sym_take] = ACTIONS(90),
    [anon_sym_drop] = ACTIONS(90),
    [anon_sym_examine] = ACTIONS(90),
    [anon_sym_through] = ACTIONS(90),
    [anon_sym_open] = ACTIONS(90),
    [anon_sym_close] = ACTIONS(90),
    [anon_sym_lock] = ACTIONS(90),
    [anon_sym_unlock] = ACTIONS(90),
    [anon_sym_read] = ACTIONS(90),
    [anon_sym_turn_DASHon] = ACTIONS(90),
    [anon_sym_turn_DASHoff] = ACTIONS(90),
    [anon_sym_attack] = ACTIONS(90),
    [anon_sym_eat] = ACTIONS(90),
    [anon_sym_drink] = ACTIONS(90),
    [anon_sym_wear] = ACTIONS(90),
    [anon_sym_remove] = ACTIONS(90),
    [anon_sym_push] = ACTIONS(90),
    [anon_sym_pull] = ACTIONS(90),
    [anon_sym_climb] = ACTIONS(90),
    [anon_sym_smell] = ACTIONS(90),
    [anon_sym_listen] = ACTIONS(90),
    [anon_sym_touch] = ACTIONS(90),
    [sym_unknown] = ACTIONS(88),
    [sym_identifier] = ACTIONS(90),
    [anon_sym_DQUOTE] = ACTIONS(88),
    [sym_number] = ACTIONS(88),
  },
  [13] = {
    [ts_builtin_sym_end] = ACTIONS(92),
    [sym_comment] = ACTIONS(3),
    [anon_sym_LPAREN] = ACTIONS(92),
    [anon_sym_RPAREN] = ACTIONS(92),
    [sym_keyword] = ACTIONS(92),
    [anon_sym_world] = ACTIONS(94),
    [anon_sym_room] = ACTIONS(94),
    [anon_sym_object] = ACTIONS(94),
    [anon_sym_defsyntax] = ACTIONS(94),
    [anon_sym_defglobal] = ACTIONS(94),
    [anon_sym_defroutine] = ACTIONS(94),
    [anon_sym_case] = ACTIONS(94),
    [anon_sym_true] = ACTIONS(94),
    [anon_sym_false] = ACTIONS(94),
    [anon_sym_and] = ACTIONS(94),
    [anon_sym_or] = ACTIONS(94),
    [anon_sym_not] = ACTIONS(94),
    [anon_sym_eq_QMARK] = ACTIONS(94),
    [anon_sym_in_QMARK] = ACTIONS(94),
    [anon_sym_has_DASHflag_QMARK] = ACTIONS(94),
    [anon_sym_set_DASHflag_BANG] = ACTIONS(94),
    [anon_sym_clear_DASHflag_BANG] = ACTIONS(94),
    [anon_sym_move_BANG] = ACTIONS(94),
    [anon_sym_tell] = ACTIONS(94),
    [anon_sym_random] = ACTIONS(94),
    [anon_sym_first_DASHchild] = ACTIONS(94),
    [anon_sym_next_DASHsibling] = ACTIONS(94),
    [anon_sym_get_DASHprop] = ACTIONS(94),
    [anon_sym_put_DASHprop] = ACTIONS(94),
    [anon_sym_north] = ACTIONS(94),
    [anon_sym_south] = ACTIONS(94),
    [anon_sym_east] = ACTIONS(94),
    [anon_sym_west] = ACTIONS(94),
    [anon_sym_up] = ACTIONS(94),
    [anon_sym_down] = ACTIONS(94),
    [anon_sym_northeast] = ACTIONS(94),
    [anon_sym_northwest] = ACTIONS(94),
    [anon_sym_southeast] = ACTIONS(94),
    [anon_sym_southwest] = ACTIONS(94),
    [anon_sym_in] = ACTIONS(94),
    [anon_sym_out] = ACTIONS(94),
    [anon_sym_land] = ACTIONS(94),
    [sym_flag] = ACTIONS(94),
    [anon_sym_enter] = ACTIONS(94),
    [anon_sym_leave] = ACTIONS(94),
    [anon_sym_take] = ACTIONS(94),
    [anon_sym_drop] = ACTIONS(94),
    [anon_sym_examine] = ACTIONS(94),
    [anon_sym_through] = ACTIONS(94),
    [anon_sym_open] = ACTIONS(94),
    [anon_sym_close] = ACTIONS(94),
    [anon_sym_lock] = ACTIONS(94),
    [anon_sym_unlock] = ACTIONS(94),
    [anon_sym_read] = ACTIONS(94),
    [anon_sym_turn_DASHon] = ACTIONS(94),
    [anon_sym_turn_DASHoff] = ACTIONS(94),
    [anon_sym_attack] = ACTIONS(94),
    [anon_sym_eat] = ACTIONS(94),
    [anon_sym_drink] = ACTIONS(94),
    [anon_sym_wear] = ACTIONS(94),
    [anon_sym_remove] = ACTIONS(94),
    [anon_sym_push] = ACTIONS(94),
    [anon_sym_pull] = ACTIONS(94),
    [anon_sym_climb] = ACTIONS(94),
    [anon_sym_smell] = ACTIONS(94),
    [anon_sym_listen] = ACTIONS(94),
    [anon_sym_touch] = ACTIONS(94),
    [sym_unknown] = ACTIONS(92),
    [sym_identifier] = ACTIONS(94),
    [anon_sym_DQUOTE] = ACTIONS(92),
    [sym_number] = ACTIONS(92),
  },
  [14] = {
    [ts_builtin_sym_end] = ACTIONS(96),
    [sym_comment] = ACTIONS(3),
    [anon_sym_LPAREN] = ACTIONS(96),
    [anon_sym_RPAREN] = ACTIONS(96),
    [sym_keyword] = ACTIONS(96),
    [anon_sym_world] = ACTIONS(98),
    [anon_sym_room] = ACTIONS(98),
    [anon_sym_object] = ACTIONS(98),
    [anon_sym_defsyntax] = ACTIONS(98),
    [anon_sym_defglobal] = ACTIONS(98),
    [anon_sym_defroutine] = ACTIONS(98),
    [anon_sym_case] = ACTIONS(98),
    [anon_sym_true] = ACTIONS(98),
    [anon_sym_false] = ACTIONS(98),
    [anon_sym_and] = ACTIONS(98),
    [anon_sym_or] = ACTIONS(98),
    [anon_sym_not] = ACTIONS(98),
    [anon_sym_eq_QMARK] = ACTIONS(98),
    [anon_sym_in_QMARK] = ACTIONS(98),
    [anon_sym_has_DASHflag_QMARK] = ACTIONS(98),
    [anon_sym_set_DASHflag_BANG] = ACTIONS(98),
    [anon_sym_clear_DASHflag_BANG] = ACTIONS(98),
    [anon_sym_move_BANG] = ACTIONS(98),
    [anon_sym_tell] = ACTIONS(98),
    [anon_sym_random] = ACTIONS(98),
    [anon_sym_first_DASHchild] = ACTIONS(98),
    [anon_sym_next_DASHsibling] = ACTIONS(98),
    [anon_sym_get_DASHprop] = ACTIONS(98),
    [anon_sym_put_DASHprop] = ACTIONS(98),
    [anon_sym_north] = ACTIONS(98),
    [anon_sym_south] = ACTIONS(98),
    [anon_sym_east] = ACTIONS(98),
    [anon_sym_west] = ACTIONS(98),
    [anon_sym_up] = ACTIONS(98),
    [anon_sym_down] = ACTIONS(98),
    [anon_sym_northeast] = ACTIONS(98),
    [anon_sym_northwest] = ACTIONS(98),
    [anon_sym_southeast] = ACTIONS(98),
    [anon_sym_southwest] = ACTIONS(98),
    [anon_sym_in] = ACTIONS(98),
    [anon_sym_out] = ACTIONS(98),
    [anon_sym_land] = ACTIONS(98),
    [sym_flag] = ACTIONS(98),
    [anon_sym_enter] = ACTIONS(98),
    [anon_sym_leave] = ACTIONS(98),
    [anon_sym_take] = ACTIONS(98),
    [anon_sym_drop] = ACTIONS(98),
    [anon_sym_examine] = ACTIONS(98),
    [anon_sym_through] = ACTIONS(98),
    [anon_sym_open] = ACTIONS(98),
    [anon_sym_close] = ACTIONS(98),
    [anon_sym_lock] = ACTIONS(98),
    [anon_sym_unlock] = ACTIONS(98),
    [anon_sym_read] = ACTIONS(98),
    [anon_sym_turn_DASHon] = ACTIONS(98),
    [anon_sym_turn_DASHoff] = ACTIONS(98),
    [anon_sym_attack] = ACTIONS(98),
    [anon_sym_eat] = ACTIONS(98),
    [anon_sym_drink] = ACTIONS(98),
    [anon_sym_wear] = ACTIONS(98),
    [anon_sym_remove] = ACTIONS(98),
    [anon_sym_push] = ACTIONS(98),
    [anon_sym_pull] = ACTIONS(98),
    [anon_sym_climb] = ACTIONS(98),
    [anon_sym_smell] = ACTIONS(98),
    [anon_sym_listen] = ACTIONS(98),
    [anon_sym_touch] = ACTIONS(98),
    [sym_unknown] = ACTIONS(96),
    [sym_identifier] = ACTIONS(98),
    [anon_sym_DQUOTE] = ACTIONS(96),
    [sym_number] = ACTIONS(96),
  },
};

static const uint16_t ts_small_parse_table[] = {
  [0] = 5,
    ACTIONS(100), 1,
      sym_comment,
    ACTIONS(102), 1,
      anon_sym_DQUOTE,
    ACTIONS(104), 1,
      aux_sym_string_token1,
    ACTIONS(106), 1,
      anon_sym_BSLASH,
    STATE(16), 1,
      aux_sym_string_repeat1,
  [16] = 5,
    ACTIONS(100), 1,
      sym_comment,
    ACTIONS(106), 1,
      anon_sym_BSLASH,
    ACTIONS(108), 1,
      anon_sym_DQUOTE,
    ACTIONS(110), 1,
      aux_sym_string_token1,
    STATE(17), 1,
      aux_sym_string_repeat1,
  [32] = 5,
    ACTIONS(100), 1,
      sym_comment,
    ACTIONS(112), 1,
      anon_sym_DQUOTE,
    ACTIONS(114), 1,
      aux_sym_string_token1,
    ACTIONS(117), 1,
      anon_sym_BSLASH,
    STATE(17), 1,
      aux_sym_string_repeat1,
  [48] = 2,
    ACTIONS(100), 1,
      sym_comment,
    ACTIONS(112), 3,
      anon_sym_DQUOTE,
      aux_sym_string_token1,
      anon_sym_BSLASH,
  [57] = 2,
    ACTIONS(3), 1,
      sym_comment,
    ACTIONS(120), 1,
      ts_builtin_sym_end,
  [64] = 2,
    ACTIONS(100), 1,
      sym_comment,
    ACTIONS(122), 1,
      aux_sym_string_token2,
};

static const uint32_t ts_small_parse_table_map[] = {
  [SMALL_STATE(15)] = 0,
  [SMALL_STATE(16)] = 16,
  [SMALL_STATE(17)] = 32,
  [SMALL_STATE(18)] = 48,
  [SMALL_STATE(19)] = 57,
  [SMALL_STATE(20)] = 64,
};

static const TSParseActionEntry ts_parse_actions[] = {
  [0] = {.entry = {.count = 0, .reusable = false}},
  [1] = {.entry = {.count = 1, .reusable = false}}, RECOVER(),
  [3] = {.entry = {.count = 1, .reusable = true}}, SHIFT_EXTRA(),
  [5] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_source_file, 0, 0, 0),
  [7] = {.entry = {.count = 1, .reusable = true}}, SHIFT(4),
  [9] = {.entry = {.count = 1, .reusable = true}}, SHIFT(3),
  [11] = {.entry = {.count = 1, .reusable = false}}, SHIFT(8),
  [13] = {.entry = {.count = 1, .reusable = false}}, SHIFT(12),
  [15] = {.entry = {.count = 1, .reusable = false}}, SHIFT(6),
  [17] = {.entry = {.count = 1, .reusable = false}}, SHIFT(10),
  [19] = {.entry = {.count = 1, .reusable = false}}, SHIFT(7),
  [21] = {.entry = {.count = 1, .reusable = true}}, SHIFT(10),
  [23] = {.entry = {.count = 1, .reusable = true}}, SHIFT(15),
  [25] = {.entry = {.count = 1, .reusable = true}}, REDUCE(aux_sym_source_file_repeat1, 2, 0, 0),
  [27] = {.entry = {.count = 2, .reusable = true}}, REDUCE(aux_sym_source_file_repeat1, 2, 0, 0), SHIFT_REPEAT(4),
  [30] = {.entry = {.count = 2, .reusable = true}}, REDUCE(aux_sym_source_file_repeat1, 2, 0, 0), SHIFT_REPEAT(2),
  [33] = {.entry = {.count = 2, .reusable = false}}, REDUCE(aux_sym_source_file_repeat1, 2, 0, 0), SHIFT_REPEAT(8),
  [36] = {.entry = {.count = 2, .reusable = false}}, REDUCE(aux_sym_source_file_repeat1, 2, 0, 0), SHIFT_REPEAT(12),
  [39] = {.entry = {.count = 2, .reusable = false}}, REDUCE(aux_sym_source_file_repeat1, 2, 0, 0), SHIFT_REPEAT(6),
  [42] = {.entry = {.count = 2, .reusable = false}}, REDUCE(aux_sym_source_file_repeat1, 2, 0, 0), SHIFT_REPEAT(10),
  [45] = {.entry = {.count = 2, .reusable = false}}, REDUCE(aux_sym_source_file_repeat1, 2, 0, 0), SHIFT_REPEAT(7),
  [48] = {.entry = {.count = 2, .reusable = true}}, REDUCE(aux_sym_source_file_repeat1, 2, 0, 0), SHIFT_REPEAT(10),
  [51] = {.entry = {.count = 2, .reusable = true}}, REDUCE(aux_sym_source_file_repeat1, 2, 0, 0), SHIFT_REPEAT(15),
  [54] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_source_file, 1, 0, 0),
  [56] = {.entry = {.count = 1, .reusable = true}}, SHIFT(2),
  [58] = {.entry = {.count = 1, .reusable = true}}, SHIFT(9),
  [60] = {.entry = {.count = 1, .reusable = true}}, SHIFT(5),
  [62] = {.entry = {.count = 1, .reusable = true}}, SHIFT(13),
  [64] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_direction, 1, 0, 0),
  [66] = {.entry = {.count = 1, .reusable = false}}, REDUCE(sym_direction, 1, 0, 0),
  [68] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_behavior_name, 1, 0, 0),
  [70] = {.entry = {.count = 1, .reusable = false}}, REDUCE(sym_behavior_name, 1, 0, 0),
  [72] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_defform, 1, 0, 0),
  [74] = {.entry = {.count = 1, .reusable = false}}, REDUCE(sym_defform, 1, 0, 0),
  [76] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_list, 2, 0, 0),
  [78] = {.entry = {.count = 1, .reusable = false}}, REDUCE(sym_list, 2, 0, 0),
  [80] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_symbol, 1, 0, 0),
  [82] = {.entry = {.count = 1, .reusable = false}}, REDUCE(sym_symbol, 1, 0, 0),
  [84] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_string, 2, 0, 0),
  [86] = {.entry = {.count = 1, .reusable = false}}, REDUCE(sym_string, 2, 0, 0),
  [88] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_builtin, 1, 0, 0),
  [90] = {.entry = {.count = 1, .reusable = false}}, REDUCE(sym_builtin, 1, 0, 0),
  [92] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_list, 3, 0, 0),
  [94] = {.entry = {.count = 1, .reusable = false}}, REDUCE(sym_list, 3, 0, 0),
  [96] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_string, 3, 0, 0),
  [98] = {.entry = {.count = 1, .reusable = false}}, REDUCE(sym_string, 3, 0, 0),
  [100] = {.entry = {.count = 1, .reusable = false}}, SHIFT_EXTRA(),
  [102] = {.entry = {.count = 1, .reusable = false}}, SHIFT(11),
  [104] = {.entry = {.count = 1, .reusable = false}}, SHIFT(16),
  [106] = {.entry = {.count = 1, .reusable = false}}, SHIFT(20),
  [108] = {.entry = {.count = 1, .reusable = false}}, SHIFT(14),
  [110] = {.entry = {.count = 1, .reusable = false}}, SHIFT(17),
  [112] = {.entry = {.count = 1, .reusable = false}}, REDUCE(aux_sym_string_repeat1, 2, 0, 0),
  [114] = {.entry = {.count = 2, .reusable = false}}, REDUCE(aux_sym_string_repeat1, 2, 0, 0), SHIFT_REPEAT(17),
  [117] = {.entry = {.count = 2, .reusable = false}}, REDUCE(aux_sym_string_repeat1, 2, 0, 0), SHIFT_REPEAT(20),
  [120] = {.entry = {.count = 1, .reusable = true}},  ACCEPT_INPUT(),
  [122] = {.entry = {.count = 1, .reusable = false}}, SHIFT(18),
};

#ifdef __cplusplus
extern "C" {
#endif
#ifdef TREE_SITTER_HIDE_SYMBOLS
#define TS_PUBLIC
#elif defined(_WIN32)
#define TS_PUBLIC __declspec(dllexport)
#else
#define TS_PUBLIC __attribute__((visibility("default")))
#endif

TS_PUBLIC const TSLanguage *tree_sitter_grue(void) {
  static const TSLanguage language = {
    .version = LANGUAGE_VERSION,
    .symbol_count = SYMBOL_COUNT,
    .alias_count = ALIAS_COUNT,
    .token_count = TOKEN_COUNT,
    .external_token_count = EXTERNAL_TOKEN_COUNT,
    .state_count = STATE_COUNT,
    .large_state_count = LARGE_STATE_COUNT,
    .production_id_count = PRODUCTION_ID_COUNT,
    .field_count = FIELD_COUNT,
    .max_alias_sequence_length = MAX_ALIAS_SEQUENCE_LENGTH,
    .parse_table = &ts_parse_table[0][0],
    .small_parse_table = ts_small_parse_table,
    .small_parse_table_map = ts_small_parse_table_map,
    .parse_actions = ts_parse_actions,
    .symbol_names = ts_symbol_names,
    .symbol_metadata = ts_symbol_metadata,
    .public_symbol_map = ts_symbol_map,
    .alias_map = ts_non_terminal_alias_map,
    .alias_sequences = &ts_alias_sequences[0][0],
    .lex_modes = ts_lex_modes,
    .lex_fn = ts_lex,
    .primary_state_ids = ts_primary_state_ids,
  };
  return &language;
}
#ifdef __cplusplus
}
#endif
