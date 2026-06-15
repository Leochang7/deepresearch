import json

import pytest

from deepresearch.llm.base import LLMMessage
from deepresearch.llm.mock import MockLLM


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("prompt", "expected_key"),
    [
        ("You are a research planner.", "plan_id"),
        ("You are a research agent.", "evidence"),
        ("You are a red agent.", "issues"),
        ("You are a blue agent.", "actions"),
    ],
)
async def test_semantic_json_responses(prompt, expected_key):
    response = await MockLLM().chat([LLMMessage(role="system", content=prompt)])
    assert expected_key in json.loads(response.content)


@pytest.mark.asyncio
async def test_semantic_synthesis_response():
    response = await MockLLM().chat(
        [LLMMessage(role="system", content="You are a research synthesizer.")]
    )
    assert "Executive Summary" in response.content


@pytest.mark.asyncio
async def test_agents_do_not_depend_on_global_call_order():
    mock = MockLLM()
    research = await mock.chat(
        [LLMMessage(role="system", content="You are a research agent.")]
    )
    planner = await mock.chat(
        [LLMMessage(role="system", content="You are a research planner.")]
    )

    assert "evidence" in json.loads(research.content)
    assert "tasks" in json.loads(planner.content)


@pytest.mark.asyncio
async def test_custom_responses_are_consumed_then_semantic_fallback_is_used():
    mock = MockLLM(["first", "second"])

    first = await mock.chat([LLMMessage(role="user", content="a")])
    second = await mock.chat([LLMMessage(role="user", content="b")])
    planner = await mock.chat(
        [LLMMessage(role="system", content="You are a research planner.")]
    )

    assert first.content == "first"
    assert second.content == "second"
    assert "plan_id" in json.loads(planner.content)


@pytest.mark.asyncio
async def test_set_response_appends_and_set_responses_replaces_queue():
    mock = MockLLM()
    mock.set_response("appended")
    assert (
        await mock.chat([LLMMessage(role="user", content="anything")])
    ).content == "appended"

    mock.set_responses(["replacement"])
    assert (
        await mock.chat([LLMMessage(role="user", content="anything")])
    ).content == "replacement"


@pytest.mark.asyncio
async def test_default_response_for_unknown_prompt():
    response = await MockLLM(default_response='{"answer": 42}').chat(
        [LLMMessage(role="user", content="unclassified prompt")]
    )
    assert json.loads(response.content) == {"answer": 42}


@pytest.mark.asyncio
async def test_tracks_calls_and_usage():
    mock = MockLLM()
    response = await mock.chat(
        [LLMMessage(role="user", content="test")],
        model="custom",
        temperature=0.5,
        json_mode=True,
    )

    assert mock.call_count == 1
    assert mock.calls[0]["temperature"] == 0.5
    assert mock.calls[0]["json_mode"] is True
    assert response.model == "custom"
    assert "prompt_tokens" in response.usage
