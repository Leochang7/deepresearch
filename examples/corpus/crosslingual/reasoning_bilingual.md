# Reasoning Methods for LLMs / 大语言模型推理方法

## Overview

Large language models can be prompted to perform complex reasoning tasks through carefully designed prompting strategies. Chain-of-thought (CoT) prompting is one of the most effective techniques, enabling models to decompose problems into intermediate steps before arriving at a final answer.

## 概述

大语言模型可以通过精心设计的提示策略来执行复杂推理任务。思维链（Chain-of-Thought, CoT）提示是最有效的技术之一，它使模型能够将问题分解为中间步骤，然后得出最终答案。

## Chain-of-Thought Prompting / 思维链提示

Chain-of-thought prompting decomposes problems into intermediate reasoning steps, allowing the model to show its work rather than jumping directly to a conclusion. By providing examples that demonstrate step-by-step reasoning, few-shot CoT guides the model through a similar reasoning process for new problems. This technique has been shown to significantly improve performance on arithmetic, commonsense, and symbolic reasoning tasks.

思维链提示将问题分解为中间推理步骤，使模型能够展示推理过程，而不是直接跳到结论。通过提供展示逐步推理的示例，少样本 CoT 引导模型对新问题进行类似的推理过程。该技术已被证明能显著提高算术、常识和符号推理任务的性能。

## Self-Consistency and Advanced Methods / 自一致性与高级方法

Self-consistency extends CoT by sampling multiple reasoning paths and selecting the most common answer through majority voting. This approach leverages the insight that correct reasoning paths are more likely to converge on the same answer. Few-shot CoT guides step-by-step reasoning by including worked examples in the prompt, while zero-shot CoT simply appends "Let's think step by step" to encourage the model to reason explicitly.

自一致性通过采样多条推理路径并通过多数投票选择最常见的答案来扩展 CoT。这种方法利用了正确推理路径更可能收敛到同一答案的洞察。少样本 CoT 通过在提示中包含解题示例来引导逐步推理，而零样本 CoT 则简单地附加"让我们逐步思考"来鼓励模型进行显式推理。
