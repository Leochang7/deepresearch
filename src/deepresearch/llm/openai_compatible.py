from __future__ import annotations

from typing import Any

import httpx

from deepresearch.llm.base import LLMClient, LLMMessage, LLMResponse


class OpenAICompatibleLLMClient(LLMClient):
    """Generic OpenAI-compatible chat completions client."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        api_key_header: str = "Authorization",
        api_key_prefix: str = "Bearer ",
        max_tokens_field: str = "max_tokens",
        default_temperature: float = 1.0,
        default_top_p: float = 0.95,
        default_max_completion_tokens: int = 1024,
        timeout: float = 60.0,
        extras: dict[str, Any] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._api_key_header = api_key_header
        self._api_key_prefix = api_key_prefix
        self._max_tokens_field = max_tokens_field
        self._default_temperature = default_temperature
        self._default_top_p = default_top_p
        self._default_max_completion_tokens = default_max_completion_tokens
        self._timeout = timeout
        self._extras = extras or {}

    async def chat(
        self,
        messages: list[LLMMessage] | list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        max_completion_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": model or self._model,
            "messages": [
                m if isinstance(m, dict) else {"role": m.role, "content": m.content}
                for m in messages
            ],
            "temperature": temperature
            if temperature is not None
            else self._default_temperature,
            "top_p": top_p if top_p is not None else self._default_top_p,
            self._max_tokens_field: (
                max_completion_tokens
                if max_completion_tokens is not None
                else self._default_max_completion_tokens
            ),
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        payload.update(self._extras)

        headers = {"Content-Type": "application/json"}
        if self._api_key_header and self._api_key:
            headers[self._api_key_header] = f"{self._api_key_prefix}{self._api_key}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()

        data = resp.json()
        choice = data["choices"][0]["message"]
        return LLMResponse(
            content=choice["content"],
            model=data.get("model", self._model),
            usage=data.get("usage", {}),
            raw=data,
        )
