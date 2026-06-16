# Chain-of-Thought Prompting for LLM Reasoning

Chain-of-thought (CoT) prompting is a technique that improves reasoning in large language models by encouraging them to decompose complex problems into intermediate reasoning steps. Introduced by Wei et al. in 2022, this approach has become one of the most important methods for eliciting reliable reasoning from language models.

## Decomposing Complex Problems

The core idea of chain-of-thought prompting is to break down a difficult problem into a sequence of simpler, intermediate steps. Rather than asking a model to produce a final answer directly, CoT guides the model to show its reasoning process step by step. This decomposition makes complex problems more tractable because each intermediate step is individually simpler than the overall problem.

## How It Works

Chain-of-thought prompting typically involves including worked examples in the prompt that demonstrate step-by-step reasoning. When the model encounters a new problem, it follows the same pattern of intermediate reasoning. For instance, a math word problem might be broken into steps: identifying relevant quantities, setting up equations, and computing the final answer.

## Empirical Results

Wei et al. demonstrated that CoT prompting dramatically improves performance on arithmetic, commonsense, and symbolic reasoning benchmarks. On the GSM8K math benchmark, chain-of-thought prompting improved PaLM 540B accuracy from 17.9% to 58.1%. The technique scales with model size, showing the greatest benefits in models with more than 100 billion parameters.

## Theoretical Significance

Chain-of-thought reasoning represents a form of computational depth — by generating intermediate steps, the model effectively uses its output as working memory. This allows the model to allocate more computation to harder problems, similar to how humans think through complex questions by reasoning through intermediate steps rather than jumping directly to conclusions.
