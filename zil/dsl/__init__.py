"""
World DSL - Declarative language for interactive fiction worlds.

This module provides:
- S-expression parser and AST
- Expression evaluation
- Effect execution
- World definition loading
"""

from .sexpr import (
    parse,
    parse_all,
    to_string,
    Symbol,
    Keyword,
    SList,
    SExpr,
    SExprError,
)

from .expr import (
    ExprEvaluator,
    EffectExecutor,
    EvalError,
    WorldState,
    MutableWorldState,
    eval_predicate,
    execute_effect,
)

from .world import (
    WorldDefinition,
    Room,
    Exit,
    Object,
    Action,
    ActionMessages,
    Transition,
    Invariant,
    WinCondition,
    LoseCondition,
    GameMeta,
    WorldParser,
    load_world,
    parse_world,
)

from .runtime import (
    GameState,
    ObjectState,
    GameStateAdapter,
    ActionResult,
    MoveResult,
    Runtime,
)

from .converter import (
    ZILtoDSLConverter,
    ConversionResult,
    convert_zil_to_dsl,
)

__all__ = [
    # S-expression parser
    "parse",
    "parse_all",
    "to_string",
    "Symbol",
    "Keyword",
    "SList",
    "SExpr",
    "SExprError",
    # Expression evaluator
    "ExprEvaluator",
    "EffectExecutor",
    "EvalError",
    "WorldState",
    "MutableWorldState",
    "eval_predicate",
    "execute_effect",
    # World definitions
    "WorldDefinition",
    "Room",
    "Exit",
    "Object",
    "Action",
    "ActionMessages",
    "Transition",
    "Invariant",
    "WinCondition",
    "LoseCondition",
    "GameMeta",
    "WorldParser",
    "load_world",
    "parse_world",
    # Runtime
    "GameState",
    "ObjectState",
    "GameStateAdapter",
    "ActionResult",
    "MoveResult",
    "Runtime",
    # ZIL-to-DSL converter
    "ZILtoDSLConverter",
    "ConversionResult",
    "convert_zil_to_dsl",
]
