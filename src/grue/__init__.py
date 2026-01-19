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
    EffectInterpreter,
    EffectOutcome,
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
    GrueVictory,
    GrueDefeat,
    GrueEvent,
    load_grue,
    parse_grue,
)

from .runtime import (
    GrueRuntime,
    GameState,
    ObjectState,
    ActionResult,
)

from .converter import (
    ZILtoGRUEConverter,
    convert_zil_to_grue,
    ConversionResult,
    ast_to_zil,
    routine_to_zil,
)

from .test import (
    # Python/pytest testing
    GrueTestHarness,
    GrueTestCase,
    StateSnapshot,
    ActionTrace,
    pytest_harness,
    # DSL-based testing
    TestRunner,
    TestResult,
    TestSuiteResult,
    run_tests,
    run_tests_from_string,
)

from .llm import (
    LLMClient,
    LLMConfig,
    LLMResponse,
    ToolCall,
    GAME_TOOLS,
    get_game_tools,
    GameState,
    ObjectInfo,
    get_game_state,
)

from .llm_player import (
    GameSession,
    play_game,
    render_game_state,
    render_response,
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
    # LLM integration
    "LLMClient",
    "LLMConfig",
    "LLMResponse",
    "ToolCall",
    "GAME_TOOLS",
    "get_game_tools",
    "GameState",
    "ObjectInfo",
    "get_game_state",
    # LLM Player
    "GameSession",
    "play_game",
    "render_game_state",
    "render_response",
]
