# LLM Evaluation / 大语言模型评估

## Overview

Evaluating large language models requires a combination of automated benchmarks, human evaluation, and domain-specific metrics. No single metric captures all aspects of model quality, making comprehensive evaluation a multifaceted challenge.

## 概述

评估大语言模型需要结合自动化基准测试、人工评估和领域特定指标。没有任何单一指标能够全面衡量模型质量，这使得综合评估成为一个多维度的挑战。

## Standard Benchmarks / 标准基准测试

MMLU (Massive Multitask Language Understanding) measures knowledge across domains including STEM, humanities, social sciences, and more. It tests models on multiple-choice questions spanning 57 subjects. Other important benchmarks include HellaSwag for commonsense reasoning, TruthfulQA for factuality, and GSM8K for mathematical problem solving. GLUE and SuperGLUE remain foundational benchmarks for evaluating natural language understanding capabilities across tasks like textual entailment, sentiment analysis, and coreference resolution.

MMLU（大规模多任务语言理解）衡量跨领域知识，涵盖 STEM、人文、社会科学等多个学科。它通过跨越 57 个学科的多选题来测试模型。其他重要基准包括用于常识推理的 HellaSwag、用于事实性的 TruthfulQA 和用于数学问题求解的 GSM8K。GLUE 和 SuperGLUE 仍然是评估自然语言理解能力的基础基准，涵盖文本蕴含、情感分析和共指消解等任务。

## Human Evaluation and Automated Metrics / 人工评估与自动化指标

Human evaluation remains important for assessing qualities that automated metrics cannot capture, such as coherence, helpfulness, creativity, and safety. Automated metrics like BLEU, ROUGE, and BERTScore provide scalable evaluation but often correlate poorly with human judgments for open-ended generation tasks. The most effective evaluation strategies combine both approaches: using automated benchmarks for rapid iteration and human evaluation for final quality assurance.

人工评估对于衡量自动化指标无法捕获的质量维度仍然至关重要，例如连贯性、有用性、创造性和安全性。BLEU、ROUGE 和 BERTScore 等自动化指标提供了可扩展的评估，但对于开放式生成任务，它们与人类判断的相关性往往较差。最有效的评估策略是将两种方法结合使用：使用自动化基准进行快速迭代，使用人工评估进行最终质量保证。
