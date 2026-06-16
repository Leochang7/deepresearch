from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


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

    def __init__(self, prompts_dir: Path | str) -> None:
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
            prompt = self._client.prompt.get(
                name=f"deepresearch/{name}",
                label=self._label,
            )
            return prompt.compile()
        except Exception:
            return ""

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
        result = self._langfuse.get(name)
        if result:
            return result
        return self._local.get(name)

    def list_names(self) -> list[str]:
        return self._local.list_names()
