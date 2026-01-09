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
]
