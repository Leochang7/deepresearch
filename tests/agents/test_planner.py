import json

import pytest

from deepresearch.agents.planner import PlannerAgent
from deepresearch.llm.mock import MockLLM
from deepresearch.schemas.task import ResearchPlan


class TestPlannerAgent:
    @pytest.fixture
    def llm(self):
        return MockLLM()

    @pytest.fixture
    def agent(self, llm):
        return PlannerAgent(llm)

    @pytest.mark.asyncio
    async def test_plan_returns_research_plan(self, agent):
        plan = await agent.plan("What are the trends in LLM agents?")
        assert isinstance(plan, ResearchPlan)
        assert plan.question == "What are the trends in LLM agents?"

    @pytest.mark.asyncio
    async def test_plan_has_tasks(self, agent):
        plan = await agent.plan("test question")
        assert len(plan.tasks) >= 1
        assert all(t.task_id for t in plan.tasks)

    @pytest.mark.asyncio
    async def test_plan_has_plan_id(self, agent):
        plan = await agent.plan("test")
        assert plan.plan_id

    @pytest.mark.asyncio
    async def test_plan_with_custom_response(self, llm):
        custom_response = json.dumps(
            {
                "plan_id": "p-custom",
                "tasks": [
                    {
                        "task_id": "t1",
                        "description": "First task",
                        "dependencies": [],
                        "priority": 1,
                    },
                    {
                        "task_id": "t2",
                        "description": "Second task",
                        "dependencies": ["t1"],
                        "priority": 2,
                    },
                ],
            }
        )
        llm.set_responses([custom_response])
        agent = PlannerAgent(llm)
        plan = await agent.plan("any question")
        assert plan.plan_id == "p-custom"
        assert len(plan.tasks) == 2
        assert plan.tasks[1].dependencies == ["t1"]

    @pytest.mark.asyncio
    async def test_plan_fallback_on_bad_json(self, llm):
        llm.set_responses(["This is not JSON at all!!! [[["])
        agent = PlannerAgent(llm)
        plan = await agent.plan("bad question")
        assert isinstance(plan, ResearchPlan)
        assert len(plan.tasks) == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "tasks",
        [
            [],
            [
                {
                    "task_id": "t1",
                    "description": "first",
                    "dependencies": ["missing"],
                }
            ],
            [
                {"task_id": "t1", "description": "first", "dependencies": ["t2"]},
                {"task_id": "t2", "description": "second", "dependencies": ["t1"]},
            ],
            [
                {"task_id": "t1", "description": "first"},
                {"task_id": "t1", "description": "duplicate"},
            ],
        ],
    )
    async def test_invalid_dag_falls_back_to_valid_single_task(self, llm, tasks):
        llm.set_responses([json.dumps({"plan_id": "bad", "tasks": tasks})])
        plan = await PlannerAgent(llm).plan("research question")

        assert len(plan.tasks) == 1
        assert plan.tasks[0].task_id == "t1"
        assert plan.tasks[0].description == "research question"
