# ReAct Framework for LLM Agents

The ReAct framework, introduced by Yao et al. in 2022, is a foundational approach for enabling large language models to interact with external tools and environments. The name stands for "Reasoning and Acting," reflecting its core design of interleaving chain-of-thought reasoning with concrete action execution.

## Core Mechanism

In a typical ReAct agent loop, the model alternates between three types of steps. First, a **thought** step where the model reasons about the current situation and plans what to do next. Second, an **action** step where the model selects and invokes a tool or API call. Third, an **observation** step where the model receives the result of its action. This cycle repeats until the agent reaches a final answer.

## Advantages Over Pure Reasoning

The key insight of ReAct is that reasoning and acting are complementary. Pure reasoning without acting limits the model to its internal knowledge, while acting without reasoning leads to trial-and-error behavior. By interleaving these steps, the agent can plan, execute, observe results, and adjust its strategy dynamically.

## Interpretability

Compared to approaches that separate reasoning from tool use, ReAct provides more interpretable agent behavior since each step includes explicit reasoning traces. The framework supports diverse tools including search engines, calculators, and databases. ReAct has become a standard template for building tool-use agents and influenced frameworks like LangChain and AutoGPT.
