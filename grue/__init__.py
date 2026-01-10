"""
GRUE - Game Rules and Universe Expressions

A declarative language for defining interactive fiction worlds, designed to be:
- Statically analyzable for winnability, soft-locks, invariants
- LLM-friendly with semantic outcomes instead of canned text
- Expressive enough to represent Infocom-style game complexity
- Extractable from ZIL source with manual refinement

File extension: .grue
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

from .parser import (
    GrueParser,
    GrueParseError,
    GrueWorld,
    GrueRoom,
    GrueObject,
    GrueExit,
    GrueBehavior,
    GrueCase,
    GrueVictory,
    GrueDefeat,
    load_grue,
    parse_grue,
)

from .runtime import (
    GrueRuntime,
    GameState,
    ObjectState,
    ActionResult,
    GrueStateAdapter,
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
    # World parser
    "GrueParser",
    "GrueParseError",
    "GrueWorld",
    "GrueRoom",
    "GrueObject",
    "GrueExit",
    "GrueBehavior",
    "GrueCase",
    "GrueVictory",
    "GrueDefeat",
    "load_grue",
    "parse_grue",
    # Runtime
    "GrueRuntime",
    "GameState",
    "ObjectState",
    "ActionResult",
    "GrueStateAdapter",
]
