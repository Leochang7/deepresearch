# Advanced Embedding Models

## Matryoshka Representation Learning

Modern embedding models like text-embedding-3 have introduced Matryoshka representation learning, a technique that allows embedding vectors to be truncated to smaller dimensions without retraining. A model trained with Matryoshka objectives produces embeddings where the first d dimensions form a valid lower-dimensional representation. This enables flexible trade-offs between storage cost and retrieval quality at inference time.

## Instruction-Tuned Embeddings

Models like E5-Mistral and BGE-M3 use instruction tuning to create task-aware embeddings. Instead of encoding query and document with the same prompt, these models follow natural language task descriptions such as "Represent this document for retrieval." This instruction-following capability improves zero-shot performance across diverse retrieval tasks without task-specific fine-tuning.

## Training with Hard Negatives

Contrastive learning with hard negatives has become a key training technique for high-quality embeddings. Instead of using random negatives, the training pipeline mines difficult negative examples that are semantically similar to the query but factually incorrect. This pushes the embedding space to make finer-grained distinctions. Methods like in-batch negatives, cross-encoder distillation, and iterative mining have driven significant improvements on the MTEB benchmark leaderboard.
