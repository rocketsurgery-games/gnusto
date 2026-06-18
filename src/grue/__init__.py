"""
GRUE - Game Rules and Universe Expressions

A declarative language for defining interactive fiction worlds, designed to be:
- Statically analyzable for winnability, soft-locks, invariants
- LLM-friendly with semantic outcomes instead of canned text
- Expressive enough to represent Infocom-style game complexity
- Extractable from ZIL source with manual refinement

File extension: .grue
"""

from .converter import (
    ConversionResult,
    ZILtoGRUEConverter,
    ast_to_zil,
    convert_zil_to_grue,
    routine_to_zil,
)
from .expr import (
    EffectExecutor,
    EffectInterpreter,
    EffectOutcome,
    EvalError,
    ExprEvaluator,
    MutableWorldState,
    WorldState,
    eval_predicate,
    execute_effect,
)
from .parser import (
    GrueBehavior,
    GrueDefeat,
    GrueEvent,
    GrueExit,
    GrueObject,
    GrueParseError,
    GrueParser,
    GrueRoom,
    GrueVictory,
    GrueWorld,
    load_grue,
    parse_grue,
)
from .render import (
    RenderError,
    assemble_brief,
    asset_base,
    brief_for_variant,
    get_render_spec,
    has_render_spec,
    is_renderable,
    render_keyset,
    render_variants,
    resolve_asset_key,
)
from .runtime import (
    ActionResult,
    GameState,
    GrueRuntime,
    ObjectState,
)
from .sexpr import (
    Keyword,
    SExpr,
    SExprError,
    SList,
    Symbol,
    parse,
    parse_all,
    to_string,
)
from .test import (
    ActionTrace,
    GrueTestCase,
    # Python/pytest testing
    GrueTestHarness,
    StateSnapshot,
    TestResult,
    # DSL-based testing
    TestRunner,
    TestSuiteResult,
    pytest_harness,
    run_tests,
    run_tests_from_string,
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
    "EffectInterpreter",
    "EffectOutcome",
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
    "GrueVictory",
    "GrueDefeat",
    "GrueEvent",
    "load_grue",
    "parse_grue",
    # Runtime
    "GrueRuntime",
    "GameState",
    "ObjectState",
    "ActionResult",
    # Converter
    "ZILtoGRUEConverter",
    "convert_zil_to_grue",
    "ConversionResult",
    "ast_to_zil",
    "routine_to_zil",
    # Testing (grue.test package)
    "GrueTestHarness",
    "GrueTestCase",
    "StateSnapshot",
    "ActionTrace",
    "pytest_harness",
    "TestRunner",
    "TestResult",
    "TestSuiteResult",
    "run_tests",
    "run_tests_from_string",
    # Render specs & briefs (variant model)
    "RenderError",
    "asset_base",
    "is_renderable",
    "resolve_asset_key",
    "render_variants",
    "render_keyset",
    "brief_for_variant",
    "assemble_brief",
    "has_render_spec",
    "get_render_spec",
]
