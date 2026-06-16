# LoRA: Low-Rank Adaptation

LoRA (Low-Rank Adaptation) is a parameter-efficient fine-tuning method that has become the dominant approach for adapting large language models to downstream tasks. Introduced by Hu et al. in 2021, LoRA decomposes weight updates into low-rank matrices rather than updating the full weight matrices.

## Mechanism

Instead of fine-tuning all parameters of a pretrained model, LoRA injects trainable low-rank decomposition matrices into each transformer layer. Specifically, for a pretrained weight matrix W, LoRA adds a low-rank update W + BA where B and A are much smaller matrices. The rank r is typically much smaller than the original dimensions (e.g., r=8 or r=16).

## Parameter Efficiency

LoRA reduces trainable parameters by orders of magnitude while maintaining performance comparable to full fine-tuning. For a 7B parameter model, LoRA might only train 0.1% to 1% of total parameters. This dramatically reduces GPU memory requirements and training time.

## Adapter Layers

The broader family of adapter-based approaches inserts small trainable modules between frozen transformer layers. While adapters add new layers, LoRA modifies existing weight matrices through additive low-rank updates. Both approaches keep the original model weights frozen and only train the added parameters.

## Practical Impact

LoRA has enabled fine-tuning of large models on consumer GPUs and made model customization accessible to researchers with limited compute resources. The trained LoRA weights can be easily shared and merged with the base model at inference time.
