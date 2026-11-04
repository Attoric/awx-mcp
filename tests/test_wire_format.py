# SPDX-License-Identifier: Apache-2.0

"""Wire-format contract for tool results.

Every tool returns a JSON string. Left to the SDK defaults, a ``-> str`` tool is
given an auto-generated ``{"result": string}`` outputSchema and the same JSON is
sent twice: once as the text content block and once, escaped, as
``structuredContent.result``. The registration decorators pass
``structured_output=False`` so each result is sent once, and ``to_json`` drops
pretty-printing whitespace that would otherwise be pure token cost.
"""

import json
from unittest.mock import patch

import anyio

from awx_mcp import server
from awx_mcp.tools import inventories as inventories_mod
from awx_mcp.utils import to_json
from tests.conftest import fake_client_factory


def test_no_tool_advertises_an_output_schema():
    tools = anyio.run(server.mcp.list_tools)
    assert tools
    with_schema = [t.name for t in tools if t.output_schema]
    assert with_schema == []


def test_call_result_has_text_only_no_structured_duplicate(fake_client):
    fake_client.request.return_value = {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [{"id": 1, "name": "웹서버"}],
    }
    with patch.object(
        inventories_mod, "get_ansible_client", new=fake_client_factory(fake_client)
    ):
        result = anyio.run(server.mcp.call_tool, "list_inventories", {})

    assert result.structured_content is None
    assert len(result.content) == 1
    text = result.content[0].text
    assert json.loads(text)["results"][0]["name"] == "웹서버"
    # compact: no pretty-print newlines/indentation, non-ASCII kept readable
    assert "\n" not in text
    assert "웹서버" in text


def test_to_json_is_compact_and_unicode_preserving():
    assert to_json({"a": [1, 2], "b": "ü"}) == '{"a":[1,2],"b":"ü"}'


def _null_default_type_mismatches(schema: dict) -> list[str]:
    bad = []
    for name, prop in schema.get("properties", {}).items():
        if "default" in prop and prop["default"] is None:
            types = {prop.get("type")} | {
                alt.get("type") for alt in prop.get("anyOf", [])
            }
            if "null" not in types:
                bad.append(name)
    return bad


_JSON_PARAMS = {
    "extra_vars",
    "survey_spec",
    "source_vars",
    "variables",
    "extra_data",
}


def _schema_types(prop: dict) -> set[str]:
    types = {prop.get("type")} if prop.get("type") else set()
    for alt in prop.get("anyOf", []) + prop.get("oneOf", []):
        if alt.get("type"):
            types.add(alt["type"])
    types.discard(None)
    return {t for t in types if t is not None}


def test_json_params_advertise_string_object_array():
    tools = anyio.run(server.mcp.list_tools)
    mismatches = {}
    for tool in tools:
        for name, prop in tool.input_schema.get("properties", {}).items():
            if name in _JSON_PARAMS:
                types = _schema_types(prop)
                if not {"string", "object", "array"} <= types:
                    mismatches[f"{tool.name}.{name}"] = sorted(types)
    assert mismatches == {}


def test_every_null_default_parameter_admits_null_in_its_schema():
    """`x: str = None` renders as {"type": "string", "default": null}.

    Strict clients reject a default outside the declared type; every optional
    parameter must be spelled `x: str | None = None` (ruff RUF013).
    """
    tools = anyio.run(server.mcp.list_tools)
    offenders = {
        t.name: bad
        for t in tools
        if (bad := _null_default_type_mismatches(t.input_schema))
    }
    assert offenders == {}
