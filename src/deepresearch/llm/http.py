from __future__ import annotations

from typing import Any

import httpx


def auth_headers(
    *,
    api_key: str,
    api_key_header: str = "Authorization",
    api_key_prefix: str = "Bearer ",
) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key_header and api_key:
        headers[api_key_header] = f"{api_key_prefix}{api_key}"
    return headers


async def post_json(
    url: str,
    *,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
    max_retries: int = 0,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                continue
    raise last_error  # type: ignore[misc]


def normalize_llm_usage(usage: dict[str, Any]) -> dict[str, int]:
    prompt_tokens = int(usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0)
    completion_tokens = int(
        usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
    )
    normalized = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }
    total_tokens = usage.get("total_tokens")
    if total_tokens is not None:
        normalized["total_tokens"] = int(total_tokens or 0)
    return normalized
