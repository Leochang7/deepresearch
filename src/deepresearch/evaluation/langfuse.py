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
        *,
        case_id: str = "",
        domain: str = "",
        difficulty: str = "",
        question_lang: str = "",
        evidence_lang: str = "",
        source_dataset: str = "",
        model_backend: str = "",
        prompt_label: str = "",
    ) -> None:
        if not self._enabled or not self._client:
            return
        benchmark_metadata: dict[str, Any] = {}
        if case_id:
            benchmark_metadata.update(
                {
                    "case_id": case_id,
                    "domain": domain,
                    "difficulty": difficulty,
                    "question_lang": question_lang,
                    "evidence_lang": evidence_lang,
                    "source_dataset": source_dataset,
                    "model_backend": model_backend,
                    "prompt_label": prompt_label,
                }
            )
        try:
            if hasattr(self._client, "start_observation"):
                self._report_run_v4(
                    run_id,
                    question,
                    report,
                    evaluation,
                    budget,
                    config_summary,
                    trace_summary,
                    benchmark_metadata,
                )
                return
            full_metadata = {
                **config_summary,
                **benchmark_metadata,
                "trace_summary": trace_summary,
            }
            trace = self._client.trace(
                name=f"deepresearch-{run_id}",
                input={"question": question},
                metadata=full_metadata,
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
            # Additional evaluation scores
            trace.score(
                name="factual_hit_rate",
                value=evaluation.get("factual_hit_rate", 0),
            )
            trace.score(
                name="hallucination_flag",
                value=int(evaluation.get("hallucination_flag", False)),
            )
            for dim, score in evaluation.get("judge_scores", {}).items():
                trace.score(name=f"judge_{dim}", value=score)
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

    def _report_run_v4(
        self,
        run_id: str,
        question: str,
        report: dict[str, Any],
        evaluation: dict[str, Any],
        budget: dict[str, Any],
        config_summary: dict[str, Any],
        trace_summary: dict[str, Any],
        benchmark_metadata: dict[str, Any] | None = None,
    ) -> None:
        trace_id = self._client.create_trace_id(seed=run_id)
        full_metadata = {
            **config_summary,
            **(benchmark_metadata or {}),
            "trace_summary": trace_summary,
        }
        observation = self._client.start_observation(
            trace_context={"trace_id": trace_id},
            name=f"deepresearch-{run_id}",
            as_type="agent",
            input={"question": question},
            output={
                "report": report,
                "evaluation": evaluation,
                "budget": budget,
            },
            metadata=full_metadata,
        )
        for score_name in (
            "task_success_rate",
            "citation_coverage",
            "report_section_completeness",
            "red_issue_count",
        ):
            self._client.create_score(
                trace_id=trace_id,
                name=score_name,
                value=evaluation.get(score_name, 0),
            )
        # Additional evaluation scores
        self._client.create_score(
            trace_id=trace_id,
            name="factual_hit_rate",
            value=evaluation.get("factual_hit_rate", 0),
        )
        self._client.create_score(
            trace_id=trace_id,
            name="hallucination_flag",
            value=int(evaluation.get("hallucination_flag", False)),
        )
        for dim, score in evaluation.get("judge_scores", {}).items():
            self._client.create_score(
                trace_id=trace_id,
                name=f"judge_{dim}",
                value=score,
            )
        if hasattr(observation, "end"):
            observation.end()
        self._client.flush()

    @property
    def is_enabled(self) -> bool:
        return self._enabled
