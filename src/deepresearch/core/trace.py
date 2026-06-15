from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class TraceEventType(StrEnum):
    PLANNER_CREATED_PLAN = "planner_created_plan"
    TASK_STATE_CHANGED = "task_state_changed"
    RETRIEVER_CALLED = "retriever_called"
    MILVUS_UPSERTED = "milvus_upserted"
    MILVUS_SEARCHED = "milvus_searched"
    LLM_CALLED = "llm_called"
    RED_REVIEW_CREATED = "red_review_created"
    BLUE_FIX_APPLIED = "blue_fix_applied"
    EVALUATION_COMPLETED = "evaluation_completed"


class TraceLogger:
    def __init__(
        self,
        path: Path | str,
        *,
        run_id: str = "",
    ) -> None:
        self._path = Path(path)
        self._run_id = run_id
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> TraceLogger:
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def log(
        self,
        event_type: TraceEventType,
        data: dict[str, Any],
        *,
        task_id: str = "",
    ) -> None:
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "run_id": self._run_id,
            "task_id": task_id,
            "event_type": event_type.value,
            "metadata": data,
        }
        line = json.dumps(event, ensure_ascii=False) + "\n"
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line)
