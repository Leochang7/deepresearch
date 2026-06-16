# Long-Context and Memory-Augmented LLMs

## Extending Context Windows

Long-context language models address the fundamental limitation of fixed attention windows in transformers. Standard self-attention has quadratic complexity with sequence length, making it impractical for very long documents. Several architectural approaches have been developed to handle this challenge.

## Sliding Window Attention

Sliding window attention limits each token's attention to a fixed local window of neighboring tokens. This reduces complexity from quadratic to linear in sequence length. Mistral models use this approach with a window size of 4096 tokens. While efficient, sliding window attention may miss long-range dependencies that span beyond the window.

## RoPE Scaling

Rotary Position Embedding (RoPE) scaling extends the positional encoding range to support longer sequences. By adjusting the base frequency of the rotary embeddings, models trained on shorter contexts can be extended to handle much longer sequences. Code Llama and Llama 2 Long use this technique to extend context from 4K to 100K+ tokens.

## Ring Attention

Ring Attention distributes attention computation across multiple devices by organizing them in a ring topology. Each device computes attention for a segment of the sequence and passes results to the next device. This enables processing of million-token sequences that would be impossible on a single device.
