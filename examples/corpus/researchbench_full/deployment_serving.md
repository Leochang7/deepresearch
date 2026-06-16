# LLM Serving and Deployment

## Efficient Inference

Serving large language models efficiently in production requires techniques to maximize throughput and minimize latency. The autoregressive nature of LLM generation, where each token depends on all previous tokens, creates unique optimization challenges compared to traditional model serving.

## KV-Cache

The KV-cache stores computed key-value pairs from previous tokens to avoid redundant computation during autoregressive generation. Without KV-cache, generating each new token would require recomputing attention over all previous tokens. KV-cache is the most fundamental optimization for LLM inference, reducing generation time from quadratic to linear in sequence length.

## Continuous Batching

Continuous batching dynamically groups incoming requests to maximize GPU utilization. Unlike static batching that waits for all requests in a batch to complete, continuous batching allows new requests to join a batch as soon as a slot opens. This approach, implemented in vLLM and TensorRT-LLM, significantly improves throughput for variable-length requests.

## Tensor Parallelism

Tensor parallelism splits model weight matrices across multiple GPUs for faster inference. Each GPU computes a portion of the matrix multiplication, and results are combined through communication primitives. This technique is essential for serving models that exceed the memory of a single GPU.
