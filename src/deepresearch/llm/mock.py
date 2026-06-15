from __future__ import annotations

import json
from typing import Any

from deepresearch.llm.base import LLMClient, LLMMessage, LLMResponse

_PLANNER_RESPONSE = json.dumps(
    {
        "plan_id": "p1",
        "tasks": [
            {
                "task_id": "t1",
                "description": "Research background and context",
                "goal": "Gather foundational information",
                "dependencies": [],
                "priority": 1,
            },
            {
                "task_id": "t2",
                "description": "Analyze current trends",
                "goal": "Identify key trends and patterns",
                "dependencies": ["t1"],
                "priority": 2,
            },
            {
                "task_id": "t3",
                "description": "Evaluate impact and implications",
                "goal": "Assess significance",
                "dependencies": ["t1", "t2"],
                "priority": 3,
            },
        ],
    }
)

_RESEARCH_RESPONSE = json.dumps(
    {
        "task_id": "t1",
        "summary": "Found several relevant sources on the topic.",
        "evidence": [
            {
                "evidence_id": "E1",
                "claim": "LLM agents have improved significantly in 2024-2025",
                "quote": "Recent advances in LLM agents show 40% improvement in task completion rates.",
                "citation": "AI Research Journal 2025",
                "source_url": "https://example.com/paper1",
                "confidence": 0.85,
            },
            {
                "evidence_id": "E2",
                "claim": "Multi-agent collaboration is a key trend",
                "quote": "Multi-agent systems outperform single-agent approaches on complex tasks.",
                "citation": "Agent Conference 2024",
                "source_url": "https://example.com/paper2",
                "confidence": 0.78,
            },
        ],
    }
)

_SYNTHESIS_RESPONSE = """## Executive Summary

This report analyzes recent developments in the field.

## Background

Based on the evidence gathered, several key findings emerge [E1].

## Analysis

Multi-agent approaches show significant promise [E2].

## Limitations

- Limited coverage of non-English sources
- Time window constrained to 2024-2025

## References

- [E1] AI Research Journal 2025
- [E2] Agent Conference 2024
"""

_RED_RESPONSE = json.dumps(
    {
        "issues": [
            {
                "issue_id": "R1",
                "type": "missing_citation",
                "severity": "medium",
                "location": "Background section, paragraph 2",
                "description": "Claim about industry adoption lacks citation.",
                "suggestion": "Add supporting evidence from industry reports.",
            }
        ],
        "score": 0.75,
    }
)

_BLUE_RESPONSE = json.dumps(
    {
        "actions": [
            {
                "action_id": "B1",
                "type": "ADD",
                "target": "Background section",
                "content": "Industry reports indicate growing adoption of LLM agents in enterprise settings.",
                "evidence_id": "E1",
            }
        ],
        "revised_score": 0.82,
    }
)


class MockLLM(LLMClient):
    def __init__(
        self,
        responses: dict[str, str] | None = None,
        default_response: str = '{"result": "ok"}',
    ) -> None:
        self._responses = responses or {
            "planner": _PLANNER_RESPONSE,
            "research": _RESEARCH_RESPONSE,
            "synthesis": _SYNTHESIS_RESPONSE,
            "red": _RED_RESPONSE,
            "blue": _BLUE_RESPONSE,
        }
        self._default_response = default_response
        self._calls: list[dict[str, Any]] = []

    @property
    def calls(self) -> list[dict[str, Any]]:
        return self._calls

    @property
    def call_count(self) -> int:
        return len(self._calls)

    def set_response(self, key: str, response: str) -> None:
        self._responses[key] = response

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        max_completion_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        self._calls.append(
            {
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "model": model,
                "temperature": temperature,
                "top_p": top_p,
                "max_completion_tokens": max_completion_tokens,
                "json_mode": json_mode,
            }
        )

        content = self._pick_response(messages)
        return LLMResponse(
            content=content,
            model=model or "mock",
            usage={"prompt_tokens": 100, "completion_tokens": 50},
        )

    def _pick_response(self, messages: list[LLMMessage]) -> str:
        combined = " ".join(m.content.lower() for m in messages)

        for key in self._responses:
            if key in combined:
                return self._responses[key]

        return self._default_response
