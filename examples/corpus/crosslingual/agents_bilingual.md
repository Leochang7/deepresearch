# LLM Agents / 大语言模型智能体

## Overview

LLM agents extend large language models beyond simple text generation by enabling them to use external tools, take actions in the environment, and reason about their observations. The ReAct framework (Reasoning + Acting) is a foundational paradigm that interleaves reasoning and acting in an iterative loop.

## 概述

LLM 智能体将大语言模型的能力从简单的文本生成扩展到使用外部工具、在环境中采取行动并对观察结果进行推理。ReAct 框架（推理 + 行动）是一个基础范式，在迭代循环中交替进行推理和行动。

## ReAct Framework / ReAct 框架

ReAct interleaves reasoning and acting in a unified framework. At each step, the agent first reasons about the current state and decides what action to take, then executes the action using available tools, and finally observes the result to inform the next reasoning step. This tight coupling of thought and action allows agents to handle complex, multi-step tasks that require external information or real-world interaction.

ReAct 在统一框架中交替进行推理和行动。在每个步骤中，智能体首先对当前状态进行推理并决定采取什么行动，然后使用可用工具执行行动，最后观察结果以指导下一步推理。这种思想和行动的紧密耦合使智能体能够处理需要外部信息或现实世界交互的复杂多步骤任务。

## Function Calling and Tool Use / 函数调用与工具使用

Modern LLM providers support function calling natively. OpenAI and Anthropic both provide structured tool use APIs that allow models to invoke external functions with typed parameters. Function calling supported by OpenAI/Anthropic enables agents to search the web, query databases, execute code, call APIs, and interact with various software systems. Multi-agent systems further extend this paradigm by orchestrating multiple specialized agents that collaborate to solve complex problems.

现代 LLM 原生支持函数调用。OpenAI 和 Anthropic 都提供结构化的工具使用 API，允许模型使用类型化参数调用外部函数。OpenAI/Anthropic 支持的函数调用使智能体能够搜索网络、查询数据库、执行代码、调用 API 以及与各种软件系统交互。多智能体系统通过编排多个协作解决复杂问题的专业智能体来进一步扩展这一范式。
