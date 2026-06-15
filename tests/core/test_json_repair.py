import pytest

from deepresearch.core.json_repair import parse_json


class TestStrictJSON:
    def test_valid_json_object(self):
        data = parse_json('{"key": "value", "num": 42}')
        assert data == {"key": "value", "num": 42}

    def test_valid_json_array(self):
        data = parse_json("[1, 2, 3]")
        assert data == [1, 2, 3]

    def test_valid_json_string(self):
        data = parse_json('"hello"')
        assert data == "hello"

    def test_valid_json_nested(self):
        s = '{"a": {"b": [1, 2]}, "c": true}'
        data = parse_json(s)
        assert data["a"]["b"] == [1, 2]
        assert data["c"] is True


class TestMarkdownCodeBlock:
    def test_json_in_code_block(self):
        text = """Here is the result:
```json
{"plan": "test", "tasks": ["a", "b"]}
```
Hope this helps."""
        data = parse_json(text)
        assert data == {"plan": "test", "tasks": ["a", "b"]}

    def test_json_in_plain_code_block(self):
        text = """```
{"key": "value"}
```"""
        data = parse_json(text)
        assert data == {"key": "value"}

    def test_code_block_with_extra_text(self):
        text = """Some preamble text.

```json
{"answer": 42}
```

Some trailing text."""
        data = parse_json(text)
        assert data == {"answer": 42}


class TestExtractFirstJSON:
    def test_json_with_surrounding_text(self):
        text = 'blah blah {"key": "value"} blah blah'
        data = parse_json(text)
        assert data == {"key": "value"}

    def test_json_array_with_surrounding_text(self):
        text = "some text [1, 2, 3] more text"
        data = parse_json(text)
        assert data == [1, 2, 3]

    def test_nested_braces(self):
        text = 'prefix {"a": {"b": 1}} suffix'
        data = parse_json(text)
        assert data == {"a": {"b": 1}}

    def test_string_with_braces_in_values(self):
        text = '{"msg": "use {x} here"}'
        data = parse_json(text)
        assert data == {"msg": "use {x} here"}


class TestTrailingCommas:
    def test_trailing_comma_in_object(self):
        text = '{"a": 1, "b": 2,}'
        data = parse_json(text)
        assert data == {"a": 1, "b": 2}

    def test_trailing_comma_in_array(self):
        text = "[1, 2, 3,]"
        data = parse_json(text)
        assert data == [1, 2, 3]

    def test_trailing_comma_in_nested(self):
        text = '{"items": [1, 2,], "ok": true,}'
        data = parse_json(text)
        assert data == {"items": [1, 2], "ok": True}


class TestChineseQuotes:
    def test_chinese_double_quotes(self):
        text = '{"key": “value”}'
        data = parse_json(text)
        assert data == {"key": "value"}

    def test_chinese_single_quotes(self):
        text = "{'key': 'value'}"
        data = parse_json(text)
        assert data == {"key": "value"}

    def test_fullwidth_quotes(self):
        text = '{"key": ＂value＂}'
        data = parse_json(text)
        assert data == {"key": "value"}


class TestDefaultFields:
    def test_fill_missing_fields(self):
        text = '{"name": "test"}'
        defaults = {"name": "default", "version": 1, "active": True}
        data = parse_json(text, defaults=defaults)
        assert data["name"] == "test"
        assert data["version"] == 1
        assert data["active"] is True

    def test_defaults_do_not_override_existing(self):
        text = '{"name": "real", "version": 2}'
        defaults = {"name": "default", "version": 1}
        data = parse_json(text, defaults=defaults)
        assert data["name"] == "real"
        assert data["version"] == 2

    def test_defaults_on_completely_empty(self):
        defaults = {"x": 1, "y": 2}
        data = parse_json("{}", defaults=defaults)
        assert data == {"x": 1, "y": 2}


class TestErrorCases:
    def test_unparseable_returns_none(self):
        data = parse_json("not json at all [[[", strict=False)
        assert data is None

    def test_unparseable_strict_raises(self):
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            parse_json("not json at all [[[", strict=True)

    def test_empty_string_returns_none(self):
        data = parse_json("", strict=False)
        assert data is None

    def test_whitespace_only_returns_none(self):
        data = parse_json("   \n\t  ", strict=False)
        assert data is None


class TestRealWorldLLMOutput:
    def test_llm_response_with_explanation(self):
        text = """Based on my analysis, here is the plan:

```json
{
  "plan_id": "p1",
  "tasks": [
    {"task_id": "t1", "description": "Research topic A"},
    {"task_id": "t2", "description": "Analyze data", "dependencies": ["t1"]}
  ]
}
```

This plan covers the main aspects of the research question."""
        data = parse_json(text)
        assert data["plan_id"] == "p1"
        assert len(data["tasks"]) == 2
        assert data["tasks"][1]["dependencies"] == ["t1"]

    def test_llm_json_with_trailing_commas_and_explanation(self):
        text = """Here's the result:
{
  "summary": "Found 3 relevant papers",
  "confidence": 0.85,
  "sources": ["paper1", "paper2", "paper3",],
}
Let me know if you need more details."""
        data = parse_json(text)
        assert data["summary"] == "Found 3 relevant papers"
        assert len(data["sources"]) == 3
