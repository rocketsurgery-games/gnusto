"""Structured-output schema invariants (gnusto-ntr.30).

The Anthropic structured-output API (strict json_schema mode) rejects the
request unless every `object` sets `additionalProperties` explicitly, and it
rejects an `enum` declared against a nullable union type (`["string","null"]`).
Both bit us live when the default model moved to Sonnet 4.5. These tests walk
AGENT_RESPONSE_SCHEMA so a future edit can't quietly reintroduce either.
"""

from typing import get_args

from gnusto.llm import AGENT_RESPONSE_SCHEMA, ActionRequest


def _tool_enum():
    """The `tool` enum from the actions array in AGENT_RESPONSE_SCHEMA."""
    props = AGENT_RESPONSE_SCHEMA["properties"]["actions"]["items"]["properties"]
    return props["tool"]["enum"]


def _walk(node):
    """Yield every dict node in the schema tree."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def test_every_object_sets_additional_properties():
    for node in _walk(AGENT_RESPONSE_SCHEMA):
        if node.get("type") == "object":
            assert "additionalProperties" in node, (
                f"object schema missing additionalProperties: {node.get('properties', node)}"
            )


def test_enums_use_scalar_string_type():
    for node in _walk(AGENT_RESPONSE_SCHEMA):
        if "enum" in node:
            # A nullable union type alongside an enum is rejected by the API.
            assert node.get("type") == "string", (
                f"enum field must declare a scalar string type, got {node.get('type')!r}"
            )
            assert None not in node["enum"], "enum must not include null"


def test_tool_enum_matches_action_request_literal():
    """Every ActionRequest tool must be emittable via the schema enum (gnusto-0bf7.7).

    The structured-output decoder is constrained to the enum, so any tool the
    code supports but the enum omits is silently unreachable -- e.g. 'look'
    collapsed to 'wait' ('Time passes.') because it was missing here.
    """
    supported = set(get_args(ActionRequest.__annotations__["tool"]))
    enum = set(_tool_enum())
    assert supported == enum, (
        f"tool enum drifted from ActionRequest.tool; "
        f"missing from enum: {supported - enum}, extra in enum: {enum - supported}"
    )


def test_look_is_emittable():
    """Explicit guard for the 'look' regression (gnusto-0bf7.7)."""
    assert "look" in _tool_enum()
