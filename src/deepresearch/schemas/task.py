from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class TaskState(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    RETRYING = "RETRYING"
    REPLANNING = "REPLANNING"
    CANCELLED = "CANCELLED"


class TaskNode(BaseModel):
    task_id: str
    description: str
    goal: str = ""
    dependencies: list[str] = Field(default_factory=list)
    input: dict = Field(default_factory=dict)
    expected_output: str = ""
    priority: int = 0
    status: TaskState = TaskState.PENDING
    retries: int = 0
    max_retries: int = 2
    error: str | None = None
    result: dict | None = None


class ResearchPlan(BaseModel):
    plan_id: str
    question: str
    tasks: list[TaskNode]
    created_at: str = ""
    metadata: dict = Field(default_factory=dict)
