from __future__ import annotations

from deepresearch.llm.openai_compatible import OpenAICompatibleLLMClient


class MiMoLLMClient(OpenAICompatibleLLMClient):
    def __init__(
        self,
        *,
        base_url: str = "https://api.xiaomimimo.com/v1",
        api_key: str = "",
        model: str = "mimo-v2.5-pro",
        default_temperature: float = 1.0,
        default_top_p: float = 0.95,
        default_max_completion_tokens: int = 1024,
        thinking: str = "disabled",
        timeout: float = 60.0,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            model=model,
            api_key_header="api-key",
            api_key_prefix="",
            max_tokens_field="max_completion_tokens",
            default_temperature=default_temperature,
            default_top_p=default_top_p,
            default_max_completion_tokens=default_max_completion_tokens,
            timeout=timeout,
            extras={"thinking": {"type": thinking}},
        )
