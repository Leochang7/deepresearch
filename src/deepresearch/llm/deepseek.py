from __future__ import annotations

from deepresearch.llm.openai_compatible import OpenAICompatibleLLMClient


class DeepSeekLLMClient(OpenAICompatibleLLMClient):
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
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            model=model,
            api_key_header="Authorization",
            api_key_prefix="Bearer ",
            max_tokens_field="max_tokens",
            default_temperature=default_temperature,
            default_top_p=default_top_p,
            default_max_completion_tokens=default_max_completion_tokens,
            timeout=timeout,
        )
