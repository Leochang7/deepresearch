# LLM Safety / 大语言模型安全

## Overview

As large language models become more capable and widely deployed, safety concerns have become a central focus of AI research and policy. Key challenges include hallucination, bias, misuse, and the difficulty of aligning model behavior with human values.

## 概述

随着大语言模型变得越来越强大并被广泛部署，安全问题已成为 AI 研究和政策的核心关注点。主要挑战包括幻觉、偏见、滥用以及使模型行为与人类价值观保持一致的困难。

## Hallucination and Red-Teaming / 幻觉与红队测试

Hallucination is a major concern in LLM safety — models can generate fluent, confident-sounding text that contains fabricated facts, incorrect citations, or entirely fictional claims. This undermines trust in model outputs, especially in high-stakes domains like healthcare, law, and finance. Red-teaming helps identify vulnerabilities by systematically probing models with adversarial prompts designed to elicit harmful, biased, or inaccurate outputs. Through red-teaming, researchers discover failure modes before deployment and develop targeted mitigations.

幻觉是 LLM 安全中的一个主要问题——模型可以生成流畅、自信的文本，但其中包含捏造的事实、错误的引用或完全虚构的说法。这破坏了对模型输出的信任，尤其是在医疗、法律和金融等高风险领域。红队测试通过系统性地用旨在引发有害、有偏见或不准确输出的对抗性提示来探测模型，从而帮助识别漏洞。通过红队测试，研究人员在部署前发现失败模式并开发有针对性的缓解措施。

## Alignment and Guardrails / 对齐与护栏

Reinforcement Learning from Human Feedback (RLHF) is the primary technique for aligning LLMs with human preferences. RLHF trains a reward model on human comparisons of model outputs, then uses reinforcement learning to optimize the language model against this reward signal. Guardrails provide runtime safety by filtering inputs and outputs, blocking harmful content generation, and enforcing content policies. Together, alignment training and runtime guardrails form a defense-in-depth approach to LLM safety.

基于人类反馈的强化学习（RLHF）是使 LLM 与人类偏好保持一致的主要技术。RLHF 在人类对模型输出的比较上训练一个奖励模型，然后使用强化学习针对该奖励信号优化语言模型。护栏通过过滤输入和输出、阻止有害内容生成和强制执行内容策略来提供运行时安全保障。对齐训练和运行时护栏共同构成了 LLM 安全的纵深防御方法。
