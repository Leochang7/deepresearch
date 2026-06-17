from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

_DEFAULT_PROMPTS_DIR = Path(__file__).parent


@dataclass(frozen=True)
class PromptMetadata:
    """Metadata about a loaded prompt for traceability."""

    name: str
    provider_type: str  # "local", "langfuse", "langfuse_with_local_fallback"
    label: str  # Langfuse label, empty for local
    version: str  # Langfuse version, empty for local
    content_hash: str  # truncated sha256 (first 12 hex chars) of prompt text


class PromptProviderError(RuntimeError):
    """Raised when a strict prompt provider cannot return a prompt."""


@runtime_checkable
class PromptProvider(Protocol):
    """Abstraction for prompt text retrieval."""

    def get(self, name: str) -> str:
        """Return prompt text for the given name.

        Local providers may return an empty string for missing prompts; strict
        providers should raise PromptProviderError.
        """
        ...

    def get_with_metadata(self, name: str) -> tuple[str, PromptMetadata]:
        """Return (prompt_text, metadata)."""
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

    def get_with_metadata(self, name: str) -> tuple[str, PromptMetadata]:
        text = self.get(name)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12] if text else ""
        return text, PromptMetadata(
            name=name,
            provider_type="local",
            label="",
            version="",
            content_hash=content_hash,
        )

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
            prompt = self._client.get_prompt(
                prompt_name,
                label=self._label,
                type="text",
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

    def get_with_metadata(self, name: str) -> tuple[str, PromptMetadata]:
        text = self.get(name)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12] if text else ""
        return text, PromptMetadata(
            name=name,
            provider_type="langfuse",
            label=self._label,
            version="",
            content_hash=content_hash,
        )

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

    def get_with_metadata(self, name: str) -> tuple[str, PromptMetadata]:
        try:
            return self._langfuse.get_with_metadata(name)
        except PromptProviderError:
            pass
        text = self._local.get(name)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12] if text else ""
        return text, PromptMetadata(
            name=name,
            provider_type="langfuse_with_local_fallback",
            label=self._langfuse._label,
            version="",
            content_hash=content_hash,
        )

    def list_names(self) -> list[str]:
        return self._local.list_names()
