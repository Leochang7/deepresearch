# Hybrid Search and Reciprocal Rank Fusion in RAG

Hybrid search combines dense and sparse retrieval methods to achieve better retrieval quality than either approach alone. A key technique for combining these results is Reciprocal Rank Fusion (RRF), a simple yet effective method for merging ranked lists from different retrieval systems.

## Why Hybrid Search

Dense retrieval captures semantic similarity — understanding that "car" and "automobile" are related — while sparse retrieval like BM25 excels at exact keyword matching. A query for a specific product model number might be poorly served by semantic search but perfectly matched by BM25. Hybrid search combines both approaches to capture the strengths of each, improving recall and robustness across diverse query types.

## Reciprocal Rank Fusion (RRF)

RRF combines rankings from multiple retrieval systems using the formula: score = sum(1 / (k + rank_i)), where k is a constant (typically 60) and rank_i is the document's rank in each retrieval list. This approach works well because it depends only on rank positions, not raw scores, making it easy to combine scores from retrieval methods with very different score distributions.

## How RRF Works in Practice

In a hybrid search pipeline, the same query is sent to both the dense retrieval system and the sparse retrieval system. Each system returns its ranked list of documents. RRF then assigns each document a combined score based on its rank in each list. Documents that appear highly ranked in both lists receive the highest fused scores, while documents ranked highly by only one system receive moderate scores.

## Impact on RAG Quality

Hybrid search with RRF consistently outperforms either dense or sparse retrieval alone on retrieval benchmarks. By combining the semantic understanding of dense retrieval with the precision of sparse retrieval, hybrid systems achieve higher recall and more robust performance across different query types. This approach has become the recommended default for production RAG systems where retrieval quality is critical.
