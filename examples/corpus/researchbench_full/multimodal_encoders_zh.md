# 视觉编码器架构

## 多模态模型中的视觉编码器

多模态大模型的视觉编码器负责将图像转换为语言模型可以处理的token表示。主流的视觉编码器架构包括Vision Transformer（ViT）、CLIP和SigLIP，它们各自采用不同的训练策略和架构设计。

## Vision Transformer (ViT)

Vision Transformer将图像分割为固定大小的patch（如16x16像素），将每个patch视为一个token，然后应用标准的transformer自注意力机制。ViT通过全局自注意力捕获图像patch之间的长距离依赖关系。与CNN相比，ViT在大规模数据上训练时表现出更强的扩展性。

## CLIP 对比学习

CLIP（Contrastive Language-Image Pre-training）使用对比学习将视觉和文本表示对齐到共享空间。CLIP在4亿图像-文本对上训练，通过对比损失函数使匹配的图像和文本嵌入接近，不匹配的远离。这种训练方式赋予了CLIP强大的零样本视觉理解能力。

## SigLIP 改进

SigLIP 对CLIP的训练目标进行了改进，用sigmoid损失替代softmax损失。这种改变使得每个图像-文本对的损失计算独立于batch中的其他样本，允许更高效的分布式训练。SigLIP在保持CLIP性能的同时实现了更好的训练效率和扩展性。

## 在大模型中的应用

现代多模态大模型通常采用预训练的视觉编码器作为视觉理解的基础。LLaVA使用CLIP编码器，InternVL使用ViT-6B，而Qwen-VL使用自研的视觉编码器。视觉编码器的选择直接影响模型的视觉理解粒度和多模态融合效果。
