# Few-Shot Chain-of-Thought Prompting

Few-shot chain-of-thought prompting combines the power of in-context learning with step-by-step reasoning demonstrations. By providing exemplar questions with detailed reasoning traces in the prompt, this technique guides language models to reason through problems systematically rather than producing answers without explanation.

## Exemplars with Reasoning

In few-shot CoT prompting, each example in the prompt includes not just a question and answer, but a complete step-by-step reasoning trace. These exemplars demonstrate the desired reasoning pattern, showing the model how to break problems into intermediate steps. For example, a math exemplar might show: identifying given information, determining what to calculate, performing intermediate computations, and stating the final answer.

## In-Context Learning for Reasoning

Few-shot CoT leverages in-context learning, where the model adapts its behavior based on examples provided in the prompt without any parameter updates. The model recognizes the reasoning pattern from the exemplars and applies it to new questions. This makes few-shot CoT accessible and flexible — practitioners can change the model's reasoning behavior simply by modifying the prompt examples.

## Selecting Effective Exemplars

The choice of exemplars significantly affects performance. Effective few-shot examples should cover diverse reasoning patterns, use clear step-by-step formatting, and match the difficulty level of target problems. Research has shown that even randomly selected exemplars can improve reasoning, but carefully chosen examples that demonstrate relevant reasoning strategies produce the best results.

## Prompt Design Principles

Successful few-shot CoT prompts share several characteristics: each reasoning step is clearly delineated, intermediate conclusions are explicitly stated, and the chain of reasoning leads logically to the final answer. The prompt format should be consistent across exemplars so the model can reliably follow the demonstrated pattern when generating its own step-by-step response.
