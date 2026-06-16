# LLM Evaluation Benchmarks

## Major Benchmarks

The evaluation of large language models relies on a growing ecosystem of standardized benchmarks. MMLU (Massive Multitask Language Understanding) measures knowledge across 57 domains including STEM, humanities, social sciences, and more. It has become one of the most widely reported benchmarks for comparing model capabilities.

## Code Generation

HumanEval, developed by OpenAI, tests code generation capabilities through 164 Python programming problems. Models must generate function implementations that pass unit tests. The pass@k metric measures the probability that at least one of k generated samples is correct.

## Comprehensive Frameworks

HELM (Holistic Evaluation of Language Models) by Stanford provides a comprehensive evaluation framework that assesses models across multiple dimensions including accuracy, calibration, robustness, fairness, bias, and toxicity. Rather than a single leaderboard, HELM provides multi-dimensional profiles of model capabilities.

## Limitations of Benchmarks

Static benchmarks suffer from contamination risks as models may be trained on test data. Benchmark saturation occurs when top models achieve near-perfect scores, reducing discriminative power. The field increasingly values dynamic evaluation and human preference assessments alongside static benchmarks.
