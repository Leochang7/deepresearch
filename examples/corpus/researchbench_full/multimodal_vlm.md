# Vision-Language Models

## Architecture Overview

Vision-language models (VLMs) combine visual understanding with language generation to process images alongside text. These models have become increasingly capable with the release of systems like GPT-4V, LLaVA, and Gemini that can reason about visual content in natural language.

## Visual Encoding

VLMs use a visual encoder to convert images into token-like representations that the language model can process. Common visual encoders include Vision Transformer (ViT) variants and CLIP-based encoders. The visual tokens are typically projected into the same embedding space as text tokens through a learned projection layer.

## LLaVA Architecture

LLaVA (Large Language and Vision Assistant) connects a CLIP visual encoder to a Vicuna language model through a learned projection layer. This simple architecture demonstrated that effective vision-language understanding can be achieved without complex cross-attention modules. The projection layer maps visual features into the language model's input space.

## Cross-Attention Approaches

More sophisticated architectures like Flamingo and Qwen-VL use cross-attention mechanisms to allow text tokens to attend to visual features during generation. This provides finer-grained integration between modalities but at higher computational cost. Cross-attention enables the model to selectively focus on relevant image regions when generating each word.
