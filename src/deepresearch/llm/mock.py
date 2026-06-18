from __future__ import annotations

import json
import re
from typing import Any

from deepresearch.llm.base import LLMClient, LLMMessage, LLMResponse

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


class MockLLM(LLMClient):
    def __init__(
        self,
        responses: list[str] | None = None,
        default_response: str = '{"result": "ok"}',
    ) -> None:
        self._queue: list[str] = list(responses or [])
        self._default_response = default_response
        self._calls: list[dict[str, Any]] = []

    @property
    def calls(self) -> list[dict[str, Any]]:
        return self._calls

    @property
    def call_count(self) -> int:
        return len(self._calls)

    def set_response(self, response: str, *, index: int | None = None) -> None:
        if index is not None:
            if index < len(self._queue):
                self._queue[index] = response
            else:
                self._queue.extend(
                    self._default_response for _ in range(index - len(self._queue))
                )
                self._queue.append(response)
        else:
            self._queue.append(response)

    def set_responses(self, responses: list[str]) -> None:
        self._queue = list(responses)

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

        content = self._next_response(messages)
        return LLMResponse(
            content=content,
            model=model or "mock",
            usage={"prompt_tokens": 100, "completion_tokens": 50},
        )

    def _next_response(self, messages: list[LLMMessage]) -> str:
        if self._queue:
            return self._queue.pop(0)

        combined = " ".join(message.content.lower() for message in messages)
        if "research planner" in combined:
            return _planner_response(_extract_question(messages))
        if "research synthesizer" in combined:
            return _synthesis_response(messages)
        if "blue agent" in combined or "blue fix" in combined:
            return _blue_response(messages)
        if "red agent" in combined or "red review" in combined:
            return _RED_RESPONSE
        if "research agent" in combined:
            return _research_response(messages)
        return self._default_response


def _extract_question(messages: list[LLMMessage]) -> str:
    text = "\n".join(message.content for message in messages)
    match = re.search(r"Research question:\s*(.+)", text)
    if match:
        return _clean_topic(match.group(1))
    return "the research topic"


def _extract_task(messages: list[LLMMessage]) -> tuple[str, str]:
    text = "\n".join(message.content for message in messages)
    task_match = re.search(r"(?:Generate search queries for|Task):\s*(.+)", text)
    goal_match = re.search(r"Goal:\s*(.+)", text)
    task = (
        _clean_topic(task_match.group(1)) if task_match else _extract_question(messages)
    )
    goal = _clean_topic(goal_match.group(1)) if goal_match else "research the topic"
    return task, goal


def _clean_topic(value: str) -> str:
    value = value.splitlines()[0].strip()
    value = value.strip("\"'`：: ")
    return value or "the research topic"


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", text))


def _planner_response(question: str) -> str:
    if _has_cjk(question):
        tasks = [
            {
                "task_id": "t1",
                "description": f"梳理{question}的定义和背景",
                "goal": f"说明{question}是什么以及为什么重要",
                "dependencies": [],
                "priority": 1,
            },
            {
                "task_id": "t2",
                "description": f"分析{question}的核心组成和工作方式",
                "goal": f"总结{question}的关键机制",
                "dependencies": ["t1"],
                "priority": 2,
            },
            {
                "task_id": "t3",
                "description": f"评估{question}的应用场景和局限",
                "goal": f"给出{question}的实践价值和注意事项",
                "dependencies": ["t1", "t2"],
                "priority": 3,
            },
        ]
    else:
        tasks = [
            {
                "task_id": "t1",
                "description": f"Define and contextualize {question}",
                "goal": f"Explain what {question} is and why it matters",
                "dependencies": [],
                "priority": 1,
            },
            {
                "task_id": "t2",
                "description": f"Analyze the core mechanisms of {question}",
                "goal": f"Summarize the key components of {question}",
                "dependencies": ["t1"],
                "priority": 2,
            },
            {
                "task_id": "t3",
                "description": f"Evaluate applications and limitations of {question}",
                "goal": f"Identify practical uses and caveats for {question}",
                "dependencies": ["t1", "t2"],
                "priority": 3,
            },
        ]
    return json.dumps({"plan_id": "p1", "tasks": tasks}, ensure_ascii=False)


def _research_response(messages: list[LLMMessage]) -> str:
    text = "\n".join(message.content for message in messages)
    task, goal = _extract_task(messages)
    if "reranked source chunks" not in text.lower():
        return json.dumps(
            {
                "task_id": "t1",
                "queries": [task, goal, f"{task} evidence"],
                "summary": f"Generated mock queries for {task}.",
                "evidence": [],
            },
            ensure_ascii=False,
        )

    source_id_match = re.search(r"\[(S\d+)\]", text)
    source_id = source_id_match.group(1) if source_id_match else "S1"
    content_match = re.search(
        r"Content:\s*(.+?)(?:\n\n\[S\d+\]|\n\nExtract evidence|\Z)", text, re.S
    )
    source_text = " ".join((content_match.group(1) if content_match else task).split())
    quote = _first_sentence(source_text) or source_text[:160]
    if _has_cjk(task):
        claim = quote
        summary = f"找到与{task}相关的离线模拟资料。"
    else:
        claim = quote
        summary = f"Found offline mock evidence related to {task}."

    return json.dumps(
        {
            "task_id": "t1",
            "queries": [task, goal, f"{task} evidence"],
            "summary": summary,
            "evidence": [
                {
                    "evidence_id": "E1",
                    "claim": claim,
                    "quote": quote,
                    "citation": f"Mock source for: {task}",
                    "source_url": "",
                    "source_id": source_id,
                    "confidence": 0.85,
                }
            ],
        },
        ensure_ascii=False,
    )


def _first_sentence(text: str) -> str:
    if not text:
        return ""
    match = re.match(r"(.+?[。.!?])(?:\s|$)", text)
    return match.group(1).strip() if match else text[:160].strip()


def _synthesis_response(messages: list[LLMMessage]) -> str:
    question = _extract_question(messages)
    text = "\n".join(message.content for message in messages if message.role == "user")
    evidence_ids = re.findall(r"\[(E\d+)\]", text)
    unique_ids = list(dict.fromkeys(evidence_ids)) or ["E1"]
    citations = " ".join(f"[{evidence_id}]" for evidence_id in unique_ids)
    first_id = f"[{unique_ids[0]}]"

    if _has_cjk(question):
        return f"""## Executive Summary

本报告基于离线 mock 证据，对“{question}”进行简要说明 {first_id}。

## Background

从已收集的资料看，“{question}”可以先从定义、背景和使用动机理解 {first_id}。

## Analysis

围绕“{question}”的核心分析包括基本概念、关键机制、应用场景和潜在局限 {citations}。

## Limitations

- 当前为离线 mock 运行，只用于验证 pipeline，不代表真实检索结论
- 如需真实资料，请使用 --mode real 并配置 retriever、LLM、embedding、reranker 和 Milvus

## References

- {citations} Mock source
"""

    return f"""## Executive Summary

This report gives a concise offline mock overview of {question} {first_id}.

## Background

The gathered mock evidence frames {question} through its definition, context, and motivation {first_id}.

## Analysis

The core analysis of {question} covers its concepts, mechanisms, applications, and limitations {citations}.

## Limitations

- This is an offline mock run for pipeline validation, not a real retrieval result
- Use --mode real with configured retriever, LLM, embedding, reranker, and Milvus for real evidence

## References

- {citations} Mock source
"""


def _blue_response(messages: list[LLMMessage]) -> str:
    text = "\n".join(message.content for message in messages if message.role == "user")
    is_zh = _has_cjk(text)
    content = (
        "离线 mock 修复仅验证 Red-Blue 流程，未新增真实事实。"
        if is_zh
        else "Offline mock repair only verifies the Red-Blue flow and adds no real-world facts."
    )
    return json.dumps(
        {
            "actions": [
                {
                    "action_id": "B1",
                    "type": "VERIFY",
                    "target": "Limitations",
                    "content": content,
                    "evidence_id": None,
                }
            ]
        },
        ensure_ascii=False,
    )
