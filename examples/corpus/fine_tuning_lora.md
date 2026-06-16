# LoRA: Low-Rank Adaptation for Efficient Fine-Tuning

Low-Rank Adaptation (LoRA), introduced by Hu et al. in 2021, is a parameter-efficient fine-tuning method that dramatically reduces the computational cost of adapting large language models. Instead of updating all model weights during fine-tuning, LoRA decomposes weight updates into low-rank matrices, enabling efficient adaptation with minimal parameters.

## How LoRA Works

LoRA freezes the pretrained model weights entirely and injects trainable low-rank decomposition matrices into each transformer layer. For a weight matrix W of dimension d x d, LoRA represents the update as the product of two smaller matrices A (d x r) and B (r x d), where r is the rank, typically much smaller than d (e.g., r=8 or r=16).

## Low-Rank Decomposition

The key insight is that weight updates during fine-tuning have low intrinsic rank. Rather than learning a full d x d update matrix, LoRA captures the essential changes through the rank-r decomposition. This reduces trainable parameters by factors of 100x to 1000x while preserving most of the adaptation quality achieved by full fine-tuning.

## Preserving Pretrained Knowledge

Because LoRA keeps the original pretrained weights frozen, the model retains its general capabilities while learning task-specific adaptations. The low-rank matrices A and B are merged with the original weights at inference time, introducing no additional latency. This approach to adaptation is particularly valuable for large models where full fine-tuning would require prohibitive memory.

## Practical Impact

LoRA has become one of the most widely adopted parameter-efficient fine-tuning techniques. It enables researchers and practitioners to fine-tune billion-parameter models on consumer hardware, democratizing access to custom model adaptation. The low-rank decomposition approach has also inspired variants like QLoRA, which combines LoRA with quantization for even greater efficiency.
