"""Tests that agents and judge evaluator accept a custom PromptProvider."""

from __future__ import annotations

from unittest.mock import MagicMock

from deepresearch.agents.blue_agent import BlueAgent
from deepresearch.agents.planner import PlannerAgent
from deepresearch.agents.red_agent import RedAgent
from deepresearch.agents.synthesizer import Synthesizer
from deepresearch.llm.mock import MockLLM


def test_planner_accepts_custom_provider():
    mock_provider = MagicMock()
    mock_provider.get.return_value = "Custom planner prompt"
    agent = PlannerAgent(llm=MockLLM(), prompt_provider=mock_provider)
    assert agent._system_prompt == "Custom planner prompt"
    mock_provider.get.assert_called_once_with("planner")


def test_planner_defaults_to_local_provider():
    agent = PlannerAgent(llm=MockLLM())
    # Default provider loads from the real prompts directory
    assert agent._system_prompt  # should be non-empty (prompt file exists)


def test_red_agent_accepts_custom_provider():
    mock_provider = MagicMock()
    mock_provider.get.return_value = "Custom red agent prompt"
    agent = RedAgent(llm=MockLLM(), prompt_provider=mock_provider)
    assert agent._system_prompt == "Custom red agent prompt"
    mock_provider.get.assert_called_once_with("red_agent")


def test_blue_agent_accepts_custom_provider():
    mock_provider = MagicMock()
    mock_provider.get.return_value = "Custom blue agent prompt"
    agent = BlueAgent(llm=MockLLM(), prompt_provider=mock_provider)
    assert agent._system_prompt == "Custom blue agent prompt"
    mock_provider.get.assert_called_once_with("blue_agent")


def test_synthesizer_accepts_custom_provider():
    mock_provider = MagicMock()
    mock_provider.get.return_value = "Custom synthesizer prompt"
    agent = Synthesizer(llm=MockLLM(), prompt_provider=mock_provider)
    # Synthesizer augments the base prompt via build_profile_prompt
    assert "Custom synthesizer prompt" in agent._system_prompt
    mock_provider.get.assert_called_once_with("synthesizer")
