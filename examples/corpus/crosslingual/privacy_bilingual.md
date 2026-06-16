# LLM Privacy / 隐私风险

Large language models can memorize sensitive training examples and leak them later through generated text. This risk is higher when datasets contain personal identifiers, secrets, or rare verbatim strings.

如果训练数据中包含个人身份信息、密钥或罕见原文片段，模型可能记忆这些 sensitive training examples，并在后续输出中泄露。

PII filtering and data minimization reduce privacy risk before training. Teams should remove unnecessary user data, redact personal identifiers, and keep provenance records for high-risk datasets.

隐私治理通常包括个人身份信息过滤、数据最小化、访问控制和训练前审计，以降低用户数据被模型记忆和泄露的概率。
