import json
from bettercopilot.ui.gui import api


def test_extract_json_from_fenced_block():
    s = 'Here is the result:\n```json\n{"chat": "hello", "diffs": []}\n```\nThanks.'
    parsed = api._extract_json_from_string(s)
    assert isinstance(parsed, dict)
    assert parsed.get('chat') == 'hello'


def test_extract_json_embedded_object():
    # Use escaped backslashes so JSON contains literal "\\n" sequences
    s = 'prefix text {"chat":"hi","diff":"--- a\\n+++ b\\n"} trailing'
    parsed = api._extract_json_from_string(s)
    assert isinstance(parsed, dict)
    assert parsed.get('chat') == 'hi'


def test_extract_json_array():
    s = 'Result: [1, 2, 3] end.'
    parsed = api._extract_json_from_string(s)
    assert isinstance(parsed, list)
    assert parsed == [1, 2, 3]


def test_extract_json_none_on_nonjson():
    s = 'No json here, just text.'
    parsed = api._extract_json_from_string(s)
    assert parsed is None
