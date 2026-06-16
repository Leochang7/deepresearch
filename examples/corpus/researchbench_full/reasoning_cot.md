# Chain-of-Thought Prompting

Chain-of-thought (CoT) prompting is a technique that significantly improves the reasoning capabilities of large language models. Introduced by Wei et al. in 2022, CoT decomposes complex problems into intermediate reasoning steps rather than jumping directly to an answer.

## Mechanism

In chain-of-thought prompting, the model is guided to reason step by step before producing a final answer. Few-shot CoT examples demonstrate this pattern by showing worked examples where each intermediate reasoning step is explicitly laid out. The model then follows this pattern on new problems, generating intermediate steps that lead to more accurate answers.

## Performance Impact

CoT prompting was shown to dramatically improve performance on arithmetic reasoning, commonsense reasoning, and symbolic reasoning tasks. On GSM8K math problems, CoT improved PaLM 540B accuracy from 17.9% to 58.1%. The benefits scale with model size, with smaller models showing less improvement from CoT.

## Zero-Shot Chain-of-Thought

A simple variant, zero-shot CoT, appends "Let's think step by step" to the prompt. This surprisingly effective approach requires no examples and works across diverse reasoning tasks. It demonstrates that large models have latent reasoning abilities that can be activated through appropriate prompting.
