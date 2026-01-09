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
