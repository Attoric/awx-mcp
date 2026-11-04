# SPDX-License-Identifier: Apache-2.0

import pytest

from awx_mcp.utils import normalize_json_param, parse_json_str, validate_json_str


def test_validate_json_str_returns_none_for_valid_object_array_string_number():
    assert validate_json_str('{"k": 1}', "payload") is None
    assert validate_json_str("[1, 2, 3]", "payload") is None
    assert validate_json_str('"hello"', "payload") is None
    assert validate_json_str("42", "payload") is None


def test_validate_json_str_raises_value_error_naming_the_param():
    with pytest.raises(ValueError, match="extra_vars"):
        validate_json_str('{"k":', "extra_vars")


def test_parse_json_str_returns_parsed_data_for_valid_json():
    assert parse_json_str('{"k": 1}', "payload") == {"k": 1}
    assert parse_json_str("[1, 2, 3]", "payload") == [1, 2, 3]


def test_parse_json_str_raises_value_error_naming_the_param():
    with pytest.raises(ValueError, match="inputs") as info:
        parse_json_str('{"k":', "inputs")
    # the JSON parser's reason is kept so the model can fix the value
    assert "Invalid JSON in inputs:" in str(info.value)
    assert info.value.__cause__ is not None


def test_parse_json_str_returns_expected_python_types_for_dict_and_list():
    assert isinstance(parse_json_str('{"a": 1}', "payload"), dict)
    assert isinstance(parse_json_str('["a", "b"]', "payload"), list)


def test_normalize_json_param_dumps_dict_and_list():
    assert normalize_json_param({"k": 1}, "payload") == '{"k": 1}'
    assert normalize_json_param([1, 2], "payload") == "[1, 2]"


def test_normalize_json_param_preserves_valid_json_string():
    raw = '{"deploy_commands":"false"}'
    assert normalize_json_param(raw, "extra_vars") == raw


def test_normalize_json_param_rejects_invalid_json_string():
    with pytest.raises(ValueError, match="extra_vars"):
        normalize_json_param('{"k":', "extra_vars")


def test_normalize_json_param_rejects_unsupported_types():
    with pytest.raises(ValueError, match="extra_vars must be a JSON string"):
        normalize_json_param(42, "extra_vars")  # type: ignore[arg-type]


def test_normalize_json_param_rejects_unserializable_dict():
    with pytest.raises(ValueError, match="Invalid JSON in extra_vars"):
        normalize_json_param({"k": {1, 2}}, "extra_vars")


def test_normalize_json_param_allows_yaml_when_requested():
    yaml_text = "key: value"
    assert (
        normalize_json_param(yaml_text, "source_vars", allow_non_json_str=True)
        == yaml_text
    )
    with pytest.raises(ValueError, match="source_vars"):
        normalize_json_param("{bad", "source_vars", allow_non_json_str=True)
