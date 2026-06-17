from __future__ import annotations

import contextlib
import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from deepresearch.schemas.evaluation import EvaluationLayers

logger = logging.getLogger(__name__)


class LangfuseContext:
    """Manages nested Langfuse observations for a single run."""

    def __init__(
        self,
        client: Any,
        trace_id: str,
        parent_observation_id: str,
        run_observation: Any = None,
    ) -> None:
        self._client = client
        self.trace_id = trace_id
        self._parent_observation_id = parent_observation_id
        self._run_observation = run_observation

    def __enter__(self) -> LangfuseContext:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        return None

    @contextmanager
    def create_phase(
        self,
        name: str,
        input_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        as_type: str = "span",
    ) -> Generator[dict[str, Any], None, None]:
        """Create a phase-level span nested under the run observation.

        Yields a dict that will be sent as output on exit.
        """
        obs = None
        try:
            obs = self._client.start_observation(
                trace_context={"trace_id": self.trace_id},
                name=name,
                as_type=as_type,
                input=input_data or {},
                metadata=metadata or {},
                parent_observation_id=self._parent_observation_id,
            )
        except Exception:
            logger.debug("Failed to create Langfuse phase span '%s'", name, exc_info=True)
        obs_id = getattr(obs, "observation_id", "") if obs else ""
        result: dict[str, Any] = {"_observation_id": obs_id}
        try:
            yield result
        finally:
            if obs is not None and hasattr(obs, "end"):
                with contextlib.suppress(Exception):
                    obs.end()

    @contextmanager
    def create_task(
        self,
        task_id: str,
        description: str,
        parent_observation_id: str,
    ) -> Generator[dict[str, Any], None, None]:
        """Create a task-level span nested under a phase observation."""
        obs = None
        try:
            obs = self._client.start_observation(
                trace_context={"trace_id": self.trace_id},
                name=f"task-{task_id}",
                as_type="span",
                input={"task_id": task_id, "description": description},
                metadata={"task_id": task_id},
                parent_observation_id=parent_observation_id,
            )
        except Exception:
            logger.debug(
                "Failed to create Langfuse task span '%s'", task_id, exc_info=True
            )
        result: dict[str, Any] = {}
        try:
            yield result
        finally:
            if obs is not None and hasattr(obs, "end"):
                with contextlib.suppress(Exception):
                    obs.end()

    def end_run(
        self,
        evaluation: dict[str, Any],
        budget: dict[str, Any],
    ) -> None:
        """End the run-level observation and emit evaluation + budget scores."""
        # Evaluation scores
        try:
            layers = EvaluationLayers.from_evaluation_dict(evaluation)
            rule_metrics = layers.rule_metrics
            for score_name in (
                "task_success_rate",
                "citation_coverage",
                "report_section_completeness",
            ):
                with contextlib.suppress(Exception):
                    self._client.create_score(
                        trace_id=self.trace_id,
                        name=score_name,
                        value=getattr(rule_metrics, score_name),
                    )
            with contextlib.suppress(Exception):
                self._client.create_score(
                    trace_id=self.trace_id,
                    name="factual_hit_rate",
                    value=rule_metrics.factual_hit_rate,
                )
            with contextlib.suppress(Exception):
                self._client.create_score(
                    trace_id=self.trace_id,
                    name="hallucination_flag",
                    value=int(rule_metrics.hallucination_flag),
                )
            with contextlib.suppress(Exception):
                self._client.create_score(
                    trace_id=self.trace_id,
                    name="red_issue_count",
                    value=layers.statistical_context.red_issue_count,
                )
            for dim, score in layers.judge_scores.items():
                with contextlib.suppress(Exception):
                    self._client.create_score(
                        trace_id=self.trace_id,
                        name=f"judge_{dim}",
                        value=score,
                    )
        except Exception:
            logger.debug("Failed to emit evaluation scores", exc_info=True)

        # Budget scores
        for name in (
            "llm_calls",
            "search_calls",
            "fetched_docs",
            "chunks",
            "embedding_batches",
            "rerank_calls",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "elapsed_seconds",
        ):
            if name in budget:
                with contextlib.suppress(Exception):
                    self._client.create_score(
                        trace_id=self.trace_id,
                        name=f"budget_{name}",
                        value=float(budget[name]),
                    )

        # End the run-level observation
        if self._run_observation is not None and hasattr(self._run_observation, "end"):
            with contextlib.suppress(Exception):
                self._run_observation.end()
        with contextlib.suppress(Exception):
            self._client.flush()


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
        self._last_trace_id: str = ""
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
            self._report_run(
                run_id,
                question,
                report,
                evaluation,
                budget,
                config_summary,
                trace_summary,
                benchmark_metadata,
            )
            self._client.flush()
        except Exception:
            logger.warning("Failed to report run to Langfuse", exc_info=True)

    def _report_run(
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
        self._last_trace_id = trace_id
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
        layers = EvaluationLayers.from_evaluation_dict(evaluation)
        rule_metrics = layers.rule_metrics
        for score_name in (
            "task_success_rate",
            "citation_coverage",
            "report_section_completeness",
        ):
            self._client.create_score(
                trace_id=trace_id,
                name=score_name,
                value=getattr(rule_metrics, score_name),
            )
        # Additional evaluation scores
        self._client.create_score(
            trace_id=trace_id,
            name="factual_hit_rate",
            value=rule_metrics.factual_hit_rate,
        )
        self._client.create_score(
            trace_id=trace_id,
            name="hallucination_flag",
            value=int(rule_metrics.hallucination_flag),
        )
        self._client.create_score(
            trace_id=trace_id,
            name="red_issue_count",
            value=layers.statistical_context.red_issue_count,
        )
        for dim, score in layers.judge_scores.items():
            self._client.create_score(
                trace_id=trace_id,
                name=f"judge_{dim}",
                value=score,
            )
        if hasattr(observation, "end"):
            observation.end()

    def report_benchmark_scores(
        self,
        *,
        trace_id: str,
        evaluation: dict[str, Any],
    ) -> None:
        """Attach benchmark-specific scores to an existing trace."""
        if not self._enabled or not self._client or not trace_id:
            return
        try:
            layers = EvaluationLayers.from_evaluation_dict(evaluation)
            rule_metrics = layers.rule_metrics
            for score_name in (
                "task_success_rate",
                "citation_coverage",
                "report_section_completeness",
                "factual_hit_rate",
            ):
                self._client.create_score(
                    trace_id=trace_id,
                    name=f"benchmark_{score_name}",
                    value=getattr(rule_metrics, score_name),
                )
            self._client.create_score(
                trace_id=trace_id,
                name="benchmark_hallucination_flag",
                value=int(rule_metrics.hallucination_flag),
            )
            for dim, score in layers.judge_scores.items():
                self._client.create_score(
                    trace_id=trace_id,
                    name=f"benchmark_judge_{dim}",
                    value=score,
                )
            self._client.flush()
        except Exception:
            logger.warning(
                "Failed to report benchmark scores to Langfuse", exc_info=True
            )

    def push_dataset(
        self,
        *,
        dataset_name: str,
        cases: list[dict],
    ) -> int:
        """Push benchmark cases to Langfuse as dataset items. Returns count pushed."""
        if not self._enabled:
            return 0
        if not self._client:
            self._init_client()
        if not self._client:
            return 0
        with contextlib.suppress(Exception):  # dataset may already exist
            self._client.create_dataset(name=dataset_name)
        count = 0
        for case in cases:
            try:
                self._client.create_dataset_item(
                    dataset_name=dataset_name,
                    input={
                        "question": case.get("question", ""),
                        "case_id": case.get("id", ""),
                    },
                    expected_output={
                        "expected_facts": case.get("expected_facts", []),
                    },
                    metadata={
                        "domain": case.get("domain", ""),
                        "difficulty": case.get("difficulty", ""),
                        "question_lang": case.get("question_lang", "en"),
                        "evidence_lang": case.get("evidence_lang", "en"),
                    },
                    id=case.get("id", ""),
                )
                count += 1
            except Exception as exc:
                logger.warning(
                    "Failed to push Langfuse dataset item %s: %s",
                    case.get("id", ""),
                    exc,
                )
        with contextlib.suppress(Exception):
            self._client.flush()
        return count

    def link_run_to_dataset(
        self,
        *,
        dataset_name: str,
        case_id: str,
        run_id: str,
        trace_id: str,
    ) -> None:
        """Link a benchmark run trace to a Langfuse dataset item."""
        if not self._enabled:
            return
        logger.info(
            "Langfuse dataset link available via trace metadata: "
            "dataset=%s case_id=%s run_id=%s trace_id=%s",
            dataset_name,
            case_id,
            run_id,
            trace_id,
        )

    @property
    def last_trace_id(self) -> str:
        return self._last_trace_id

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def context(
        self,
        run_id: str,
        question: str,
        metadata: dict[str, Any] | None = None,
    ) -> LangfuseContext | None:
        """Create a LangfuseContext for nested observation tracking.

        Returns None if Langfuse is disabled. The caller should use the
        returned context as a context manager; on exit the run-level
        observation is NOT ended (call end_run() explicitly).
        """
        if not self._enabled or not self._client:
            return None
        try:
            trace_id = self._client.create_trace_id(seed=run_id)
            self._last_trace_id = trace_id
            obs = self._client.start_observation(
                trace_context={"trace_id": trace_id},
                name=f"deepresearch-{run_id}",
                as_type="agent",
                input={"question": question},
                metadata=metadata or {},
            )
            obs_id = getattr(obs, "observation_id", "")
            return LangfuseContext(
                client=self._client,
                trace_id=trace_id,
                parent_observation_id=obs_id,
                run_observation=obs,
            )
        except Exception:
            logger.warning("Failed to create Langfuse context", exc_info=True)
            return None
