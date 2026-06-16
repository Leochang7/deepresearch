from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

_DEFAULT_PROMPTS_DIR = Path(__file__).parent


class PromptProviderError(RuntimeError):
    """Raised when a strict prompt provider cannot return a prompt."""


@runtime_checkable
class PromptProvider(Protocol):
    """Abstraction for prompt text retrieval."""

    def get(self, name: str) -> str:
        """Return prompt text for the given name, or empty string if missing."""
        ...

    def list_names(self) -> list[str]:
        """Return names of all available prompts."""
        ...


class LocalPromptProvider:
    """Reads prompt .md files from a local directory."""

    def __init__(self, prompts_dir: Path | str = _DEFAULT_PROMPTS_DIR) -> None:
        self._dir = Path(prompts_dir)

    def get(self, name: str) -> str:
        path = self._dir / f"{name}.md"
        if path.is_file():
            return path.read_text(encoding="utf-8")
        return ""

    def list_names(self) -> list[str]:
        if not self._dir.is_dir():
            return []
        return sorted(p.stem for p in self._dir.glob("*.md"))


class LangfusePromptProvider:
    """Fetches prompts from Langfuse Prompt Management."""

    def __init__(self, client: object, label: str = "production") -> None:
        self._client = client
        self._label = label

    def get(self, name: str) -> str:
        try:
            prompt_name = f"deepresearch/{name}"
            if hasattr(self._client, "get_prompt"):
                prompt = self._client.get_prompt(
                    prompt_name,
                    label=self._label,
                    type="text",
                )
            else:
                prompt = self._client.prompt.get(
                    name=prompt_name,
                    label=self._label,
                )
            result = prompt.compile()
        except Exception as exc:
            raise PromptProviderError(
                f"Failed to load Langfuse prompt deepresearch/{name} "
                f"with label {self._label}: {exc}"
            ) from exc
        if not result:
            raise PromptProviderError(
                f"Langfuse prompt deepresearch/{name} with label {self._label} is empty"
            )
        return result

    def list_names(self) -> list[str]:
        return []


class LangfuseWithFallbackProvider:
    """Tries Langfuse first, falls back to local on failure."""

    def __init__(
        self,
        client: object,
        local: PromptProvider,
        label: str = "production",
    ) -> None:
        self._langfuse = LangfusePromptProvider(client=client, label=label)
        self._local = local

    def get(self, name: str) -> str:
        try:
            return self._langfuse.get(name)
        except PromptProviderError:
            pass
        return self._local.get(name)

    def list_names(self) -> list[str]:
        return self._local.list_names()
