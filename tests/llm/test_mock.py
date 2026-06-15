import json

import pytest

from deepresearch.llm.base import LLMClient, LLMMessage, LLMResponse
from deepresearch.llm.mock import MockLLM


class TestLLMBase:
    def test_llm_message(self):
        msg = LLMMessage(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"

    def test_llm_response(self):
        resp = LLMResponse(content="hi", model="test", usage={"tokens": 10})
        assert resp.content == "hi"
        assert resp.model == "test"

    def test_llm_client_is_abstract(self):
        with pytest.raises(TypeError):
            LLMClient()


class TestMockLLM:
    @pytest.fixture
    def mock(self):
        return MockLLM()

    @pytest.mark.asyncio
    async def test_returns_response(self, mock):
        messages = [LLMMessage(role="user", content="hello")]
        resp = await mock.chat(messages)
        assert isinstance(resp, LLMResponse)
        assert resp.content

    @pytest.mark.asyncio
    async def test_planner_response(self, mock):
        messages = [LLMMessage(role="system", content="You are a planner.")]
        resp = await mock.chat(messages)
        data = json.loads(resp.content)
        assert "plan_id" in data
        assert "tasks" in data
        assert len(data["tasks"]) >= 2

    @pytest.mark.asyncio
    async def test_research_response(self, mock):
        messages = [LLMMessage(role="user", content="research this topic")]
        resp = await mock.chat(messages)
        data = json.loads(resp.content)
        assert "evidence" in data
        assert len(data["evidence"]) >= 1

    @pytest.mark.asyncio
    async def test_synthesis_response(self, mock):
        messages = [LLMMessage(role="user", content="synthesis the findings")]
        resp = await mock.chat(messages)
        assert "Executive Summary" in resp.content

    @pytest.mark.asyncio
    async def test_red_response(self, mock):
        messages = [LLMMessage(role="user", content="red review this report")]
        resp = await mock.chat(messages)
        data = json.loads(resp.content)
        assert "issues" in data
        assert "score" in data

    @pytest.mark.asyncio
    async def test_blue_response(self, mock):
        messages = [LLMMessage(role="user", content="blue fix the issues")]
        resp = await mock.chat(messages)
        data = json.loads(resp.content)
        assert "actions" in data

    @pytest.mark.asyncio
    async def test_default_response(self):
        mock = MockLLM(responses={})
        messages = [LLMMessage(role="user", content="something random")]
        resp = await mock.chat(messages)
        data = json.loads(resp.content)
        assert data == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_custom_response(self):
        mock = MockLLM()
        mock.set_response("custom", '{"answer": 42}')
        messages = [LLMMessage(role="user", content="custom question")]
        resp = await mock.chat(messages)
        assert resp.content == '{"answer": 42}'

    @pytest.mark.asyncio
    async def test_tracks_calls(self, mock):
        messages = [LLMMessage(role="user", content="test")]
        await mock.chat(messages, model="mimo", temperature=0.5)
        await mock.chat(messages)

        assert mock.call_count == 2
        assert mock.calls[0]["model"] == "mimo"
        assert mock.calls[0]["temperature"] == 0.5
        assert mock.calls[1]["model"] is None

    @pytest.mark.asyncio
    async def test_usage_in_response(self, mock):
        messages = [LLMMessage(role="user", content="test")]
        resp = await mock.chat(messages)
        assert "prompt_tokens" in resp.usage
        assert "completion_tokens" in resp.usage

    @pytest.mark.asyncio
    async def test_json_mode_param(self, mock):
        messages = [LLMMessage(role="user", content="test")]
        await mock.chat(messages, json_mode=True)
        assert mock.calls[0]["json_mode"] is True
