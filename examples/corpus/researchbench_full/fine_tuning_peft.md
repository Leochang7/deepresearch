# Parameter-Efficient Fine-Tuning Methods

## PEFT Overview

Parameter-Efficient Fine-Tuning (PEFT) encompasses a family of techniques that adapt large pretrained models by updating only a small fraction of parameters. This approach reduces computational and memory requirements while achieving competitive performance with full fine-tuning.

## Prefix Tuning

Prefix tuning prepends trainable continuous vectors to the key and value matrices in each attention layer. These soft prompts steer the model behavior without modifying the underlying weights. Unlike discrete prompts, prefix tuning learns continuous representations that are more expressive and task-specific.

## Full Fine-Tuning Comparison

Full fine-tuning updates all model parameters on the target task data. While this achieves the highest performance ceiling, it requires significant GPU memory proportional to the model size. For a 70B parameter model, full fine-tuning needs hundreds of gigabytes of GPU memory.

## LoRA Performance

LoRA achieves near-full-finetune performance with less than 1% of parameters on most benchmarks. Research shows that LoRA with rank 16 matches or exceeds full fine-tuning on classification, generation, and instruction-following tasks. The performance gap widens only for tasks requiring dramatic behavioral changes.

## QLoRA

QLoRA combines 4-bit NormalFloat quantization with LoRA adapters to enable fine-tuning on consumer hardware. NF4 (NormalFloat4) is a data type specifically designed for normally distributed neural network weights. Double quantization further reduces memory overhead by quantizing the quantization constants themselves. QLoRA made it possible to fine-tune 65B parameter models on a single 48GB GPU.
