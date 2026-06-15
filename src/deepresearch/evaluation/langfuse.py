from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class LangfuseAdapter:
    """Optional Langfuse integration. No-op when disabled or unavailable."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        public_key: str = "",
        secret_key: str = "",
        host: str = "https://cloud.langfuse.com",
    ) -> None:
        self._enabled = enabled or os.environ.get(
            "DEEPRESEARCH_LANGFUSE_ENABLED", ""
        ) in ("1", "true", "True")
        self._public_key = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY", "")
        self._secret_key = secret_key or os.environ.get("LANGFUSE_SECRET_KEY", "")
        self._host = host or os.environ.get(
            "LANGFUSE_HOST", "https://cloud.langfuse.com"
        )
        self._client: Any = None
        if self._enabled:
            self._init_client()

    def _init_client(self) -> None:
        if not self._public_key or not self._secret_key:
            logger.warning(
                "Langfuse enabled but LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY "
                "not set. Disabling Langfuse."
            )
            self._enabled = False
            return
        try:
            from langfuse import Langfuse

            self._client = Langfuse(
                public_key=self._public_key,
                secret_key=self._secret_key,
                host=self._host,
            )
        except ImportError:
            logger.warning(
                "Langfuse package not installed. Install with: "
                "uv add langfuse. Disabling Langfuse."
            )
            self._enabled = False

    def report_run(
        self,
        run_id: str,
        question: str,
        report: dict[str, Any],
        evaluation: dict[str, Any],
        budget: dict[str, Any],
        config_summary: dict[str, Any],
        trace_summary: dict[str, Any],
    ) -> None:
        if not self._enabled or not self._client:
            return
        try:
            trace = self._client.trace(
                name=f"deepresearch-{run_id}",
                input={"question": question},
                metadata={"config": config_summary, "trace_summary": trace_summary},
            )
            trace.score(
                name="task_success_rate",
                value=evaluation.get("task_success_rate", 0),
            )
            trace.score(
                name="citation_coverage",
                value=evaluation.get("citation_coverage", 0),
            )
            trace.score(
                name="report_section_completeness",
                value=evaluation.get("report_section_completeness", 0),
            )
            trace.score(
                name="red_issue_count",
                value=evaluation.get("red_issue_count", 0),
            )
            trace.update(
                output={
                    "report": report,
                    "evaluation": evaluation,
                    "budget": budget,
                }
            )
            self._client.flush()
        except Exception:
            logger.warning("Failed to report run to Langfuse", exc_info=True)

    @property
    def is_enabled(self) -> bool:
        return self._enabled
