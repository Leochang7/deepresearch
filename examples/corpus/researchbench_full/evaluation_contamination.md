# Benchmark Contamination and Evaluation Reliability

## Data Leakage Problem

Contamination occurs when benchmark test data leaks into LLM training corpora. Since modern LLMs are trained on vast web corpora, popular benchmark questions and answers may be inadvertently included. This inflates benchmark scores and makes models appear more capable than they actually are on novel tasks.

## N-gram Overlap Detection

N-gram overlap detection is the most straightforward contamination detection method. It compares n-gram sequences in benchmark test sets against the model's training data. High overlap rates indicate potential contamination. However, this method has limitations since partial overlap or paraphrased contamination may not be detected.

## Membership Inference Attacks

Membership inference attacks determine whether specific examples were present in the training data. These attacks exploit the observation that models tend to assign higher likelihood to memorized sequences. By comparing model likelihoods on benchmark data versus held-out data, researchers can estimate contamination levels.

## Implications

Contamination fundamentally undermines the reliability of evaluation. When benchmark scores are inflated by data leakage, the research community cannot accurately track progress. This has led to increased emphasis on held-out evaluation sets, dynamic benchmarks, and contamination-aware evaluation protocols that account for potential leakage.
