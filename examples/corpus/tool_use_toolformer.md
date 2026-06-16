# Toolformer: Learning Tool Use Through Self-Supervised Training

Toolformer, introduced by Meta AI Research in 2023, represents a novel approach to teaching language models when and how to use external tools. Unlike methods that rely on human demonstrations or reinforcement learning, Toolformer learns tool use through a self-supervised training process applied directly to web text data.

## Self-Supervised Approach

The core innovation of Toolformer is its self-supervised methodology. The model is first fine-tuned to generate API calls within text, then a filtering step selects only the API calls that genuinely improve the model's ability to predict subsequent tokens. This creates a training signal without requiring human annotation of when tools should be used.

## Training Process

During training, the model learns to insert API calls at appropriate points in the text. For example, when encountering a calculation, the model learns to call a calculator; when facing a factual question, it may call a search API. The training data consists of web text augmented with API call demonstrations that the model generates and self-evaluates.

## Token-Level Decisions

A distinctive feature of Toolformer is that tool use decisions are made at the token level during generation. Rather than making a single upfront decision about whether to use a tool, the model continuously evaluates whether an API call would be helpful as it generates each token. This allows for flexible, context-sensitive tool use.

## Significance

Toolformer demonstrated that tool use capabilities can be learned directly from web text without explicit supervision. The approach scales to multiple tools and has influenced subsequent research on integrating external capabilities into language models through learned rather than prompted behavior.
