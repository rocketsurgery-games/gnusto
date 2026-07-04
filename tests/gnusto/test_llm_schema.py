"""Structured-output schema invariants (gnusto-ntr.30).

The Anthropic structured-output API (strict json_schema mode) rejects the
request unless every `object` sets `additionalProperties` explicitly, and it
rejects an `enum` declared against a nullable union type (`["string","null"]`).
Both bit us live when the default model moved to Sonnet 4.5. These tests walk
AGENT_RESPONSE_SCHEMA so a future edit can't quietly reintroduce either.
"""

from gnusto.llm import AGENT_RESPONSE_SCHEMA


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
