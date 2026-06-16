# LoRA: Low-Rank Adaptation / 低秩适配

## Overview

LoRA (Low-Rank Adaptation) is a parameter-efficient fine-tuning technique that has revolutionized how we adapt large language models to downstream tasks. Instead of updating all model weights during training, LoRA decomposes weight updates into low-rank matrices, dramatically reducing the number of trainable parameters.

## 概述

LoRA（低秩适配，Low-Rank Adaptation）是一种参数高效的微调技术，它革新了我们将大语言模型适应下游任务的方式。LoRA 不需要在训练时更新所有模型权重，而是将权重更新分解为低秩矩阵（low-rank decomposition），从而大幅减少可训练参数的数量。

## How LoRA Works / 工作原理

The core insight of LoRA is that the weight update matrix during fine-tuning has a low intrinsic rank. LoRA decomposes weight updates into low-rank matrices by introducing two small trainable matrices A and B, where the original weight update DW is approximated as DW = B * A. During inference, these low-rank matrices are merged back into the original weights with no additional latency.

LoRA 的核心洞察在于，微调过程中的权重更新矩阵具有较低的内在秩。LoRA 通过引入两个小的可训练矩阵 A 和 B 来将权重更新分解为低秩矩阵，其中原始权重更新 DW 被近似为 DW = B * A。在推理时，这些低秩矩阵会合并回原始权重中，不会带来额外的延迟。

## Memory Efficiency / 内存效率

LoRA reduces memory requirements for fine-tuning by orders of magnitude. While full fine-tuning of a 7B parameter model requires storing gradients and optimizer states for all parameters, LoRA only needs to update a fraction of a percent of the total weights. This makes it possible to fine-tune large models on consumer GPUs with limited VRAM.

LoRA 将微调所需的内存降低了数个数量级。对一个 70 亿参数的模型进行全量微调需要存储所有参数的梯度和优化器状态，而 LoRA 只需更新总权重的百分之几甚至更少。这使得在显存有限的消费级 GPU 上微调大模型成为可能。低秩适配技术因此成为目前最流行的 PEFT 方法之一。
