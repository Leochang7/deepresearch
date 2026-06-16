# Model Compression / 模型压缩

Knowledge distillation trains a smaller student model to imitate a larger teacher model. The goal is to transfer useful behavior while reducing serving cost.

知识蒸馏通常让较小的 student model 学习较大的 teacher model 的输出分布或中间表示，从而在保持能力的同时降低推理成本。

Quantization reduces numerical precision of weights or activations to lower memory and latency. For example, moving from full precision to 8-bit or 4-bit weights can make deployment cheaper.

量化会降低权重或激活值的数值精度，以减少显存占用和推理延迟，但需要校准或量化感知训练来控制精度损失。
