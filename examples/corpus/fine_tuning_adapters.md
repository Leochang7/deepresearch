# Adapter Layers for Efficient Model Fine-Tuning

Adapter layers are a parameter-efficient fine-tuning technique that inserts small trainable modules between the frozen layers of a pretrained transformer model. Introduced by Houlsby et al. in 2019, adapters enable task-specific adaptation by training only the newly inserted parameters while keeping the original model weights unchanged.

## How Adapters Work

An adapter layer typically consists of a down-projection, a non-linear activation, and an up-projection. The input is first projected to a lower dimension, passed through a non-linearity, then projected back to the original dimension. This bottleneck architecture ensures that each adapter module contains very few trainable parameters compared to the surrounding transformer layers.

## Frozen Base Model

The key principle of adapter-based fine-tuning is that the original transformer weights remain completely frozen during training. Only the adapter modules are updated, which typically constitute less than 5% of the total model parameters. This approach preserves the general knowledge encoded in the pretrained model while adding task-specific capabilities through the inserted modules.

## Placement in Transformer Layers

Adapter modules are inserted between the self-attention and feed-forward sub-layers of each transformer block. Some implementations place adapters after both sub-layers, while others insert them only after the feed-forward network. The residual connection ensures that the adapter can learn to pass through its input unchanged when no adaptation is needed.

## Comparison to Other Methods

Adapter layers offer a different trade-off compared to methods like LoRA. While adapters add parameters to the model (increasing inference latency slightly), LoRA modifies existing weights without adding new parameters. However, adapters have the advantage of being modular — different task adapters can be swapped in and out of the same base model, enabling multi-task serving from a single pretrained backbone.
