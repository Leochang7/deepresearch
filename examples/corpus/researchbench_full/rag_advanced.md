# Advanced RAG Techniques and Failure Modes

## Query-Document Semantic Gap

A primary failure mode in RAG is the semantic gap between user queries and relevant documents. Queries are often short and use different terminology than the indexed documents. This mismatch causes the retriever to miss relevant passages, leading to incomplete or incorrect answers.

## Hypothetical Document Embeddings (HyDE)

HyDE addresses the semantic gap by generating a hypothetical answer to the query using the language model, then using that hypothetical answer as the retrieval query. Since the hypothetical answer is in the same style as the target documents, embedding similarity is higher. This technique improves recall for queries where direct embedding search fails.

## Citation Attribution

Citation attribution measures whether generated content is grounded in retrieved passages. Attribution scoring frameworks like RAGAS evaluate whether each claim in the generated answer can be traced back to a specific retrieved document. This is critical for trustworthy RAG systems in high-stakes domains like healthcare and legal.

## Reranking

Cross-encoder reranking applies a more powerful model to rescore the top-k retrieved passages. While initial retrieval uses fast bi-encoder models, reranking with a cross-encoder significantly improves precision by jointly encoding query and passage. This two-stage approach balances speed and quality.

## Iterative Retrieval

Some advanced RAG systems perform multiple rounds of retrieval, using the initial generation to reformulate the query for a second retrieval pass. This iterative approach helps when the original query is insufficient to retrieve all necessary information.
