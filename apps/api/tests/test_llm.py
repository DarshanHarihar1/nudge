import pytest

from ai.llm import parse_json_reply


def test_plain_object():
    assert parse_json_reply('{"a": 1}') == {"a": 1}


def test_fenced_and_list_wrapped():
    # Both shapes Gemma was seen returning for the classifier prompt.
    assert parse_json_reply('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_reply('[ {"a": 1} ]') == {"a": 1}


def test_non_object_rejected():
    with pytest.raises(ValueError):
        parse_json_reply('[1, 2]')
