# Alignment Techniques: RLHF, DPO, and RLAIF

## RLHF

RLHF (Reinforcement Learning from Human Feedback) is the most established alignment technique. It trains a reward model on human preference data, where annotators compare pairs of model outputs and select the preferred one. The reward model is then used as a signal for reinforcement learning to optimize the language model policy.

## DPO

Direct Preference Optimization (DPO) eliminates the need for a separate reward model. Instead, DPO directly optimizes the language model policy using preference pairs through a mathematically derived loss function. This simplifies the training pipeline and avoids the reward hacking problem where models learn to exploit imperfections in the reward model.

## RLAIF

RLAIF (Reinforcement Learning from AI Feedback) replaces human preference annotations with AI-generated labels. A capable language model serves as the annotator, providing preference judgments at much lower cost and higher throughput. Research shows that RLAIF can achieve comparable performance to RLHF for many alignment objectives.

## Trade-offs

RLHF provides the highest quality alignment but is expensive and slow due to human annotation requirements. DPO offers a simpler training pipeline with competitive results. RLAIF scales more easily but may inherit biases from the AI annotator. In practice, hybrid approaches combining these methods are increasingly common.
