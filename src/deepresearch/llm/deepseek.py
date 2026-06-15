from __future__ import annotations

from typing import Any

import httpx

from deepresearch.llm.base import LLMClient, LLMMessage, LLMResponse


class DeepSeekLLMClient(LLMClient):
    def __init__(
        self,
        *,
        base_url: str = "https://api.deepseek.com/v1",
        api_key: str = "",
        model: str = "deepseek-chat",
        default_temperature: float = 1.0,
        default_top_p: float = 0.95,
        default_max_completion_tokens: int = 1024,
        timeout: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._default_temperature = default_temperature
        self._default_top_p = default_top_p
        self._default_max_completion_tokens = default_max_completion_tokens
        self._timeout = timeout

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        max_completion_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": model or self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature
            if temperature is not None
            else self._default_temperature,
            "top_p": top_p if top_p is not None else self._default_top_p,
            "max_tokens": max_completion_tokens
            if max_completion_tokens is not None
            else self._default_max_completion_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        content = choice["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=data.get("model", payload["model"]),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            },
            raw=data,
        )
