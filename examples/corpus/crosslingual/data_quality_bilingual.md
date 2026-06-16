# Benchmark Data Quality / 评测数据质量

Deduplication prevents repeated examples from inflating benchmark scores. If the same or near-duplicate question appears many times, a system can look stronger without actually generalizing.

Data contamination occurs when evaluation examples appear in training data. Contamination makes benchmark results less trustworthy because the model may have seen the answer during training.

评测数据集需要去重和污染检测。数据污染指 evaluation examples 出现在 training data 中，这会使模型分数偏高，并削弱评测可信度。
