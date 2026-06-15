from __future__ import annotations

import json
import re
from typing import Any


def parse_json(
    text: str,
    *,
    defaults: dict[str, Any] | None = None,
    strict: bool = False,
) -> Any:
    """Parse JSON from LLM output with multiple fallback strategies.

    Tries in order:
    1. Strict JSON parsing
    2. Extract from Markdown code block
    3. Extract first JSON object/array from surrounding text
    4. Clean trailing commas and Chinese quotes, then retry

    Args:
        text: Raw text that may contain JSON.
        defaults: Default field values for the top-level object.
        strict: If True, raise ValueError on failure. If False, return None.

    Returns:
        Parsed data, or None if unparseable and strict=False.
    """
    if not text or not text.strip():
        if strict:
            raise ValueError("Empty input")
        return None

    cleaned = _preprocess(text)

    # Strategy 1: strict JSON
    result = _try_parse(cleaned)
    if result is not None:
        return _apply_defaults(result, defaults)

    # Strategy 2: Markdown code block
    result = _extract_code_block(text)
    if result is not None:
        return _apply_defaults(result, defaults)

    # Strategy 3: first JSON object/array in surrounding text
    result = _extract_first_json(cleaned)
    if result is not None:
        return _apply_defaults(result, defaults)

    # Strategy 4: aggressive cleanup then retry
    aggressively_cleaned = _remove_trailing_commas(cleaned)
    aggressively_cleaned = _replace_chinese_quotes(aggressively_cleaned)
    result = _try_parse(aggressively_cleaned)
    if result is not None:
        return _apply_defaults(result, defaults)

    # Try code block extraction after aggressive cleanup
    result = _extract_code_block(aggressively_cleaned)
    if result is not None:
        return _apply_defaults(result, defaults)

    result = _extract_first_json(aggressively_cleaned)
    if result is not None:
        return _apply_defaults(result, defaults)

    if strict:
        raise ValueError(f"Failed to parse JSON from: {text[:200]}...")
    return None


def _preprocess(text: str) -> str:
    """Replace Chinese/fullwidth quotes with ASCII equivalents."""
    text = _replace_chinese_quotes(text.strip())
    text = _convert_single_quotes(text)
    return text


def _convert_single_quotes(text: str) -> str:
    """Convert single-quoted JSON-like strings to double-quoted.

    Only applies when the text starts with { or [ and uses single quotes.
    """
    stripped = text.lstrip()
    if not stripped or stripped[0] not in "{[":
        return text
    if "'" not in text:
        return text
    try:
        result = []
        in_double_quote = False
        i = 0
        while i < len(text):
            c = text[i]
            if c == '"' and (i == 0 or text[i - 1] != "\\"):
                in_double_quote = not in_double_quote
                result.append(c)
            elif c == "'" and not in_double_quote:
                # Find matching single quote
                j = i + 1
                while j < len(text) and text[j] != "'":
                    if text[j] == "\\":
                        j += 1
                    j += 1
                inner = text[i + 1 : j].replace('"', '\\"')
                result.append('"')
                result.append(inner)
                result.append('"')
                i = j + 1
                continue
            else:
                result.append(c)
            i += 1
        return "".join(result)
    except (IndexError, ValueError):
        return text


def _replace_chinese_quotes(text: str) -> str:
    replacements = {
        "“": '"',  # left double quotation mark
        "”": '"',  # right double quotation mark
        "‘": "'",  # left single quotation mark
        "’": "'",  # right single quotation mark
        "＂": '"',  # fullwidth quotation mark
        "「": '"',  # left corner bracket
        "」": '"',  # right corner bracket
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _try_parse(text: str) -> Any | None:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _extract_code_block(text: str) -> Any | None:
    pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        content = match.group(1).strip()
        content = _remove_trailing_commas(content)
        content = _replace_chinese_quotes(content)
        result = _try_parse(content)
        if result is not None:
            return result
    return None


def _extract_first_json(text: str) -> Any | None:
    """Extract the first complete JSON object or array from text."""
    text = _remove_trailing_commas(text)

    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue

        depth = 0
        in_string = False
        escape_next = False

        for i in range(start, len(text)):
            c = text[i]

            if escape_next:
                escape_next = False
                continue

            if c == "\\":
                escape_next = True
                continue

            if c == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if c == start_char:
                depth += 1
            elif c == end_char:
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    result = _try_parse(candidate)
                    if result is not None:
                        return result
                    break

    return None


def _remove_trailing_commas(text: str) -> str:
    # Remove trailing comma before } or ]
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    return text


def _apply_defaults(data: Any, defaults: dict[str, Any] | None) -> Any:
    if defaults and isinstance(data, dict):
        merged = defaults.copy()
        merged.update(data)
        return merged
    return data
